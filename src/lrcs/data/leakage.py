"""Stage 3 -- the leakage gate.  [298-38]

Runs after the splits are derived and BEFORE anything is written. If any English
source in one split is the same sentence as, or a near-duplicate of, a source in
another split, the gate raises LeakageError and the pipeline exits non-zero with
no manifest written. It halts; it does not warn.

Two checks, both on the normalised English source:

  exact  the same dedup key in two splits
  near   exact Jaccard of character 4-gram shingles >= threshold across splits

The near check uses the SAME threshold as dedupe (passed in from
--dup-threshold) but an INDEPENDENT MinHash seed. Dedupe and gate therefore
agree on what "duplicate" means, while a pair that LSH happened to miss during
dedupe gets a second, independent chance to be caught here.

If the gate halts in a demo: that is the gate working. The committed run passed.
"""

from collections import defaultdict

from lrcs.data.splits import near_duplicate_pairs
from lrcs.text import dedup_key

GATE_SEED_OFFSET = 0x5EED


class LeakageError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(
            "leakage gate: {} exact and {} near-duplicate source(s) shared across "
            "splits".format(report["exact_overlaps"], report["near_overlaps"])
        )


def check(splits, threshold, seed=0, max_examples=5):
    """Return a report dict. report['passed'] is False on any overlap."""
    split_of_key = defaultdict(set)
    for name, records in splits.items():
        for r in records:
            split_of_key[dedup_key(r["english"])].add(name)

    exact = sorted(k for k, names in split_of_key.items() if len(names) > 1)

    keys = sorted(split_of_key)
    near = []
    for i, j, sim in near_duplicate_pairs(keys, threshold, seed=seed + GATE_SEED_OFFSET):
        if split_of_key[keys[i]] != split_of_key[keys[j]]:
            near.append((keys[i], keys[j], sim))

    target_split = defaultdict(set)
    for name, records in splits.items():
        for r in records:
            target_split[dedup_key(r["hinglish"])].add(name)
    shared_targets = sum(1 for names in target_split.values() if len(names) > 1)

    return {
        "passed": not exact and not near,
        "threshold": threshold,
        "sources_checked": len(keys),
        "exact_overlaps": len(exact),
        "near_overlaps": len(near),
        "exact_examples": exact[:max_examples],
        "near_examples": [
            {"a": a, "b": b, "jaccard": round(sim, 4)} for a, b, sim in near[:max_examples]
        ],
        # Not gated: two different English sources may legitimately share a short
        # Hinglish rendering. Reported so a reviewer can see it was looked at.
        "info_identical_targets_across_splits": shared_targets,
    }


def gate(splits, threshold, seed=0):
    report = check(splits, threshold, seed=seed)
    if not report["passed"]:
        raise LeakageError(report)
    return report


def print_report(report):
    status = "PASSED" if report["passed"] else "HALTED"
    print("  leakage gate {}: {:,} sources checked at Jaccard >= {} -- "
          "{} exact, {} near-duplicate overlaps".format(
              status, report["sources_checked"], report["threshold"],
              report["exact_overlaps"], report["near_overlaps"]))
    for key in report["exact_examples"]:
        print("    exact: {!r}".format(key))
    for ex in report["near_examples"]:
        print("    near ({:.2f}): {!r} ~ {!r}".format(ex["jaccard"], ex["a"], ex["b"]))
