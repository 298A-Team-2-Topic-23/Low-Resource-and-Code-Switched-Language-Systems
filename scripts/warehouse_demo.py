#!/usr/bin/env python3
"""
Run the warehouse demo queries and print the result tables.  [298-70]

  python scripts/warehouse_demo.py
  python scripts/warehouse_demo.py --db data/warehouse/lrcs.sqlite

Expects a prior `scripts/load_warehouse.py` load. Each query file under
warehouse/queries/ is executed in order so a viewer can watch the evidence
for sections 3.3–3.6 come off a real SQL store.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for entry in (REPO_ROOT / "src",):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from lrcs.warehouse.schema import DEFAULT_DB_PATH  # noqa: E402

QUERIES_DIR = REPO_ROOT / "warehouse" / "queries"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--db", default=str(DEFAULT_DB_PATH))
    p.add_argument("--queries", default=str(QUERIES_DIR))
    return p.parse_args(argv)


def _print_table(columns, rows):
    if not columns:
        print("  (no columns)")
        return
    widths = [len(c) for c in columns]
    str_rows = []
    for row in rows:
        cells = []
        for i, col in enumerate(columns):
            val = row[i] if not isinstance(row, sqlite3.Row) else row[col]
            text = "" if val is None else str(val)
            cells.append(text)
            widths[i] = max(widths[i], len(text))
        str_rows.append(cells)
    header = "  ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    print(header)
    print("  ".join("-" * w for w in widths))
    for cells in str_rows:
        print("  ".join(cells[i].ljust(widths[i]) for i in range(len(columns))))


def main(argv=None):
    args = parse_args(argv)
    db = Path(args.db)
    if not db.exists():
        print("warehouse DB missing: {}".format(db), file=sys.stderr)
        print("run: python scripts/load_warehouse.py", file=sys.stderr)
        return 2
    qdir = Path(args.queries)
    files = sorted(qdir.glob("*.sql"))
    if not files:
        print("no query files in {}".format(qdir), file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db))
    try:
        n = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        if n == 0:
            print("warehouse is empty — load a run first", file=sys.stderr)
            return 2
        for path in files:
            sql = path.read_text(encoding="utf-8")
            print("\n== {} ==".format(path.name))
            cur = conn.execute(sql)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            _print_table(columns, rows)
            print("  ({} row{})".format(len(rows), "" if len(rows) == 1 else "s"))
    finally:
        conn.close()
    print("\ndemo queries OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
