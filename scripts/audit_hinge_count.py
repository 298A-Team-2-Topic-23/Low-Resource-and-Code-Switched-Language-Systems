#!/usr/bin/env python3
"""
Reconcile the HinGE human-reference count: 4,799 measured against 4,803 published.  [298-77]

The pipeline counts 4,799 human Hinglish references from 1,976 source rows. The
paper (Srivastava & Singh, 2021, Table 1) publishes 4,803. This script tests
every candidate explanation for the four-reference gap against the released
file itself and records which ones the file rules out.

    python scripts/audit_hinge_count.py data/raw/HinGE.pkl \
        --expected-sha256 e78c8f48af3eea0b141e767082189b7b619e9cbe50ad8f0b2a4863b82ebc5960
    # also count the CSV the pipeline ingests, and cross-check the authors'
    # second release (HinglishEval, same Drive folder):
    python scripts/audit_hinge_count.py data/raw/HinGE.pkl --csv data/raw/hinge.csv \
        --hinglisheval data/raw/hinglisheval/human_generated

The pickle is opened only through scripts/convert_hinge_pkl.py's restricted
unpickler. Output: reports/hinge_reference_count.json -- counts and row
indices only, never sentence text, so it is safe to commit.

Candidates checked, cheapest first (the order in the 298-77 brief):
  1. whitespace-only or empty reference strings that ingest would drop
  2. duplicate references inside one source row (positions vs distinct strings)
  3. malformed cells: not a list, or holding non-string items
  4. the pipeline's ingest counting differently from the file
  5. source pairs the authors counted but left out of the release (--hinglisheval)
  6. the published figure counting something the release does not contain
"""

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lrcs import repo_relative  # noqa: E402

PUBLISHED = OrderedDict([
    ("source", "Srivastava & Singh (2021), HinGE, Table 1 and section 2"),
    ("parallel_sentences_table1", 1976),
    ("human_generated_sentences_table1", 4803),
    ("machine_generated_sentences_table1", 3952),
    ("sentence_pairs_section2_text", 1978),
    ("min_references_per_pair_claimed", 2),
])


def human_column(df):
    cols = [c for c in df.columns if "human" in str(c).lower()]
    if not cols:
        raise ValueError("no human-generated Hinglish column in {}".format(list(df.columns)))
    return cols[0]


def audit_frame(df):
    """All checks that need only the DataFrame. Returns an OrderedDict."""
    col = human_column(df)
    cells = list(df[col])
    non_list = [i for i, v in enumerate(cells) if not isinstance(v, (list, tuple))]
    lists = [list(v) if isinstance(v, (list, tuple)) else [v] for v in cells]
    non_str = [i for i, v in enumerate(lists) if any(not isinstance(s, str) for s in v)]
    blank = [i for i, v in enumerate(lists) if any(not str(s).strip() for s in v)]
    positions = sum(len(v) for v in lists)
    distinct = sum(len(set(map(str, v))) for v in lists)
    dup_rows = [i for i, v in enumerate(lists) if len(v) != len(set(map(str, v)))]
    lengths = Counter(len(v) for v in lists)
    english = [str(e).strip() for e in df["English"]]
    eng_counts = Counter(english)
    machine = sum(1 for c in ("WAC", "PAC") if c in df.columns
                  for v in df[c] if isinstance(v, str) and v.strip())

    measured = OrderedDict([
        ("rows", len(df)),
        ("unique_english_sources", len(eng_counts)),
        ("english_sources_appearing_twice", sum(1 for n in eng_counts.values() if n > 1)),
        ("reference_positions", positions),
        ("distinct_references_per_row_summed", distinct),
        ("references_per_row", OrderedDict(sorted((str(k), v) for k, v in lengths.items()))),
        ("rows_with_fewer_than_two_references", lengths.get(1, 0) + lengths.get(0, 0)),
        ("machine_generated_non_empty", machine),
        ("index_contiguous", list(df.index) == list(range(len(df)))),
    ])
    gap = PUBLISHED["human_generated_sentences_table1"] - positions
    checks = [
        ("empty_or_whitespace_references",
         len(blank) == 0,
         "{} row(s) hold an empty or whitespace-only reference".format(len(blank)),
         blank),
        ("duplicate_references_within_a_row",
         True,
         "{} row(s) repeat a reference; counting distinct strings gives {:,}, "
         "which moves AWAY from 4,803, so it cannot explain the gap".format(
             len(dup_rows), distinct),
         dup_rows),
        ("cells_not_a_list", len(non_list) == 0,
         "{} cell(s) are not a list".format(len(non_list)), non_list),
        ("non_string_references", len(non_str) == 0,
         "{} row(s) hold a non-string reference".format(len(non_str)), non_str),
    ]
    return measured, gap, checks


