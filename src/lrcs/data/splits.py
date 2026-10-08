"""Stage 3 -- dedupe + split derivation.  [298-38]

Why splits are re-derived at all: HinGE's downstream released train/dev files
are not disjoint (docs/datasheet.md records 285 of dev's 376 unique English
sources also in train). This stage never reads a released split; it derives
its own from the cleaned records.

How
---
1. Every record is keyed by its normalised English source (text.dedup_key).
   All references of one source share a key, so they cannot be split up.
2. Keys are grouped as near-duplicates when the exact Jaccard similarity of
   their character 4-gram shingles is >= --dup-threshold. Candidates come from
   MinHash/LSH, every candidate is then verified exactly, so LSH can only cause
   a miss, never a false merge.
3. Whole groups are assigned to train/dev/test by a seeded shuffle, so a
   paraphrase pair can never straddle a boundary.

The SAME threshold is used by the leakage gate (leakage.py). When dedupe and the
gate used different thresholds, pairs between the two values passed dedupe as
"different" and then failed the gate as "leaked" on clean data. One knob, both
sides.

Pure standard library: no datasketch dependency, so the demo runs on a fresh
clone with nothing but matplotlib installed for the figures.
"""

import hashlib
import json
import random
from collections import OrderedDict, defaultdict
from pathlib import Path

from lrcs import repo_relative
from lrcs.text import dedup_key, sha256_bytes

SHINGLE = 4
NUM_PERM = 96
ROWS_PER_BAND = 3          # 32 bands x 3 rows: P(candidate | J=0.7) > 0.99999
_MERSENNE = (1 << 61) - 1


class SplitError(RuntimeError):
    pass


# ----------------------------------------------------------------- similarity

def shingles(key, k=SHINGLE):
    if len(key) < k:
        return {key} if key else set()
    return {key[i:i + k] for i in range(len(key) - k + 1)}


def jaccard(a, b):
    if not a and not b:
        return 1.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def _hash64(text):
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")


class MinHasher:
    """Universal hashing (a*x + b) mod p over 64-bit shingle hashes."""

    def __init__(self, num_perm=NUM_PERM, seed=0):
        rng = random.Random(seed)
        self.params = [
            (rng.randrange(1, _MERSENNE), rng.randrange(0, _MERSENNE))
            for _ in range(num_perm)
        ]

    def signature(self, shingle_set):
        hashed = [_hash64(s) for s in shingle_set] or [0]
        return tuple(min((a * x + b) % _MERSENNE for x in hashed) for a, b in self.params)


