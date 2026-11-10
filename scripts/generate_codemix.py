#!/usr/bin/env python3
"""
Synthetic code-mixing under the Equivalence Constraint.  [298-17]

Reads a Romanised English/Hindi parallel TSV, aligns it with IBM Model 1, cuts
each sentence at order-preserving boundaries, and emits code-mixed sentences
sampled to match a target switch-point fraction rather than uniformly.

Usage
-----
  # the committed fixture: proves the pipeline runs, 30 sentences
  python3 scripts/generate_codemix.py

  # a real parallel corpus, once one is licensed and Romanised
  python3 scripts/generate_codemix.py --input data/raw/samanantar.roman.tsv \
      --target-spf 0.2398 --per-sentence 3 --seed 42

--target-spf defaults to the switch-point fraction measured on the real HinGE
corpus (0.2398, reports/data_statistics.json), so generated text is matched to
how much people actually switch instead of to what the generator finds easiest.

Output: a TSV of generated sentences and a JSON of what the run did, including
how many sentences were skipped and why.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative  # noqa: E402
from lrcs.data import codemix  # noqa: E402
from lrcs.text import sha256_file  # noqa: E402

DEFAULT_INPUT = REPO_ROOT / "data" / "codemix" / "parallel_fixture.tsv"
DEFAULT_OUTDIR = REPO_ROOT / "reports" / "codemix"
# Measured on the real corpus; see reports/data_statistics.json code_mixing.
HINGE_SPF = 0.2398

COLUMNS = ("source_index", "english", "hindi", "codemixed", "blocks",
           "switch_points", "spf", "alignment_coverage")


def write_tsv(path, rows):
    lines = ["\t".join(COLUMNS)]
    for row in rows:
        lines.append("\t".join(str(row[c]) for c in COLUMNS))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input", default=str(DEFAULT_INPUT),
                   help="TSV: english <tab> romanised hindi")
    p.add_argument("--target-spf", type=float, default=HINGE_SPF,
                   help="switch-point fraction to match (default: HinGE's)")
    p.add_argument("--per-sentence", type=int, default=1,
                   help="generated sentences per source pair. Raising this on a "
                        "small corpus exhausts the candidate pool and the SPF "
                        "target stops being reachable")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--em-iterations", type=int, default=codemix.DEFAULT_ITERATIONS)
    p.add_argument("--out-dir", default=str(DEFAULT_OUTDIR))
    p.add_argument("--stats-out", help="where to write the stats JSON (default: <out-dir>/"
                   "codemix_stats.json). Lets a licensed batch stay in gitignored data/interim "
                   "while its statistics are committed")
    p.add_argument("--gate-manifest", metavar="MANIFEST",
                   help="before writing, re-check every generated row's English source against "
                        "this split manifest's dev and test sources (lrcs.data.contamination); "
                        "any match halts with exit 3 and nothing is written")
    p.add_argument("--processed-dir", default=str(REPO_ROOT / "data" / "processed"),
                   help="where the split TSVs named by --gate-manifest live")
    args = p.parse_args(argv)

    try:
        pairs = codemix.read_parallel(args.input)
        rows, stats = codemix.generate(
            pairs, args.target_spf, args.per_sentence, args.seed,
            iterations=args.em_iterations)
    except codemix.CodeMixError as exc:
        print("code-mixing failed: {}".format(exc), file=sys.stderr)
        return 2

    gate_report = None
    if args.gate_manifest:
        from lrcs.data import contamination
        try:
            threshold, sources = contamination.load_split_sources(
                args.gate_manifest, args.processed_dir)
            index = contamination.ContaminationIndex(sources, threshold, seed=args.seed)
            english = sorted({r["english"] for r in rows})
            gate_report = contamination.gate([(e, "") for e in english], index)
        except contamination.ContaminationError as exc:
            print("HALTED: {}. Nothing written.".format(exc), file=sys.stderr)
            return 3
        print("  contamination gate PASSED: {:,} generated sources, 0 matches with {} at "
              "Jaccard >= {}".format(gate_report["candidates_checked"],
                                     " or ".join(gate_report["protected_splits"]),
                                     gate_report["threshold"]))

    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    tsv = outdir / "codemix_batch.tsv"
    write_tsv(tsv, rows)

    stats["input"] = repo_relative(Path(args.input))
    stats["output"] = repo_relative(tsv)
    stats["seed"] = args.seed
    stats["per_sentence"] = args.per_sentence
    stats["fixture"] = Path(args.input).resolve() == DEFAULT_INPUT.resolve()
    stats["input_sha256"] = sha256_file(Path(args.input))
    stats["output_sha256"] = sha256_file(tsv)
    if gate_report is not None:
        stats["contamination_gate"] = gate_report
    summary = Path(args.stats_out) if args.stats_out else outdir / "codemix_stats.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    print("  batch   -> {}".format(stats["output"]))
    print("  stats   -> {}".format(repo_relative(summary)))
    print("\n{:,} pairs in, {:,} sentences out".format(
        stats["pairs_in"], stats["rows_out"]))
    print("mean SPF {:.4f} against target {:.4f}{}".format(
        stats["mean_spf"], stats["target_mean_spf"],
        "" if stats["spf_within_0.05_of_target"] else "   OUT OF TOLERANCE"))
    print("mean alignment coverage {:.2f}".format(stats["mean_alignment_coverage"]))
    print("pool {:,} candidates, {:.0%} consumed".format(
        stats["candidate_pool"], stats["pool_utilisation"]))
    if stats["pool_exhausted"] and not stats["spf_within_0.05_of_target"]:
        print("  the target was missed because the batch consumed most of the "
              "pool, not because matching failed: lower --per-sentence or use "
              "a larger parallel corpus")
    skipped = {k: v for k, v in stats["skipped"].items() if v}
    if skipped:
        print("skipped: " + ", ".join("{} {}".format(v, k) for k, v in skipped.items()))
    if stats["fixture"]:
        print("\nThis is the 30-sentence fixture. It proves the pipeline runs; "
              "it is not a corpus and nothing should be trained on it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