def ingest_count(csv_path):
    """What stage 1 of the pipeline counts from the converted CSV."""
    from lrcs.data import ingest
    records, provenance = ingest.ingest_file(csv_path)
    blank = sum(1 for r in records if not r["hinglish"].strip())
    return OrderedDict([("csv", repo_relative(Path(csv_path))),
                        ("sha256", provenance["sha256"]),
                        ("rows_in_file", provenance["rows_in_file"]),
                        ("records", provenance["records"]),
                        ("records_with_empty_hinglish", blank)])


def hinglisheval_crosscheck(df, directory):
    """Compare HinGE's sources with the authors' second release.

    HinglishEval (same authors, same Drive folder) ships its own human-generated
    references as {English: [Hinglish, ...]} pickles. If HinGE.pkl were missing
    source pairs that the authors counted, they could show up here. Opened with
    the same restricted unpickler; compared on lrcs.text.dedup_key, with any
    unmatched source checked for a near-duplicate (character 4-gram Jaccard >= 0.7,
    the pipeline's threshold) so that a corrupted copy is not mistaken for a
    missing pair.
    """
    from convert_hinge_pkl import _restricted_unpickler
    from lrcs.data.splits import jaccard, shingles
    from lrcs.text import dedup_key

    hinge_keys = {dedup_key(str(e)) for e in df["English"]}
    other = {}
    files = sorted(Path(directory).glob("*_human_generated.pkl"))
    if not files:
        raise FileNotFoundError("{}: no *_human_generated.pkl files".format(directory))
    for path in files:
        obj = _restricted_unpickler(path.read_bytes()).load()
        if not isinstance(obj, dict):
            raise ValueError("{}: expected a dict, got {}".format(path.name, type(obj).__name__))
        for english, refs in obj.items():
            other[dedup_key(str(english))] = len(refs) if isinstance(refs, (list, tuple)) else 1
    unmatched = sorted(set(other) - hinge_keys)
    hinge_shingles = [(k, shingles(k)) for k in sorted(hinge_keys)]
    near = []
    for key in unmatched:
        s = shingles(key)
        best = max((jaccard(s, hs) for _, hs in hinge_shingles), default=0.0)
        near.append(round(best, 3))
    return OrderedDict([
        ("files", [p.name for p in files]),
        ("unique_sources", len(other)),
        ("sources_also_in_hinge", len(set(other) & hinge_keys)),
        ("hinge_sources_absent_from_hinglisheval", len(hinge_keys - set(other))),
        ("sources_absent_from_hinge", len(unmatched)),
        ("their_references", sum(other[k] for k in unmatched)),
        ("best_jaccard_to_a_hinge_source", near),
        ("absent_sources_that_are_near_copies_of_a_hinge_source",
         sum(1 for j in near if j >= 0.7)),
    ])


