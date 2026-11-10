#!/usr/bin/env python3
"""
Validate and profile the raw corpora before anything is built on them.

Workbook 2 section 3.2 has to describe the sources, parameters and quantity of
the raw datasets and present samples from them; 3.3 has to pre-process them
"based on cleaning and validation tools". This is that tool, and it runs before
the pipeline rather than after, because the point is to catch a corpus that
should not be used at all.

It earned its place immediately: the `hindi` column of the Trilingual Hinglish
Corpus is misaligned with its own `english` and `hinglish` columns, and nothing
downstream would have noticed. A misaligned Devanagari reference would have
silently corrupted the code-switching-penalty metric, which is defined as the
difference between scores against a Devanagari and a Romanised reference for
the same source.

How the alignment probe works
-----------------------------
Comparing two sentences across scripts is hard; comparing what survives
translation is easy. Three signals survive both translation and
transliteration:

  * **digit runs** -- "1856" is "1856" in every script
  * **@handles and #hashtags** -- literal strings a translator carries over
  * **length** -- a translation of a long sentence is long

So for each pair of columns the script measures what share of the first
column's digit runs and tags reappear in the second, and the correlation of
their word counts. HinGE is the control: its English/Hindi pairs come from the
IIT Bombay parallel corpus and are known to be aligned, so its scores are what
"aligned" looks like for this measure.

The decisive signal is the inverse one. A translation can *drop* a handle, but
it cannot *invent* one. Rows whose Hindi column carries a handle the English
never had did not come from the same source sentence.

Usage
-----
  python3 scripts/validate_raw.py                       # profile + probe all
  python3 scripts/validate_raw.py --samples             # also write the 3.2 tables
  python3 scripts/validate_raw.py --fail-on-misalignment 0.05
"""

import argparse
import ast
import csv
import json
import re
import statistics
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

RAW = REPO_ROOT / "data" / "raw"
REPORTS = REPO_ROOT / "reports"

DIGITS = re.compile(r"\d+")
TAG = re.compile(r"[@#]\w+")
LATIN = re.compile(r"[A-Za-z][A-Za-z'\-]{3,}")
DEVA = re.compile(r"[ऀ-ॿ]")

csv.field_size_limit(10 ** 7)


class ValidationError(RuntimeError):
    pass


# ----------------------------------------------------------------- loaders
def load_hinge(path=RAW / "hinge" / "HinGE.csv"):
    """English / Devanagari Hindi / first human Hinglish reference."""
    if not Path(path).exists():
        raise ValidationError(
            "{}: not found. Run: python3 scripts/fetch_data.py --only hinge".format(path))
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out, refs_total = [], 0
    for r in rows:
        raw = (r.get("Human-generated Hinglish") or "").strip()
        refs = []
        if raw.startswith("["):
            try:
                refs = [str(x).strip() for x in ast.literal_eval(raw) if str(x).strip()]
            except (ValueError, SyntaxError):
                refs = []
        elif raw:
            refs = [raw]
        refs_total += len(refs)
        if refs:
            out.append((r.get("English") or "", r.get("Hindi") or "", refs[0]))
    return out, {"rows": len(rows), "human_references": refs_total}


def load_trilingual(d=RAW / "trilingual"):
    import pandas as pd
    frames, counts = [], {}
    for split in ("train", "test"):
        f = Path(d) / "{}.parquet".format(split)
        if not f.exists():
            raise ValidationError(
                "{}: not found. Run: python3 scripts/fetch_data.py --only trilingual".format(f))
        df = pd.read_parquet(f)
        counts[split] = len(df)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    triples = list(zip(df["english"].astype(str), df["hindi"].astype(str),
                       df["hinglish"].astype(str)))
    return triples, {"rows": len(df), **counts}


def load_phinc(path=RAW / "phinc" / "hinglish_english_parallel_corpus.csv"):
    """PHINC is a pair, not a triple: (english, '', hinglish)."""
    import pandas as pd
    if not Path(path).exists():
        raise ValidationError(
            "{}: not found. Run: python3 scripts/fetch_data.py --only phinc".format(path))
    df = pd.read_csv(path)
    triples = [(str(e), "", str(h)) for h, e in
               zip(df["Sentence"], df["English_Translation"])]
    return triples, {"rows": len(df)}


