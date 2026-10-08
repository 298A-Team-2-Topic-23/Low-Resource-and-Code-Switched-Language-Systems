#!/usr/bin/env python3
"""
One command, all four data-pipeline stages.  [298-38]

  1 ingest   provenance table: path, timestamps, bytes, SHA-256, measured rows
  2 clean    six filters, attrition table, LinCE-style language tags
  3 split    near-duplicate grouping, disjoint splits, LEAKAGE GATE, manifests
  4 eda      statistics, spelling variance, four figures, data_statistics.json

Usage
-----
  # offline, no data needed -- what the demo runs if the network is down
  python scripts/run_pipeline.py --synthetic --n-synthetic 1200

  # the real corpus (data/raw/ is gitignored; see docs/datasheet.md)
  python scripts/run_pipeline.py --input data/raw/hinge.csv

`PYTHONPATH=src` is not needed: this script puts src/ on the path itself.

Exit codes: 0 ok, 2 bad input, 3 leakage gate halted, 4 degenerate split.
If the gate halts, nothing is written to the manifests directory. Do not bypass
it -- the gate catching an overlap is the gate working.

--dup-threshold is shared by dedupe and the leakage gate on purpose. With two
separate thresholds, pairs between the two values passed dedupe and then failed
the gate on clean data.
"""

import argparse
import sys
import time
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for entry in (REPO_ROOT / "src", REPO_ROOT / "common"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from lrcs import repo_relative  # noqa: E402
from lrcs.analysis import eda  # noqa: E402
from lrcs.data import clean as clean_stage  # noqa: E402
from lrcs.data import ingest, leakage, splits  # noqa: E402
from lrcs.lexicon import DEFAULT_LEXICON, load_variant_groups  # noqa: E402


def banner(n, title):
    print("\n[stage {}] {}".format(n, title))
    print("-" * 64)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="CSV/TSV with English and Hinglish columns")
    src.add_argument("--synthetic", action="store_true", help="generate a synthetic corpus (offline)")
    p.add_argument("--n-synthetic", type=int, default=1200, help="rows to generate with --synthetic")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dup-threshold", type=float, default=0.7,
                   help="char 4-gram Jaccard at which two sources count as duplicates; "
                        "shared by dedupe AND the leakage gate")
    p.add_argument("--ratios", type=float, nargs=3, default=[0.8, 0.1, 0.1],
                   metavar=("TRAIN", "DEV", "TEST"))
    p.add_argument("--max-group-frac", type=float, default=0.05,
                   help="halt if one near-duplicate group exceeds this share of records")
    p.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    p.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw"))
    p.add_argument("--processed-dir", default=str(REPO_ROOT / "data" / "processed"))
    p.add_argument("--manifest-dir", default=str(REPO_ROOT / "data" / "processed" / "manifests"))
    p.add_argument("--reports-dir", default=str(REPO_ROOT / "reports"))
    p.add_argument("--runs-dir", default=None, help="RunLogger output (default: runs/)")
    p.add_argument("--no-run-log", action="store_true", help="do not write a runs/*.json record")
    p.add_argument("--no-figures", action="store_true", help="skip stage-4 figures (statistics only)")
    p.add_argument("--inject-leak", type=int, default=0, metavar="K",
                   help="DEMO ONLY: copy K test sources into train before the gate, to show it halting")
    return p.parse_args(argv)


