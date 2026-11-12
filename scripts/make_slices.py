#!/usr/bin/env python3
"""
Build the four text slices requirement AI-6 is measured over.  [298-75]

AI-6 (`docs/workbook1/section_1_2.md`) says fertility is reported for **English,
Devanagari Hindi, Romanized Hindi and Romanized Hinglish**. Only English and
Hinglish were ever measured, so `docs/workbook2/carry_forward.md` had to correct
the requirement from met to partly met. This script builds every slice the
repository can actually supply, and says precisely what is missing for the rest
instead of leaving the requirement ambiguous.

    python3 scripts/make_slices.py
    python3 scripts/make_slices.py --out-dir data/slices --seed 42

Writes one `<slice>.txt` per available slice plus `manifest.json` recording, for
each of the four, either the source and a SHA-256 or the reason it is absent and
the one command that would supply it.

Reproducible from a clean clone. The English and Hinglish sources come from the
committed deterministic generator (`lrcs.data.synthetic`, seed 42), not from the
untracked file in `data/raw/`, so a fresh checkout regenerates byte-identical
slices. Romanized Hindi comes from the committed team-authored parallel fixture.

Nothing here downloads anything.

Script guard
------------
Each slice declares the script it must be written in, and a slice whose content
fails that check is **refused rather than written**. This is the failure mode
that would otherwise close AI-6 dishonestly: dropping a Romanised file in as
`hi_deva` would produce four rows in the table and a requirement marked met,
while measuring the same script twice.
"""

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative                      # noqa: E402
from lrcs.text import devanagari_fraction, sha256_bytes  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "data" / "slices"
FIXTURE = REPO_ROOT / "data" / "codemix" / "parallel_fixture.tsv"
DEFAULT_N = 1200
DEFAULT_SEED = 42

# Minimum Devanagari fraction for a slice that must be in Devanagari, and the
# maximum for one that must be Roman. The gap between them is deliberate: a
# genuinely mixed file fails both and is refused rather than silently accepted.
DEVA_MIN = 0.50
ROMAN_MAX = 0.05


class SliceError(RuntimeError):
    pass


def _check_script(name, lines, script):
    """Refuse a slice written in the wrong script. Returns the measured fraction."""
    joined = " ".join(lines)
    frac = devanagari_fraction(joined)
    if script == "devanagari" and frac < DEVA_MIN:
        raise SliceError(
            "slice {!r} must be Devanagari but is {:.1%} Devanagari. Refusing to "
            "write it: a Romanised file labelled hi_deva would measure the same "
            "script twice and close AI-6 on a slice that is not the one the "
            "requirement names.".format(name, frac))
    if script == "roman" and frac > ROMAN_MAX:
        raise SliceError(
            "slice {!r} must be Roman but is {:.1%} Devanagari. Refusing to write "
            "it.".format(name, frac))
    return frac


def synthetic_columns(n, seed):
    """English and Hinglish from the committed deterministic generator.

    Generated in memory rather than read from data/raw/, which is gitignored. The
    generator is seeded, so this is the same content a clean clone produces.
    """
    from lrcs.data.synthetic import generate

    # generate() yields (english, hindi, hinglish) tuples. The hindi field is
    # always empty -- that absence is the whole reason hi_deva cannot be built.
    rows = generate(n, seed)
    english, hinglish = [], []
    for en, _hindi, hg in rows:
        en, hg = (en or "").strip(), (hg or "").strip()
        if en:
            english.append(en)
        if hg:
            hinglish.append(hg)
    return english, hinglish


