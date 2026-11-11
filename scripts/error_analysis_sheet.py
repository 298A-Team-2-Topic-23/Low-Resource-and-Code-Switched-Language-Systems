#!/usr/bin/env python3
"""
Blind coding sheets for the error analysis, and their summary.  [298-84, owner: Jenil]

The categories, the sample and the analysis are fixed in analysis/error_analysis/CODEBOOK.md,
committed before any real model output existed. This script implements that document and
nothing else, so a choice made after seeing outputs has nowhere to hide.

  sheet       pick 50 unique test sources (seed 84), take each system's output for them, shuffle
              all outputs together and write a coding sheet with no system names on it, a
              30-row overlap sheet for the second coder, a sealed key and the automatic indicators
  summarise   after both sheets are coded: rates per code and system, paired M2-minus-M3 and
              M2-minus-M4 differences with bootstrap intervals, reference artifacts, coding
              agreement, and the automatic indicators

Usage
-----
  python scripts/error_analysis_sheet.py sheet \\
      --src out/test.en.txt --ref out/test.hinglish.txt \\
      --system M2=out/m2.s13.txt --system M3=out/m3.s13.txt --system M4=out/m4.s13.txt \\
      --out-dir analysis/error_analysis/run1

  python scripts/error_analysis_sheet.py summarise --dir analysis/error_analysis/run1

--src and --ref are the line-aligned files the notebook writes (one line per test record), and
each --system file is aligned with --src.
"""

import argparse
import csv
import json
import random
import statistics
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs.analysis.codemixing import cmi, spf  # noqa: E402
from lrcs.data.clean import hindi_markers, tag_tokens  # noqa: E402
from lrcs.lexicon import form_index, load_variant_groups  # noqa: E402
from lrcs.text import devanagari_fraction, word_tokens  # noqa: E402

SEED = 84
N_SOURCES = 50
N_OVERLAP = 30
BOOTSTRAP = 1000
CODES = ("SPELLING_VARIANT", "SPELLING_ERROR", "SWITCH_LOW", "SWITCH_HIGH", "SWITCH_BOUNDARY",
         "SCRIPT", "ADEQUACY", "FLUENCY", "OK")
# Spelling is analysed as one category; the codebook keeps the two kinds apart for the reader.
CATEGORIES = OrderedDict([
    ("spelling", ("SPELLING_VARIANT", "SPELLING_ERROR")),
    ("switching", ("SWITCH_LOW", "SWITCH_HIGH", "SWITCH_BOUNDARY")),
    ("script", ("SCRIPT",)),
    ("adequacy", ("ADEQUACY",)),
    ("fluency", ("FLUENCY",)),
])
SHEET_COLUMNS = ("row_id", "english_source", "references", "output", "codes", "acceptable",
                 "notes")
REF_SEPARATOR = " || "


def read_lines(path):
    return Path(path).read_text(encoding="utf-8").rstrip("\n").split("\n")


def sample_sources(src_lines, n=N_SOURCES, seed=SEED):
    """First line index of each unique source, then n of them at random."""
    first = OrderedDict()
    for i, line in enumerate(src_lines):
        first.setdefault(line.strip(), i)
    if len(first) < n:
        sys.exit("need {} unique sources, found {}".format(n, len(first)))
    return sorted(random.Random(seed).sample(list(first.values()), n))


def references_for(src_lines, ref_lines, index):
    source = src_lines[index].strip()
    refs = [r for s, r in zip(src_lines, ref_lines) if s.strip() == source]
    return list(OrderedDict.fromkeys(refs))


def indicators(output, english, index_by_form, groups, markers):
    """What can be measured without a coder. Hidden from coders until summarise."""
    tokens = [t.lower() for t in word_tokens(output)]
    in_lexicon = [t for t in tokens if t in index_by_form]
    canonical = [t for t in in_lexicon if t == index_by_form[t]]
    tags = [tag for _, tag in tag_tokens(output, english, markers)]
    point = spf(tags)
    return {
        "devanagari_share": round(devanagari_fraction(output), 4),
        "lexicon_tokens": len(in_lexicon),
        "canonical_tokens": len(canonical),
        "cmi": round(cmi(tags), 2),
        "spf": "" if point is None else round(point, 4),
    }


