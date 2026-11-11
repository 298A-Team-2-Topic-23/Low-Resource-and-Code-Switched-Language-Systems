#!/usr/bin/env python3
"""
Audit the overlap between HinglishEval's released train / valid / test files.  [298-64]

HinglishEval (INLG 2022 shared task) reuses HinGE's English sources and ships its
own train/valid/test CSVs in the same Drive folder as HinGE.pkl
(docs/datasheet.md). The project never uses those splits, because they are not
disjoint. The 25 September audit that established this was never committed;
this script is that audit, re-runnable.

    python scripts/audit_hinglisheval_overlap.py "data/raw/HinglishEval-- INLG 2022 shared task"

Sources are compared on the pipeline's own dedup key (lrcs.text.dedup_key:
NFKC, lower-case, punctuation stripped), the same key the leakage gate uses.
Output: reports/hinglisheval_overlap.json -- counts only, no sentences.
"""

import argparse
import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative  # noqa: E402
from lrcs.text import dedup_key, sha256_file  # noqa: E402

FILES = ("train.csv", "valid.csv", "test.csv")


def sources(path):
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    with open(str(path), encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    return rows, {dedup_key(r["English"]) for r in rows}


def audit(directory):
    directory = Path(directory)
    data = OrderedDict()
    for name in FILES:
        path = directory / name
        if not path.exists():
            raise FileNotFoundError(
                "{}: not found. HinglishEval is in the HinGE Drive folder linked from "
                "docs/datasheet.md".format(path))
        rows, keys = sources(path)
        data[name.split(".")[0]] = {"path": path, "rows": len(rows), "keys": keys}

    def overlap(a, b):
        shared = data[a]["keys"] & data[b]["keys"]
        n = len(data[a]["keys"])
        return OrderedDict([("shared_sources", len(shared)), ("of", n),
                            ("share", round(len(shared) / n, 4) if n else 0.0)])

    return OrderedDict([
        ("files", OrderedDict(
            (k, OrderedDict([("sha256", sha256_file(v["path"])), ("rows", v["rows"]),
                             ("unique_sources", len(v["keys"]))]))
            for k, v in data.items())),
        ("key", "lrcs.text.dedup_key"),
        ("valid_sources_also_in_train", overlap("valid", "train")),
        ("test_sources_also_in_train", overlap("test", "train")),
        ("test_sources_also_in_valid", overlap("test", "valid")),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("directory", help="folder holding HinglishEval's train/valid/test CSVs")
    ap.add_argument("--out", default=str(REPO_ROOT / "reports" / "hinglisheval_overlap.json"))
    args = ap.parse_args(argv)
    try:
        report = audit(args.directory)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for label in ("valid_sources_also_in_train", "test_sources_also_in_train",
                  "test_sources_also_in_valid"):
        o = report[label]
        print("{:<30} {:>4} of {:>4}  ({:.1%})".format(label, o["shared_sources"], o["of"], o["share"]))
    print("-> {}".format(repo_relative(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
