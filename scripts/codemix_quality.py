#!/usr/bin/env python3
"""
Automatic quality indicators for a generated code-mix batch.  [298-76]

The generator's own statistics say how much the batch switches. They say
nothing about whether the sentences read as language. This script counts two
defects that can be detected without a human, so a batch that meets its
switch-point target cannot be mistaken for a batch that is fit to train on:

  repeated_token  a word occurs more often in the output than in the English
                  and Romanised Hindi sources together allow ("agencies put
                  agencies"); a symptom of many-to-one alignment links
  english_order   a pair of English words appears in the output in the
                  opposite order to the English source; a symptom of blocks
                  being realised in Hindi word order

    python scripts/codemix_quality.py data/interim/codemix/codemix_batch.tsv \\
        --out reports/codemix/samanantar_quality.json

Counts only; no sentence text is written.
"""

import argparse
import csv
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative  # noqa: E402
from lrcs.text import sha256_file  # noqa: E402


def repeated_token(row):
    out = Counter(row["codemixed"].lower().split())
    allowed = Counter(row["english"].lower().split()) + Counter(row["hindi"].lower().split())
    return any(n > allowed.get(tok, 0) for tok, n in out.items())


def english_inversions(row):
    """Share of ordered English-word pairs, among those unique in both strings,
    whose order in the output is the reverse of the source."""
    src = row["english"].lower().split()
    out = row["codemixed"].lower().split()
    src_unique = [w for w in src if src.count(w) == 1]
    pos = {w: out.index(w) for w in src_unique if out.count(w) == 1}
    words = [w for w in src_unique if w in pos]
    pairs = inverted = 0
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            pairs += 1
            inverted += pos[words[i]] > pos[words[j]]
    return pairs, inverted


def quality(path):
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    with open(str(path), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))
    if not rows:
        raise SystemExit("{}: no rows".format(path))
    rep = sum(1 for r in rows if repeated_token(r))
    pairs = inverted = rows_with_inversion = 0
    for r in rows:
        p, inv = english_inversions(r)
        pairs += p
        inverted += inv
        rows_with_inversion += inv > 0
    clean = sum(1 for r in rows if not repeated_token(r) and english_inversions(r)[1] == 0)
    return OrderedDict([
        ("batch", repo_relative(Path(path))),
        ("sha256", sha256_file(path)),
        ("rows", len(rows)),
        ("rows_with_repeated_token", rep),
        ("share_with_repeated_token", round(rep / len(rows), 4)),
        ("rows_with_english_order_inversion", rows_with_inversion),
        ("share_with_english_order_inversion", round(rows_with_inversion / len(rows), 4)),
        ("english_word_pairs_inverted", round(inverted / pairs, 4) if pairs else 0.0),
        ("rows_with_neither_defect", clean),
        ("share_with_neither_defect", round(clean / len(rows), 4)),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("batch")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    report = quality(args.batch)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("{:,} rows: {:.1%} repeat a token, {:.1%} invert English word order, "
          "{:.1%} have neither".format(report["rows"], report["share_with_repeated_token"],
                                       report["share_with_english_order_inversion"],
                                       report["share_with_neither_defect"]))
    print("-> {}".format(repo_relative(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