def load_cmu_dog(d=RAW / "cmu_dog"):
    import pandas as pd
    triples, counts = [], {}
    for split in ("train", "validation", "test"):
        f = Path(d) / "{}.parquet".format(split)
        if not f.exists():
            raise ValidationError(
                "{}: not found. Run: python3 scripts/fetch_data.py --only cmu_dog".format(f))
        df = pd.read_parquet(f)
        counts[split] = len(df)
        for t in df["translation"]:
            if isinstance(t, dict):
                en, hg = (t.get("en") or "").strip(), (t.get("hi_en") or "").strip()
                if en and hg:
                    triples.append((en, "", hg))
    return triples, {"usable_pairs": len(triples), **counts}


LOADERS = OrderedDict([
    ("hinge", load_hinge),
    ("phinc", load_phinc),
    ("cmu_dog", load_cmu_dog),
    ("trilingual", load_trilingual),
])


# ------------------------------------------------------------------ probes
def _toks(s, pat):
    return {m.lower() for m in pat.findall(s or "")}


def _share(a, b, pat):
    """Of the pattern matches in a, what fraction reappear in b? None if a has none."""
    ta, tb = _toks(a, pat), _toks(b, pat)
    if not ta:
        return None
    return len(ta & tb) / len(ta)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs), len(xs)) if xs else (None, 0)


def _corr(pairs):
    if len(pairs) < 3:
        return None
    xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
    try:
        return statistics.correlation(xs, ys)
    except statistics.StatisticsError:
        return None


def probe_pair(triples, left, right):
    """left/right are 0=english, 1=hindi, 2=hinglish."""
    dig = [_share(t[left], t[right], DIGITS) for t in triples]
    tag = [_share(t[left], t[right], TAG) for t in triples]
    lat = [_share(t[left], t[right], LATIN) for t in triples]
    lens = [(len(t[left].split()), len(t[right].split())) for t in triples
            if t[left].strip() and t[right].strip()]

    # The decisive one: tags present in `right` that `left` never had. A
    # translation can drop a handle; it cannot invent one.
    invented = sum(1 for t in triples if _toks(t[right], TAG) - _toks(t[left], TAG))

    d, dn = _mean(dig)
    g, gn = _mean(tag)
    l, ln = _mean(lat)
    return OrderedDict([
        ("digit_share", None if d is None else round(d, 4)),
        ("digit_rows", dn),
        ("tag_share", None if g is None else round(g, 4)),
        ("tag_rows", gn),
        ("latin_share", None if l is None else round(l, 4)),
        ("latin_rows", ln),
        ("length_correlation", None if _corr(lens) is None else round(_corr(lens), 4)),
        ("rows_with_invented_tag", invented),
        ("invented_tag_rate", round(invented / len(triples), 4) if triples else 0.0),
    ])


def profile(name, triples, counts):
    has_hi = sum(1 for t in triples if t[1].strip())
    deva_hi = sum(1 for t in triples if DEVA.search(t[1] or ""))
    deva_hg = sum(1 for t in triples if DEVA.search(t[2] or ""))
    entry = OrderedDict([
        ("counts", counts),
        ("usable_triples", len(triples)),
        ("rows_with_hindi_column", has_hi),
        ("hindi_is_devanagari_rate",
         round(deva_hi / has_hi, 4) if has_hi else None),
        ("hinglish_contains_devanagari_rate",
         round(deva_hg / len(triples), 4) if triples else None),
        ("mean_words", OrderedDict([
            ("english", round(statistics.fmean(
                [len(t[0].split()) for t in triples if t[0].strip()]), 2)),
            ("hinglish", round(statistics.fmean(
                [len(t[2].split()) for t in triples if t[2].strip()]), 2)),
        ])),
        ("probes", OrderedDict([
            ("english_vs_hinglish", probe_pair(triples, 0, 2)),
        ])),
    ])
    if has_hi:
        entry["probes"]["english_vs_hindi"] = probe_pair(triples, 0, 1)
    return entry