def run(args):
    t0 = time.time()
    timings = OrderedDict()
    lexicon = load_variant_groups(args.lexicon)
    if not lexicon:
        print("warning: no variant lexicon at {} -- spelling variance will be empty".format(args.lexicon))

    banner(1, "ingest -- provenance and measured counts")
    t = time.time()
    if args.synthetic:
        records, prov = ingest.ingest_synthetic(args.n_synthetic, args.seed, args.raw_dir, lexicon=lexicon)
    else:
        records, prov = ingest.ingest_file(args.input)
    ingest.print_provenance(prov)
    timings["ingest"] = time.time() - t

    banner(2, "clean -- six filters, attrition, language tags")
    t = time.time()
    kept, attrition = clean_stage.clean(records, lexicon=lexicon)
    clean_stage.print_attrition(attrition)
    timings["clean"] = time.time() - t

    banner(3, "split -- dedupe, disjoint splits, leakage gate, manifests")
    t = time.time()
    ratios = OrderedDict(zip(("train", "dev", "test"), args.ratios))
    derived, info = splits.derive_splits(
        kept, ratios, args.dup_threshold, args.seed, max_group_frac=args.max_group_frac)
    splits.print_split_summary(derived, info)
    if args.inject_leak:
        moved = derived["test"][: args.inject_leak]
        derived["train"].extend(dict(r) for r in moved)
        print("  DEMO: injected {} test source(s) into train".format(len(moved)))
    report = leakage.check(derived, args.dup_threshold, seed=args.seed)
    leakage.print_report(report)
    if not report["passed"]:
        raise leakage.LeakageError(report)
    params = OrderedDict([
        ("seed", args.seed), ("dup_threshold", args.dup_threshold),
        ("ratios", dict(ratios)), ("max_group_frac", args.max_group_frac),
        ("shingle", splits.SHINGLE), ("num_perm", splits.NUM_PERM),
        ("rows_per_band", splits.ROWS_PER_BAND), ("clean", attrition["params"]),
    ])
    manifest_path, manifest = splits.write_splits(
        derived, info, prov, params, args.processed_dir, args.manifest_dir)
    splits.print_manifest(manifest_path, manifest)
    timings["split"] = time.time() - t

    banner(4, "eda -- statistics, spelling variance, figures")
    t = time.time()
    stats, series = eda.compute_statistics(
        derived, prov, attrition, info, report, lexicon, params, manifest_path=manifest_path)
    eda.print_statistics(stats)
    figures = {} if args.no_figures else eda.write_figures(stats, series, Path(args.reports_dir) / "figures")
    timings["eda"] = time.time() - t
    stats["figures"] = figures
    stats["timings_seconds"] = OrderedDict((k, round(v, 2)) for k, v in timings.items())
    stats["elapsed_seconds"] = round(time.time() - t0, 2)
    stats_path = eda.write_statistics(stats, Path(args.reports_dir) / "data_statistics.json")
    for path in figures.values():
        print("  figure -> {}".format(path))
    print("  statistics -> {}".format(stats_path))

    print("\npipeline OK in {:.1f}s  ({})".format(
        stats["elapsed_seconds"],
        ", ".join("{} {:.1f}s".format(k, v) for k, v in timings.items())))
    return stats


def main(argv=None):
    args = parse_args(argv)
    from repro import RunLogger, set_seed

    set_seed(args.seed)
    config = {k: v for k, v in vars(args).items() if k not in {"runs_dir", "no_run_log"}}
    for key in ("input", "lexicon", "raw_dir", "processed_dir", "manifest_dir", "reports_dir"):
        config[key] = repo_relative(config[key])
    try:
        if args.no_run_log:
            run(args)
        else:
            # n_gpus=0: a CPU job, so it is logged but adds nothing to GPU-hours
            with RunLogger("data-pipeline", seed=args.seed, config=config,
                           outdir=args.runs_dir, n_gpus=0) as log:
                stats = run(args)
                log.log_metric("records_ingested", stats["attrition"]["ingested"])
                log.log_metric("records_kept", stats["attrition"]["kept"])
                for name, s in stats["splits"].items():
                    log.log_metric("records_" + name, s["records"])
                log.log_metric("leakage_gate_passed", stats["leakage_gate"]["passed"])
    except ingest.IngestError as exc:
        print("\ningest failed: {}".format(exc), file=sys.stderr)
        return 2
    except leakage.LeakageError as exc:
        print("\nHALTED: {}. No manifest written. That is the gate working; "
              "do not bypass it.".format(exc), file=sys.stderr)
        return 3
    except splits.SplitError as exc:
        print("\nsplit failed: {}".format(exc), file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