def hinge_columns(csv_path):
    """English, Hinglish and Devanagari Hindi from the real HinGE release.

    Preferred over `synthetic_columns` now that the corpus is fetchable: AI-6
    asks what the tokenizer does to real text, and fertility measured on
    generated text answers a weaker question. `scripts/fetch_data.py` puts the
    file in place from a pinned revision, so a clean clone still reproduces.

    The 'Human-generated Hinglish' column is a Python list literal holding one
    to eight human renderings of the same English sentence; every rendering is
    its own line, because each is a real observation of how a person wrote it.
    """
    import ast
    import csv as _csv

    path = Path(csv_path)
    if not path.exists():
        raise SliceError(
            "{}: not found. Fetch the corpus first:\n"
            "  python3 scripts/fetch_data.py --only hinge".format(path))
    with path.open(encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    if not rows:
        raise SliceError("{}: empty".format(path))

    def column(*names):
        for want in names:
            for c in rows[0]:
                if str(c).strip().lower() == want:
                    return c
        raise SliceError("{}: no {} column (columns: {})".format(
            path, " / ".join(names), ", ".join(map(str, rows[0]))))

    c_en, c_hi = column("english"), column("hindi")
    c_hg = column("human-generated hinglish", "hinglish")

    english, hinglish, hindi = [], [], []
    for r in rows:
        en = str(r.get(c_en) or "").strip()
        hi = str(r.get(c_hi) or "").strip()
        if en:
            english.append(en)
        if hi:
            hindi.append(hi)
        raw = str(r.get(c_hg) or "").strip()
        refs = []
        if raw.startswith("["):
            try:
                parsed = ast.literal_eval(raw)
                refs = [str(x).strip() for x in parsed if str(x).strip()]
            except (ValueError, SyntaxError):
                refs = []
        elif raw:
            refs = [raw]
        hinglish.extend(refs)

    if not (english and hinglish and hindi):
        raise SliceError(
            "{}: expected all three of English, Hindi and Hinglish to be "
            "populated, got {} / {} / {}".format(
                path, len(english), len(hindi), len(hinglish)))
    return english, hinglish, hindi


def fixture_romanised_hindi(path=FIXTURE):
    """The Romanised Hindi side of the committed team-authored parallel fixture."""
    if not Path(path).exists():
        raise SliceError("{}: not found".format(path))
    out = []
    for lineno, raw in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        if lineno == 1 and parts[0].strip().lower() in {"english", "en", "source"}:
            continue
        hindi = parts[1].strip()
        if hindi:
            out.append(hindi)
    if not out:
        raise SliceError("{}: no Romanised Hindi rows".format(path))
    return out


def build(out_dir, n=DEFAULT_N, seed=DEFAULT_SEED, hinge_csv=None):
    """Returns the manifest. Writes a .txt per available slice.

    With `hinge_csv`, English and Hinglish come from the real corpus and the
    Devanagari slice is built in the same pass, so AI-6 is answered on real
    text. Without it the seeded generator is used, which keeps the offline
    path working on a machine that has not fetched anything.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    hinge_deva = None
    if hinge_csv:
        english, hinglish, hinge_deva = hinge_columns(hinge_csv)
        src = repo_relative(Path(hinge_csv))
        en_source = "{} English column (real corpus)".format(src)
        hg_source = "{} Human-generated Hinglish column, every human reference " \
                    "on its own line (real corpus)".format(src)
        regen = "python3 scripts/fetch_data.py --only hinge && " \
                "python3 scripts/make_slices.py --from-hinge {}".format(src)
        en_regen = hg_regen = regen
    else:
        english, hinglish = synthetic_columns(n, seed)
        en_source = "lrcs.data.synthetic generate(n={}, seed={}) english column".format(n, seed)
        hg_source = "lrcs.data.synthetic generate(n={}, seed={}) hinglish column".format(n, seed)
        en_regen = hg_regen = "python3 scripts/make_slices.py --seed {}".format(seed)

    available = OrderedDict([
        ("en", {
            "lines": english,
            "script": "roman",
            "source": en_source,
            "regenerate": en_regen,
        }),
        ("hi_roman", {
            "lines": fixture_romanised_hindi(),
            "script": "roman",
            "source": repo_relative(FIXTURE) + " hindi_roman column",
            "regenerate": "python3 scripts/make_slices.py",
        }),
        ("hinglish", {
            "lines": hinglish,
            "script": "roman",
            "source": hg_source,
            "regenerate": hg_regen,
        }),
    ])

    if hinge_deva is not None:
        available["hi_deva"] = {
            "lines": hinge_deva,
            "script": "devanagari",
            "source": "{} Hindi column (real corpus)".format(
                repo_relative(Path(hinge_csv))),
            "regenerate": "python3 scripts/fetch_data.py --only hinge && "
                          "python3 scripts/make_slices.py --from-hinge {}".format(
                              repo_relative(Path(hinge_csv))),
        }

    # Any slice the repository cannot supply is recorded with the reason and the
    # command that closes it, so a gap is actionable rather than a blank.
    absent = OrderedDict()
    if hinge_deva is None:
        absent["hi_deva"] = {
            "reason": "no Devanagari text is committed anywhere in this repository "
                      "(data/raw/ is gitignored), and this run was given no corpus "
                      "to read it from. The synthetic generator produces an empty "
                      "hindi column.",
            "supplied_by": "The HinGE release, whose 'Hindi' column is Devanagari. "
                           "It is published by the authors' own lab at "
                           "https://huggingface.co/datasets/LingoIITGN/HinGE under "
                           "CC-BY-4.0 and is fetched by scripts/fetch_data.py.",
            "command_that_closes_it":
                "python3 scripts/fetch_data.py --only hinge && "
                "python3 scripts/make_slices.py --from-hinge data/raw/hinge/HinGE.csv",
        }

    manifest = OrderedDict([
        ("slices_required_by_ai6", ["en", "hi_deva", "hi_roman", "hinglish"]),
        ("present", OrderedDict()),
        ("absent", absent),
    ])

    for name, spec in available.items():
        frac = _check_script(name, spec["lines"], spec["script"])
        path = out_dir / "{}.txt".format(name)
        body = "\n".join(spec["lines"]) + "\n"
        path.write_text(body, encoding="utf-8")
        manifest["present"][name] = OrderedDict([
            ("path", repo_relative(path)),
            ("n_lines", len(spec["lines"])),
            ("script", spec["script"]),
            ("devanagari_fraction", round(frac, 6)),
            ("source", spec["source"]),
            ("sha256", sha256_bytes(body.encode("utf-8"))),
            ("regenerate", spec["regenerate"]),
        ])

    if absent:
        manifest["ai6_status"] = (
            "not met: {} of 4 slices measurable ({}). Missing: {}.".format(
                len(manifest["present"]), ", ".join(manifest["present"]),
                ", ".join(absent)))
    else:
        manifest["ai6_status"] = "met: 4 of 4 slices measured."
    manifest["sources_are_real"] = bool(hinge_csv)

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", default=str(DEFAULT_OUT))
    p.add_argument("--n", type=int, default=DEFAULT_N,
                   help="rows from the synthetic generator (default 1200, the "
                        "size the committed pipeline run used)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--from-hinge", metavar="CSV",
                   help="build English, Hinglish and Devanagari Hindi from the "
                        "real HinGE release (data/raw/hinge/HinGE.csv after "
                        "scripts/fetch_data.py). This is the reported path: it "
                        "answers AI-6 on real text rather than generated text")
    p.add_argument("--hi-deva-from", metavar="CSV",
                   help="add only the Devanagari slice from a CSV with a 'Hindi' "
                        "column, leaving the other slices as built")
    args = p.parse_args(argv)

    try:
        manifest = build(args.out_dir, n=args.n, seed=args.seed,
                         hinge_csv=args.from_hinge)
        if args.hi_deva_from:
            manifest = add_hi_deva(args.out_dir, args.hi_deva_from, manifest)
    except SliceError as exc:
        print("slice build refused: {}".format(exc), file=sys.stderr)
        return 2

    print("slices -> {}".format(repo_relative(Path(args.out_dir))))
    for name, info in manifest["present"].items():
        print("  {:9s} {:>6,} lines  sha256 {}".format(
            name, info["n_lines"], info["sha256"][:12]))
    for name, info in manifest["absent"].items():
        print("  {:9s} ABSENT -- {}".format(name, info["reason"].split(".")[0]))
    print("\nAI-6: {}".format(manifest["ai6_status"]))
    if manifest["absent"]:
        print("\nTo close it:\n  {}".format(
            list(manifest["absent"].values())[0]["command_that_closes_it"]))
    return 0


def add_hi_deva(out_dir, csv_path, manifest):
    """Build the Devanagari slice from a CSV with a 'Hindi' column.

    Not exercised by the committed run, because no such CSV exists on any team
    machine yet. It is here so that closing AI-6 is one command and not a code
    change -- the work should be reduced to obtaining the corpus.
    """
    import csv as _csv

    path = Path(csv_path)
    if not path.exists():
        raise SliceError(
            "{}: not found. Convert the HinGE release first: "
            "python3 scripts/convert_hinge_pkl.py data/raw/HinGE.pkl {}".format(path, path))
    with path.open(encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    if not rows:
        raise SliceError("{}: empty".format(path))
    column = next((c for c in rows[0] if str(c).strip().lower() == "hindi"), None)
    if column is None:
        raise SliceError("{}: no 'Hindi' column (columns: {})".format(
            path, ", ".join(map(str, rows[0]))))

    lines = [str(r[column]).strip() for r in rows if str(r.get(column) or "").strip()]
    if not lines:
        raise SliceError("{}: the 'Hindi' column is empty".format(path))
    frac = _check_script("hi_deva", lines, "devanagari")

    out = Path(out_dir) / "hi_deva.txt"
    body = "\n".join(lines) + "\n"
    out.write_text(body, encoding="utf-8")
    manifest["present"]["hi_deva"] = OrderedDict([
        ("path", repo_relative(out)),
        ("n_lines", len(lines)),
        ("script", "devanagari"),
        ("devanagari_fraction", round(frac, 6)),
        ("source", "{} Hindi column".format(repo_relative(path))),
        ("sha256", sha256_bytes(body.encode("utf-8"))),
        ("regenerate", "python3 scripts/make_slices.py --hi-deva-from {}".format(
            repo_relative(path))),
    ])
    manifest["absent"].pop("hi_deva", None)
    manifest["ai6_status"] = "met: 4 of 4 slices measured." if not manifest["absent"] else \
        manifest["ai6_status"]
    (Path(out_dir) / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    sys.exit(main())