def write_samples(report, loaded, path=REPORTS / "raw_samples.md"):
    """The sample tables section 3.2 requires: real records, not descriptions."""
    lines = [
        "# Raw dataset samples",
        "",
        "Generated by `scripts/validate_raw.py --samples`. Every row below is a verbatim",
        "record from the fetched corpus, truncated to 100 characters for the page only.",
        "Provenance, licences and pinned revisions: `data/raw/MANIFEST.json`.",
        "",
    ]
    manifest = {}
    mpath = RAW / "MANIFEST.json"
    if mpath.exists():
        manifest = json.loads(mpath.read_text(encoding="utf-8")).get("datasets", {})

    def cut(s, n=100):
        s = " ".join((s or "").split())
        return s if len(s) <= n else s[: n - 1] + "…"

    for name, (triples, counts) in loaded.items():
        meta = manifest.get(name, {})
        prof = report["datasets"][name]
        lines += [
            "## {}".format(name),
            "",
            "- **Source:** `{}` at revision `{}`".format(
                meta.get("repo", "?"), str(meta.get("rev", "?"))[:12]),
            "- **Licence:** {}".format(meta.get("licence", "?")),
            "- **Quantity:** {}".format(", ".join(
                "{} {:,}".format(k, v) for k, v in counts.items())),
            "- **Usable triples:** {:,}".format(prof["usable_triples"]),
            "",
            "| # | English | Hindi (Devanagari) | Hinglish |",
            "|---|---|---|---|",
        ]
        for i, t in enumerate(triples[:3], start=1):
            lines.append("| {} | {} | {} | {} |".format(
                i, cut(t[0]), cut(t[1]) or "_(none in this corpus)_", cut(t[2])))
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--only", action="append", choices=list(LOADERS))
    p.add_argument("--samples", action="store_true",
                   help="also write reports/raw_samples.md for section 3.2")
    p.add_argument("--fail-on-misalignment", type=float, default=None,
                   metavar="RATE",
                   help="exit 3 if any corpus's invented-tag rate exceeds RATE")
    p.add_argument("--out", default=str(REPORTS / "raw_validation.json"))
    args = p.parse_args(argv)

    report = OrderedDict([("datasets", OrderedDict())])
    loaded = OrderedDict()
    for name in (args.only or list(LOADERS)):
        try:
            triples, counts = LOADERS[name]()
        except ValidationError as exc:
            print("{}: {}".format(name, exc), file=sys.stderr)
            return 2
        loaded[name] = (triples, counts)
        report["datasets"][name] = profile(name, triples, counts)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("\n{:<12} {:>9} {:>10} {:>10} {:>10} {:>12}".format(
        "corpus", "triples", "en/hg corr", "en/hi corr", "en/hi tag", "invented tag"))
    print("-" * 68)
    failures = []
    for name, prof in report["datasets"].items():
        hg = prof["probes"]["english_vs_hinglish"]
        hi = prof["probes"].get("english_vs_hindi")
        fmt = lambda v: "{:>10}".format("-" if v is None else "{:+.3f}".format(v))
        rate = hi["invented_tag_rate"] if hi else 0.0
        print("{:<12} {:>9,} {} {} {:>10} {:>11.1%}".format(
            name, prof["usable_triples"],
            fmt(hg["length_correlation"]),
            fmt(hi["length_correlation"]) if hi else "{:>10}".format("-"),
            "-" if not hi or hi["tag_share"] is None else "{:.3f}".format(hi["tag_share"]),
            rate))
        if args.fail_on_misalignment is not None and rate > args.fail_on_misalignment:
            failures.append((name, rate))

    print("\nreport -> {}".format(Path(args.out).relative_to(REPO_ROOT)))
    if args.samples:
        print("samples -> {}".format(write_samples(report, loaded).relative_to(REPO_ROOT)))

    print("\nen/hi corr and en/hi tag are only meaningful for a corpus that claims a\n"
          "Devanagari column. 'invented tag' is the share of rows whose Hindi carries an\n"
          "@handle or #hashtag the English never had: a translation cannot invent one, so\n"
          "those rows came from a different source sentence.")

    for name, rate in failures:
        print("\n{}: invented-tag rate {:.1%} exceeds the {:.1%} threshold. Its Devanagari "
              "column is not aligned with its own English column and must not be used as "
              "a reference.".format(name, rate, args.fail_on_misalignment), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