def near_duplicate_pairs(keys, threshold, seed=0, num_perm=NUM_PERM, rows=ROWS_PER_BAND):
    """Return [(i, j, jaccard)] for every pair of keys with exact Jaccard >=
    threshold that LSH proposed as a candidate. keys must be unique."""
    sets = [shingles(k) for k in keys]
    hasher = MinHasher(num_perm, seed)
    sigs = [hasher.signature(s) for s in sets]
    candidates = set()
    for band in range(num_perm // rows):
        buckets = defaultdict(list)
        lo = band * rows
        for i, sig in enumerate(sigs):
            buckets[sig[lo:lo + rows]].append(i)
        for members in buckets.values():
            if len(members) < 2:
                continue
            for x in range(len(members)):
                for y in range(x + 1, len(members)):
                    candidates.add((members[x], members[y]))
    pairs = []
    for i, j in sorted(candidates):
        sim = jaccard(sets[i], sets[j])
        if sim >= threshold:
            pairs.append((i, j, sim))
    return pairs


# ------------------------------------------------------------------- grouping

class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # attach the larger index to the smaller: the surviving root is a
            # property of the inputs, not of the order unions arrive in
            lo, hi = (ra, rb) if ra < rb else (rb, ra)
            self.parent[hi] = lo


def group_sources(records, threshold, seed=0):
    """Return (key_of_record, group_of_key, n_near_dup_pairs). Group ids are the
    lexicographically smallest key in the group, so they depend only on content."""
    record_keys = [dedup_key(r["english"]) for r in records]
    keys = sorted(set(record_keys))
    pairs = near_duplicate_pairs(keys, threshold, seed=seed)
    uf = _UnionFind(len(keys))
    for i, j, _ in pairs:
        uf.union(i, j)
    canonical = {}
    for i, key in enumerate(keys):
        root = uf.find(i)
        if root not in canonical or key < canonical[root]:
            canonical[root] = key
    group_of_key = {key: canonical[uf.find(i)] for i, key in enumerate(keys)}
    return record_keys, group_of_key, len(pairs)


# ----------------------------------------------------------------- assignment

def assign_groups(group_sizes, ratios, seed):
    """Seeded shuffle of group ids (sorted first, so set order cannot leak in),
    then each group goes to the split furthest below its record target."""
    names = list(ratios)
    total = sum(group_sizes.values())
    target = {name: ratios[name] * total for name in names}
    filled = {name: 0 for name in names}
    order = sorted(group_sizes)
    random.Random(seed).shuffle(order)
    assignment = {}
    for gid in order:
        best = max(names, key=lambda s: (target[s] - filled[s]) / max(target[s], 1e-9))
        assignment[gid] = best
        filled[best] += group_sizes[gid]
    return assignment


def derive_splits(records, ratios, threshold, seed, max_group_frac=0.05):
    """Returns (splits, info). splits: OrderedDict name -> list of records."""
    if abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise SplitError("split ratios must sum to 1, got {}".format(ratios))
    if not records:
        raise SplitError("no records survived cleaning; nothing to split")
    record_keys, group_of_key, n_pairs = group_sources(records, threshold, seed=seed)
    group_sizes = defaultdict(int)
    for key in record_keys:
        group_sizes[group_of_key[key]] += 1
    largest = max(group_sizes.values())
    if largest > max(max_group_frac * len(records), 2):
        # One giant cluster means the threshold is chaining unrelated sentences
        # together -- the split would be dominated by one group and the ratios
        # would be meaningless. Halt rather than write a degenerate split.
        raise SplitError(
            "degenerate clustering: largest near-duplicate group holds {} of {} "
            "records (> {:.0%}). Raise --dup-threshold.".format(
                largest, len(records), max_group_frac))
    assignment = assign_groups(dict(group_sizes), ratios, seed)
    splits = OrderedDict((name, []) for name in ratios)
    for record, key in zip(records, record_keys):
        record["group"] = group_of_key[key]
        splits[assignment[group_of_key[key]]].append(record)
    for name in splits:
        splits[name].sort(key=lambda r: r["id"])
    info = {
        "unique_sources": len(group_of_key),
        "groups": len(group_sizes),
        "near_duplicate_pairs": n_pairs,
        "sources_merged_by_near_dup": len(group_of_key) - len(group_sizes),
        "largest_group": largest,
    }
    return splits, info


# ------------------------------------------------------------------ manifests

def _split_tsv(records):
    lines = ["id\tgroup\tenglish\thindi\thinglish"]
    for r in records:
        lines.append("\t".join([r["id"], r["group"], r["english"], r["hindi"], r["hinglish"]]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_splits(splits, info, provenance, params, data_dir, manifest_dir):
    """Write split TSVs to data_dir (gitignored) and a hashed manifest to
    manifest_dir (committed). The manifest carries record ids and the SHA-256 of
    every split file, so a split is citable without redistributing the data."""
    data_dir, manifest_dir = Path(data_dir), Path(manifest_dir)
    source = provenance["source"]
    out_dir = data_dir / source
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    split_entries = OrderedDict()
    for name, records in splits.items():
        payload = _split_tsv(records)
        path = out_dir / "{}.tsv".format(name)
        path.write_bytes(payload)
        ids = [r["id"] for r in records]
        split_entries[name] = {
            "file": repo_relative(path),
            "sha256": sha256_bytes(payload),
            "records": len(records),
            "unique_sources": len({dedup_key(r["english"]) for r in records}),
            "groups": len({r["group"] for r in records}),
            "ids_sha256": sha256_bytes("\n".join(ids).encode("utf-8")),
            "ids": ids,
        }
    manifest = OrderedDict([
        ("source", source),
        ("synthetic", "synthetic" in provenance),
        ("input_sha256", provenance["sha256"]),
        ("input_rows", provenance["rows_in_file"]),
        ("params", params),
        ("grouping", info),
        ("splits", split_entries),
    ])
    path = manifest_dir / "{}_split_manifest.json".format(source)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path, manifest


def print_split_summary(splits, info):
    print("  sources {:,} -> {:,} groups ({:,} merged as near-duplicates, "
          "{:,} verified pairs; largest group {})".format(
              info["unique_sources"], info["groups"],
              info["sources_merged_by_near_dup"], info["near_duplicate_pairs"],
              info["largest_group"]))
    for name, records in splits.items():
        print("  {:<6}{:>7,} records".format(name, len(records)))


def print_manifest(manifest_path, manifest):
    for name, entry in manifest["splits"].items():
        print("  {:<6} sha256 {}".format(name, entry["sha256"]))
    print("  manifest -> {}".format(manifest_path))