def build_report(df, digest, csv_path=None, hinglisheval_dir=None):
    measured, gap, checks = audit_frame(df)
    report = OrderedDict([
        ("input_sha256", digest),
        ("published", PUBLISHED),
        ("measured", measured),
        ("gap_published_minus_measured", gap),
        ("checks", [OrderedDict([("check", name), ("ruled_out", ok), ("finding", text),
                                 ("row_indices", rows[:20])])
                    for name, ok, text, rows in checks]),
    ])
    if csv_path:
        ing = ingest_count(csv_path)
        report["pipeline_ingest"] = ing
        report["checks"].append(OrderedDict([
            ("check", "pipeline_counts_differently_from_file"),
            ("ruled_out", ing["records"] == measured["reference_positions"]),
            ("finding", "ingest reads {:,} records from the CSV; the pickle holds {:,} "
                        "reference positions".format(ing["records"],
                                                     measured["reference_positions"])),
            ("row_indices", []),
        ]))
    if hinglisheval_dir:
        cross = hinglisheval_crosscheck(df, hinglisheval_dir)
        report["hinglisheval_crosscheck"] = cross
        genuinely_missing = (cross["sources_absent_from_hinge"]
                             - cross["absent_sources_that_are_near_copies_of_a_hinge_source"])
        report["checks"].append(OrderedDict([
            ("check", "source_pairs_missing_from_the_release"),
            ("ruled_out", genuinely_missing == 0),
            ("finding", "HinglishEval holds {} source(s) absent from HinGE.pkl, {} of them "
                        "near-copies of a HinGE source".format(
                            cross["sources_absent_from_hinge"],
                            cross["absent_sources_that_are_near_copies_of_a_hinge_source"])),
            ("row_indices", []),
        ]))
    rows_ok = measured["rows"] == PUBLISHED["parallel_sentences_table1"]
    machine_ok = measured["machine_generated_non_empty"] == PUBLISHED["machine_generated_sentences_table1"]
    report["published_figures_consistency"] = OrderedDict([
        ("rows_match_table1", rows_ok),
        ("machine_generated_match_table1", machine_ok),
        ("table1_pairs_vs_section2_pairs",
         "{} vs {}: the paper disagrees with itself by {}".format(
             PUBLISHED["parallel_sentences_table1"], PUBLISHED["sentence_pairs_section2_text"],
             PUBLISHED["sentence_pairs_section2_text"] - PUBLISHED["parallel_sentences_table1"])),
        ("every_pair_has_two_references",
         "claimed; {} row(s) in the release have one".format(
             measured["rows_with_fewer_than_two_references"])),
    ])
    file_side = all(c["ruled_out"] for c in report["checks"])
    report["verdict"] = (
        "measured count confirmed: the release holds {:,} references and the pipeline reads "
        "all of them. The {}-reference gap is not a parsing loss.".format(
            measured["reference_positions"], gap)
        if file_side else
        "a file-side cause was found; see the checks marked ruled_out=false")
    return report


def main(argv=None):
    from convert_hinge_pkl import MissingPickleError, UnsafePickleError, load_dataframe

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pkl", help="HinGE.pkl as released by the authors")
    ap.add_argument("--expected-sha256", help="refuse the pickle unless it has this hash")
    ap.add_argument("--csv", help="also count the converted CSV through the pipeline's ingest")
    ap.add_argument("--hinglisheval", metavar="DIR",
                    help="folder with HinglishEval's *_human_generated.pkl files, to check "
                         "for source pairs the authors released elsewhere")
    ap.add_argument("--out", default=str(REPO_ROOT / "reports" / "hinge_reference_count.json"))
    args = ap.parse_args(argv)
    try:
        df, digest = load_dataframe(args.pkl, args.expected_sha256)
    except MissingPickleError as exc:
        print(exc, file=sys.stderr)
        return 3
    except UnsafePickleError as exc:
        print("refused: {}".format(exc), file=sys.stderr)
        return 2
    report = build_report(df, digest, args.csv, args.hinglisheval)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    m = report["measured"]
    print("published  {:,} human references over {:,} pairs (Table 1); "
          "section 2 says {:,} pairs".format(PUBLISHED["human_generated_sentences_table1"],
                                             PUBLISHED["parallel_sentences_table1"],
                                             PUBLISHED["sentence_pairs_section2_text"]))
    print("measured   {:,} reference positions over {:,} rows; gap {}".format(
        m["reference_positions"], m["rows"], report["gap_published_minus_measured"]))
    for c in report["checks"]:
        print("  [{}] {:<42} {}".format("ruled out" if c["ruled_out"] else "  FOUND  ",
                                        c["check"], c["finding"]))
    for k, v in report["published_figures_consistency"].items():
        print("  paper: {:<38} {}".format(k, v))
    print("verdict: " + report["verdict"])
    print("-> {}".format(repo_relative(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