def write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def make_sheet(src, ref, systems, out_dir, n=N_SOURCES, overlap=N_OVERLAP, seed=SEED):
    src_lines, ref_lines = read_lines(src), read_lines(ref)
    if len(src_lines) != len(ref_lines):
        sys.exit("--src and --ref differ in length")
    outputs = {}
    for name, path in systems.items():
        outputs[name] = read_lines(path)
        if len(outputs[name]) != len(src_lines):
            sys.exit("{} has {} lines, --src has {}".format(name, len(outputs[name]),
                                                            len(src_lines)))

    chosen = sample_sources(src_lines, n, seed)
    groups = load_variant_groups()
    index_by_form, markers = form_index(groups), hindi_markers(groups)
    rows = []
    for line in chosen:
        refs = references_for(src_lines, ref_lines, line)
        for name in systems:
            rows.append({"system": name, "line": line, "english_source": src_lines[line],
                         "references": REF_SEPARATOR.join(refs),
                         "output": outputs[name][line]})
    rng = random.Random(seed)
    rng.shuffle(rows)
    width = len(str(len(rows)))
    for i, row in enumerate(rows, start=1):
        row["row_id"] = "E{:0{}d}".format(i, width)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blank = {"codes": "", "acceptable": "", "notes": ""}
    sheet = [dict({k: r[k] for k in SHEET_COLUMNS if k in r}, **blank) for r in rows]
    write_csv(out / "coding_sheet.csv", SHEET_COLUMNS, sheet)
    shared = sorted(random.Random(seed).sample(range(len(sheet)), min(overlap, len(sheet))))
    write_csv(out / "coding_sheet_overlap.csv", SHEET_COLUMNS, [sheet[i] for i in shared])
    write_csv(out / "key.csv", ("row_id", "system", "line"),
              [{"row_id": r["row_id"], "system": r["system"], "line": r["line"]} for r in rows])
    auto = [dict(row_id=r["row_id"], **indicators(r["output"], r["english_source"],
                                                   index_by_form, groups, markers))
            for r in rows]
    write_csv(out / "auto.csv", ("row_id",) + tuple(k for k in auto[0] if k != "row_id"), auto)
    identical = sum(1 for line in chosen if len({outputs[s][line] for s in systems}) == 1)
    meta = {"seed": seed, "sources": n, "systems": list(systems), "rows": len(rows),
            "overlap_rows": len(shared), "sources_with_identical_outputs": identical,
            "src": str(src), "ref": str(ref), "system_files": {k: str(v) for k, v in systems.items()}}
    (out / "sheet.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def parse_codes(row):
    codes = {c.strip().upper() for c in row["codes"].replace(";", ",").split(",") if c.strip()}
    problems = []
    if not codes:
        problems.append("{}: no codes".format(row["row_id"]))
    unknown = codes - set(CODES)
    if unknown:
        problems.append("{}: unknown codes {}".format(row["row_id"], sorted(unknown)))
    if "OK" in codes and len(codes) > 1:
        problems.append("{}: OK must stand alone".format(row["row_id"]))
    if row["acceptable"].strip().lower() not in ("yes", "no"):
        problems.append("{}: acceptable must be yes or no".format(row["row_id"]))
    return codes, problems


def has(codes, category):
    return any(c in codes for c in CATEGORIES[category])


def paired_difference(a, b, samples=BOOTSTRAP, seed=SEED):
    """Mean of a minus mean of b over paired items, with a 95% bootstrap interval."""
    n = len(a)
    rng = random.Random(seed)
    diffs = []
    for _ in range(samples):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(a[i] - b[i] for i in idx) / n)
    diffs.sort()
    return {"difference": round(sum(x - y for x, y in zip(a, b)) / n, 4),
            "ci95": [round(diffs[int(0.025 * samples)], 4),
                     round(diffs[int(0.975 * samples) - 1], 4)]}


def sentence_chrf(output, references):
    from sacrebleu.metrics import CHRF
    return CHRF(word_order=2).sentence_score(output, references).score


def nominal_alpha(pairs):
    sys.path.insert(0, str(REPO_ROOT / "human_eval"))
    from agreement import krippendorff_alpha
    return krippendorff_alpha([list(p) for p in pairs], scale="nominal")


