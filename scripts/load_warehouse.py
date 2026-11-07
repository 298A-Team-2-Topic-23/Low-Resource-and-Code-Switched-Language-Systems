#!/usr/bin/env python3
"""
Load pipeline outputs into the SQLite warehouse.  [298-70]

  python scripts/load_warehouse.py
  python scripts/load_warehouse.py --stats reports/data_statistics.json \\
      --processed-dir data/processed --db data/warehouse/lrcs.sqlite

Re-runs ingest+clean against the provenance input when that file is still on
disk, so raw / preprocessed / transformed tables are populated. Prepared rows
always come from the split TSVs. Reloading the same run_id replaces that run's
rows and leaves every other run alone.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for entry in (REPO_ROOT / "src",):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from lrcs.warehouse.load import open_and_load  # noqa: E402
from lrcs.warehouse.schema import DEFAULT_DB_PATH  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--stats", default=str(REPO_ROOT / "reports" / "data_statistics.json"),
                   help="pipeline statistics JSON")
    p.add_argument("--processed-dir", default=str(REPO_ROOT / "data" / "processed"))
    p.add_argument("--db", default=str(DEFAULT_DB_PATH))
    p.add_argument("--input", help="override the provenance input path for stage reload")
    p.add_argument("--lexicon", default=None)
    p.add_argument("--run-id", default=None, help="override the derived run_id")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    stats = Path(args.stats)
    if not stats.exists():
        print("missing statistics file: {}".format(stats), file=sys.stderr)
        print("run scripts/run_pipeline.py first", file=sys.stderr)
        return 2
    summary = open_and_load(
        args.db,
        stats,
        processed_dir=args.processed_dir,
        input_path=args.input,
        lexicon_path=args.lexicon,
        run_id=args.run_id,
    )
    print("warehouse <- {}".format(summary["db_path"]))
    print("  run_id         {}".format(summary["run_id"]))
    print("  source         {}".format(summary["source"]))
    print("  raw            {:,}".format(summary["raw"]))
    print("  preprocessed   {:,}".format(summary["preprocessed"]))
    print("  transformed    {:,}".format(summary["transformed"]))
    print("  prepared       {:,}".format(summary["prepared"]))
    if not summary["input_reloaded"]:
        print("  note           input file not found; raw/preprocessed/transformed empty")
        print("                 prepared + aggregates still loaded from TSVs and statistics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
