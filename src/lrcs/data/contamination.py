"""Contamination check for synthetic training data.  [298-58, shared with 298-76]

The leakage gate (leakage.py) compares our three splits with each other. It
cannot see a corpus we pull in from outside. Model 4 trains on synthetic pairs
generated from a parallel corpus, and HinGE's English sources come from the IIT
Bombay corpus, which is itself part of Samanantar. A Samanantar pair whose
English is a HinGE dev or test source would put that sentence into training by
the back door, and every M4 number would be scored partly on training data.

So this module answers one question about every candidate pair, **before any
synthetic text is generated from it**: is it one of our evaluation sources?

  exact        same normalised English key (lrcs.text.dedup_key) as a protected source
  near         character 4-gram Jaccard >= the threshold the splits were derived with
  hindi_exact  same normalised Hindi text as a protected source, whatever the English

The near check reuses the gate's own machinery -- the same shingles, the same
MinHash, the same exact-Jaccard verification of every LSH candidate -- and the
threshold is read from the frozen split manifest, not passed in by hand. When
dedupe and the gate once used different thresholds, pairs between the two
values slipped through; this check cannot drift from the gate the same way.

Protected sources are read from the split TSVs, and each file is checked
against its manifest hash first. Checking against a split that is not the
frozen split would prove nothing.

Back-translation (298-58) and code-mixing (298-76) both produce synthetic
training data, so both run this one check rather than two.
"""

import csv
import json
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

from lrcs import repo_relative
from lrcs.data.splits import NUM_PERM, ROWS_PER_BAND, MinHasher, jaccard, shingles
from lrcs.text import dedup_key, sha256_file

SPLITS = ("train", "dev", "test")
# The splits a synthetic training corpus must never contain. Train overlap is
# reported but allowed: training on a train source again is not leakage.
DEFAULT_PROTECTED = ("dev", "test")
CHECK_SEED_OFFSET = 0xC0DE


class ContaminationError(RuntimeError):
    pass


def load_split_sources(manifest_path, processed_dir):
    """Return (threshold, {split: [(english, hindi), ...]}) for the frozen splits.

    Raises ContaminationError if a split file is missing or does not match the
    manifest hash.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise ContaminationError("{}: no split manifest".format(repo_relative(manifest_path)))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    threshold = manifest["params"]["dup_threshold"]
    source = manifest["source"]
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    out = OrderedDict()
    for name in SPLITS:
        path = Path(processed_dir) / source / "{}.tsv".format(name)
        if not path.exists():
            raise ContaminationError(
                "{}: not found. The split files are gitignored; regenerate them with "
                "scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42 "
                "(docs/datasheet.md says where to get the input)".format(repo_relative(path)))
        if sha256_file(path) != manifest["splits"][name]["sha256"]:
            raise ContaminationError(
                "{}: does not match the manifest hash, so it is not the frozen split".format(
                    repo_relative(path)))
        with open(str(path), encoding="utf-8", newline="") as fh:
            rows = csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
            out[name] = [(r["english"], r["hindi"]) for r in rows]
    return threshold, out


class ContaminationIndex:
    """LSH index over the protected English sources, queried one candidate at a time."""

    def __init__(self, split_sources, threshold, seed=0,
                 num_perm=NUM_PERM, rows=ROWS_PER_BAND):
        self.threshold = threshold
        self.rows = rows
        self.bands = num_perm // rows
        self.hasher = MinHasher(num_perm, seed + CHECK_SEED_OFFSET)
        self.split_of_key = defaultdict(set)
        self.split_of_hindi = defaultdict(set)
        for name, pairs in split_sources.items():
            for english, hindi in pairs:
                self.split_of_key[dedup_key(english)].add(name)
                if hindi and hindi.strip():
                    self.split_of_hindi[dedup_key(hindi)].add(name)
        self.keys = sorted(self.split_of_key)
        self.key_index = {k: i for i, k in enumerate(self.keys)}
        self.shingles = [shingles(k) for k in self.keys]
        self.buckets = [defaultdict(list) for _ in range(self.bands)]
        for i, s in enumerate(self.shingles):
            sig = self.hasher.signature(s)
            for b in range(self.bands):
                self.buckets[b][sig[b * rows:(b + 1) * rows]].append(i)

    def query(self, english, hindi=""):
        """Return a list of hits: (kind, split, similarity, protected_key_index)."""
        key = dedup_key(english)
        hits = []
        for name in sorted(self.split_of_key.get(key, ())):
            hits.append(("exact", name, 1.0, self.key_index[key]))
        if hindi and hindi.strip():
            for name in sorted(self.split_of_hindi.get(dedup_key(hindi), ())):
                hits.append(("hindi_exact", name, 1.0, None))
        if hits:
            return hits
        s = shingles(key)
        sig = self.hasher.signature(s)
        candidates = set()
        for b in range(self.bands):
            candidates.update(self.buckets[b].get(sig[b * self.rows:(b + 1) * self.rows], ()))
        for i in sorted(candidates):
            sim = jaccard(s, self.shingles[i])
            if sim >= self.threshold:
                for name in sorted(self.split_of_key[self.keys[i]]):
                    hits.append(("near", name, sim, i))
        return hits


def check_pairs(pairs, index, protected=DEFAULT_PROTECTED, max_examples=5):
    """Check (english, hindi) candidate pairs. Returns (kept_indices, report).

    A pair is removed if it hits a protected split by any of the three checks.
    Hits on unprotected splits (train) are counted and kept.
    """
    protected = set(protected)
    kept, removed = [], []
    counts = OrderedDict((kind, OrderedDict((s, 0) for s in SPLITS))
                         for kind in ("exact", "near", "hindi_exact"))
    examples = []
    for i, (english, hindi) in enumerate(pairs):
        hits = index.query(english, hindi)
        for kind, split, _sim, _ in hits:
            counts[kind][split] += 1
        bad = [h for h in hits if h[1] in protected]
        if bad:
            removed.append(i)
            if len(examples) < max_examples:
                kind, split, sim, _ = bad[0]
                examples.append(OrderedDict([("candidate_index", i), ("kind", kind),
                                             ("split", split), ("jaccard", round(sim, 4))]))
        else:
            kept.append(i)
    report = OrderedDict([
        ("threshold", index.threshold),
        ("protected_splits", sorted(protected)),
        ("candidates_checked", len(pairs)),
        ("removed", len(removed)),
        ("kept", len(kept)),
        ("hits", counts),
        ("examples", examples),
        ("passed", None),
    ])
    return kept, report


def gate(pairs, index, protected=DEFAULT_PROTECTED):
    """Check an already-filtered corpus. Raises if anything protected remains --
    the same halt-not-warn rule as the split gate."""
    kept, report = check_pairs(pairs, index, protected)
    report["passed"] = report["removed"] == 0
    if not report["passed"]:
        raise ContaminationError(
            "contamination gate: {} candidate pair(s) match a protected source".format(
                report["removed"]))
    return report