def summarise(run_dir):
    run = Path(run_dir)
    sheet = read_csv(run / "coding_sheet.csv")
    key = {r["row_id"]: r for r in read_csv(run / "key.csv")}
    auto = {r["row_id"]: r for r in read_csv(run / "auto.csv")}
    problems, coded = [], {}
    for row in sheet:
        codes, issues = parse_codes(row)
        problems += issues
        coded[row["row_id"]] = (codes, row["acceptable"].strip().lower() == "yes")
        devanagari = float(auto[row["row_id"]]["devanagari_share"]) > 0
        if not issues and devanagari != ("SCRIPT" in codes):
            problems.append("{}: SCRIPT disagrees with the automatic indicator".format(
                row["row_id"]))
    if problems:
        return {"complete": False, "problems": problems}

    systems = list(OrderedDict.fromkeys(k["system"] for k in key.values()))
    by_system = {s: {} for s in systems}
    for row in sheet:
        k = key[row["row_id"]]
        by_system[k["system"]][int(k["line"])] = row
    lines = sorted(next(iter(by_system.values())))

    result = {"complete": True, "rates": {}, "differences": {}, "reference_artifacts": {},
              "automatic": {}, "agreement": {}}
    for s in systems:
        rows = [by_system[s][line] for line in lines]
        result["rates"][s] = {cat: round(sum(has(coded[r["row_id"]][0], cat) for r in rows)
                                         / len(rows), 4) for cat in CATEGORIES}
        result["rates"][s]["acceptable"] = round(
            sum(coded[r["row_id"]][1] for r in rows) / len(rows), 4)
        scores = [sentence_chrf(r["output"], r["references"].split(REF_SEPARATOR)) for r in rows]
        median = statistics.median(scores)
        result["reference_artifacts"][s] = sum(
            1 for r, score in zip(rows, scores) if coded[r["row_id"]][1] and score < median)
        auto_rows = [auto[r["row_id"]] for r in rows]
        lexicon = sum(int(a["lexicon_tokens"]) for a in auto_rows)
        spfs = [float(a["spf"]) for a in auto_rows if a["spf"] != ""]
        result["automatic"][s] = {
            "canonical_spelling_rate": round(sum(int(a["canonical_tokens"]) for a in auto_rows)
                                             / lexicon, 4) if lexicon else None,
            "outputs_with_devanagari": sum(float(a["devanagari_share"]) > 0 for a in auto_rows),
            "mean_cmi": round(statistics.mean(float(a["cmi"]) for a in auto_rows), 2),
            "mean_spf": round(statistics.mean(spfs), 4) if spfs else None,
        }

    def vector(system, category):
        return [int(has(coded[by_system[system][line]["row_id"]][0], category)) for line in lines]

    for other in ("M3", "M4"):
        if "M2" in by_system and other in by_system:
            result["differences"]["M2_minus_" + other] = {
                cat: paired_difference(vector("M2", cat), vector(other, cat)) for cat in CATEGORIES}

    overlap_path = run / "coding_sheet_overlap.csv"
    second = read_csv(overlap_path) if overlap_path.exists() else []
    if second and all(r["codes"].strip() for r in second):
        for name, test in list(CATEGORIES.items()) + [("acceptable", None)]:
            pairs = []
            for r in second:
                mine = coded[r["row_id"]]
                theirs, _ = parse_codes(r)
                if test is None:
                    pairs.append((mine[1], r["acceptable"].strip().lower() == "yes"))
                else:
                    pairs.append((has(mine[0], name), has(theirs, name)))
            agree = sum(a == b for a, b in pairs) / len(pairs)
            prevalence = sum(a + b for a, b in pairs) / (2 * len(pairs))
            alpha = nominal_alpha(pairs) if len({v for p in pairs for v in p}) > 1 else None
            result["agreement"][name] = {
                "alpha": None if alpha is None else round(alpha, 3),
                "raw_agreement": round(agree, 3), "prevalence": round(prevalence, 3),
                "reliable": alpha is not None and alpha >= 0.667}
    else:
        result["agreement"] = "overlap sheet not yet coded"
    (run / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--src", required=True)
    s.add_argument("--ref", required=True)
    s.add_argument("--system", action="append", required=True, metavar="NAME=PATH")
    s.add_argument("--out-dir", required=True)
    m = sub.add_parser("summarise")
    m.add_argument("--dir", required=True)
    args = ap.parse_args(argv)

    if args.command == "sheet":
        systems = OrderedDict(item.split("=", 1) for item in args.system)
        meta = make_sheet(args.src, args.ref, systems, args.out_dir)
        print("wrote {rows} rows for {sources} sources; {overlap_rows} overlap rows; "
              "{sources_with_identical_outputs} sources identical across systems".format(**meta))
        return 0
    result = summarise(args.dir)
    if not result["complete"]:
        for problem in result["problems"]:
            print("incomplete:", problem)
        return 1
    print(json.dumps(result["rates"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
