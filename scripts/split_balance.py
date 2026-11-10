#!/usr/bin/env python3
"""
Per-split composition of the frozen splits.  [298-64]

The splits are not stratified: stage 3 assigns whole near-duplicate groups by a
seeded shuffle (src/lrcs/data/splits.py). Section 3.5 says so, and this script
is the check that the shuffle did not leave the three splits looking different
anyway. It reads the split TSVs the pipeline wrote, checks them against the
committed manifest, and reports per split:

  records, share, unique sources, groups, references per source,
  sources with a single reference, English and Hinglish length,
  and the code-mixing statistics the pipeline uses (CMI, SPF, share mixed,
  tagger coverage), computed with the pipeline's own tagger.

    python scripts/split_balance.py                      # HinGE, the default
    python scripts/split_balance.py --source synthetic   # offline

Output: reports/split_balance_<source>.json -- aggregates only, no sentences,
so it is safe to commit. Exit 2 if the split files are missing or no longer
match the manifest hashes (a split that does not match its manifest is not the
frozen split, and describing it would be describing something else).
"""

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative  # noqa: E402
from lrcs.analysis.codemixing import corpus_stats  # noqa: E402
from lrcs.data.clean import hindi_markers, tag_tokens  # noqa: E402
from lrcs.text import dedup_key, sha256_file, word_tokens  # noqa: E402

SPLITS = ("train", "dev", "test")


class BalanceError(RuntimeError):
    pass


def read_split(path):
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    with open(str(path), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))


def describe(rows, total, markers):
    sources = Counter(dedup_key(r["english"]) for r in rows)
    en_len = [len(word_tokens(r["english"])) for r in rows]
    hi_len = [len(word_tokens(r["hinglish"])) for r in rows]
    tags = [[t for _, t in tag_tokens(r["hinglish"], r["english"], markers)] for r in rows]
    cm = corpus_stats(tags)
    return OrderedDict([
        ("records", len(rows)),
        ("share_of_records", round(len(rows) / total, 4) if total else 0.0),
        ("unique_sources", len(sources)),
        ("groups", len({r["group"] for r in rows})),
        ("references_per_source", round(len(rows) / len(sources), 3) if sources else 0.0),
        ("single_reference_sources", sum(1 for n in sources.values() if n == 1)),
        ("english_words_mean", round(statistics.mean(en_len), 2) if en_len else 0.0),
        ("english_words_median", statistics.median(en_len) if en_len else 0),
        ("hinglish_words_mean", round(statistics.mean(hi_len), 2) if hi_len else 0.0),
        ("cmi_mean_all", round(cm["cmi_mean_all"], 2)),
        ("frac_sentences_mixed", round(cm["frac_sentences_mixed"], 4)),
        ("spf", round(cm["switch_point_fraction"], 4)),
        ("tagger_coverage", round(cm["tagger_coverage"], 4)),
    ])


def balance(source, processed_dir, manifest_dir):
    manifest_path = Path(manifest_dir) / "{}_split_manifest.json".format(source)
    if not manifest_path.exists():
        raise BalanceError("{}: no manifest; run scripts/run_pipeline.py first".format(
            repo_relative(manifest_path)))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = {}
    for name in SPLITS:
        path = Path(processed_dir) / source / "{}.tsv".format(name)
        if not path.exists():
            raise BalanceError(
                "{}: not found. Split files are gitignored; regenerate them with "
                "scripts/run_pipeline.py (the HinGE input is in docs/datasheet.md)".format(
                    repo_relative(path)))
        expected = manifest["splits"][name]["sha256"]
        actual = sha256_file(path)
        if actual != expected:
            raise BalanceError(
                "{}: sha256 {} does not match the manifest's {}. This is not the "
                "frozen split.".format(repo_relative(path), actual[:12], expected[:12]))
        data[name] = read_split(path)

    total = sum(len(rows) for rows in data.values())
    markers = hindi_markers()
    report = OrderedDict([
        ("source", source),
        ("manifest", repo_relative(manifest_path)),
        ("input_sha256", manifest["input_sha256"]),
        ("split_files_match_manifest", True),
        ("stratified", False),
        ("assignment", "whole near-duplicate groups, seeded shuffle, each group to the "
                       "split furthest below its record target (src/lrcs/data/splits.py)"),
        ("splits", OrderedDict((name, describe(data[name], total, markers))
                               for name in SPLITS)),
    ])
    report["merged_groups"] = merged_groups(data)
    return report


def merged_groups(data):
    """Groups that hold more than one distinct source: the near-duplicate merges.
    Reported as split, group size and record count only -- the group id is the
    normalised English sentence, and this file carries no corpus text."""
    out = []
    for name in SPLITS:
        by_group = {}
        for r in data[name]:
            by_group.setdefault(r["group"], set()).add(dedup_key(r["english"]))
        for group, keys in sorted(by_group.items()):
            if len(keys) > 1:
                out.append(OrderedDict([
                    ("split", name),
                    ("sources_in_group", len(keys)),
                    ("records", sum(1 for r in data[name] if r["group"] == group)),
                ]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", default="hinge")
    ap.add_argument("--processed-dir", default=str(REPO_ROOT / "data" / "processed"))
    ap.add_argument("--manifest-dir",
                    default=str(REPO_ROOT / "data" / "processed" / "manifests"))
    ap.add_argument("--out", help="default: reports/split_balance_<source>.json")
    args = ap.parse_args(argv)
    try:
        report = balance(args.source, args.processed_dir, args.manifest_dir)
    except BalanceError as exc:
        print("split balance: {}".format(exc), file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else (
        REPO_ROOT / "reports" / "split_balance_{}.json".format(args.source))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("split    records   share  sources  groups  refs/src  en-words  CMI    mixed  SPF")
    for name, s in report["splits"].items():
        print("{:<7}{:>9,}  {:>6.2%}  {:>7,}  {:>6,}  {:>8.2f}  {:>8.1f}  {:>5.1f}  {:>5.1%}  {}".format(
            name, s["records"], s["share_of_records"], s["unique_sources"], s["groups"],
            s["references_per_source"], s["english_words_mean"], s["cmi_mean_all"],
            s["frac_sentences_mixed"], s["spf"]))
    print("-> {}".format(repo_relative(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
