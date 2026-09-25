#!/usr/bin/env python3
"""
Re-derive disjoint train/dev/test splits for HinGE.  [owner: Yash]

Why this exists
----------------
HinGE has no released splits of its own; the released splits people reach
for are actually from the downstream INLG HinglishEval shared task, which
reused HinGE's English sources. Those released train/valid/test files are
NOT mutually exclusive -- 75.8% of dev's unique English sources also occur
in train (see --audit). Any model trained on those released splits is
evaluated on sentences it has already seen.

This script:
  1. loads the primary HinGE corpus (English, Hindi, Hinglish variant,
     variant source, ratings) -- one row per human/WAC/PAC reference
  2. reports how much leakage the released HinglishEval splits contain
  3. groups near-duplicates so paraphrases cannot straddle a split
     boundary -- exact normalised match AND MinHash/LSH, not exact
     match alone
  4. writes disjoint train/dev/test splits (to data/processed/, NOT
     committed -- see .gitignore)
  5. writes a manifest with SHA-256 hashes to
     data/processed/manifests/, which IS committed, so the splits are
     citable and reproducible without redistributing the data itself

Dependency: pip install datasketch   (MinHash/LSH near-duplicate search)

Usage
-----
  # inspect leakage in the released (HinglishEval) splits -- report only
  python scripts/make_splits.py --audit data/raw/hinge_released_train.tsv \
      data/raw/hinge_released_dev.tsv

  # derive our own splits from the primary HinGE corpus
  python scripts/make_splits.py --input data/raw/hinge_base.tsv \
      --outdir data/processed --train 0.8 --dev 0.1 --test 0.1 --seed 42

Input format: TSV, one record per line. Column 0 must be the English
source. Remaining columns are carried through untouched.
"""

import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from datasketch import MinHash, MinHashLSH
except ImportError:
    sys.exit("pip install datasketch  -- required for near-duplicate filtering")

# ------------------------------------------------------------------- near-dupes

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")

MINHASH_NUM_PERM = 128
MINHASH_SHINGLE_SIZE = 4       # character n-grams -- robust to short sentences
MINHASH_JACCARD_THRESHOLD = 0.7


def dedup_key(text: str) -> str:
    """Cheap normalisation used to group EXACT near-duplicates.

    Two sentences with the same key always go into the same split. This
    alone catches case/punctuation/whitespace variants but not paraphrases
    or reordering -- that is what the MinHash pass below is for.
    """
    t = unicodedata.normalize("NFKC", text).lower()
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    return t


def shingles(text: str, k: int = MINHASH_SHINGLE_SIZE):
    if len(text) < k:
        return {text} if text else set()
    return {text[i:i + k] for i in range(len(text) - k + 1)}


def minhash_of(text: str) -> MinHash:
    m = MinHash(num_perm=MINHASH_NUM_PERM)
    for sh in shingles(text):
        m.update(sh.encode("utf-8"))
    return m


class UnionFind:
    def __init__(self, items):
        self.parent = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def near_dup_clusters(keys):
    """Cluster normalised keys that are near-duplicates under MinHash/LSH.

    Exact-match grouping (dedup_key) is not enough -- two paraphrases of
    the same sentence can normalise to different keys and still be near
    duplicates. This is the belt to dedup_key's braces: it catches what
    normalisation misses, using Jaccard similarity over character
    4-gram MinHash signatures via LSH so it scales past brute-force
    pairwise comparison.

    Returns {key: cluster_id}.
    """
    lsh = MinHashLSH(threshold=MINHASH_JACCARD_THRESHOLD, num_perm=MINHASH_NUM_PERM)
    sigs = {}
    for k in keys:
        m = minhash_of(k)
        sigs[k] = m
        lsh.insert(k, m)

    uf = UnionFind(keys)
    for k in keys:
        for neighbour in lsh.query(sigs[k]):
            if neighbour != k:
                uf.union(k, neighbour)

    return {k: uf.find(k) for k in keys}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_tsv(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            rows.append(line.split("\t"))
    if not rows:
        sys.exit(f"empty file: {path}")
    return rows


# ------------------------------------------------------------------------ audit


def audit(paths):
    """Report overlap between the released (HinglishEval) splits. Writes nothing."""
    sets = {}
    for p in paths:
        rows = read_tsv(p)
        sets[Path(p).name] = {dedup_key(r[0]) for r in rows}
        print(f"{Path(p).name:<32} {len(rows):>6} rows, "
              f"{len(sets[Path(p).name]):>6} unique keys")

    print("\npairwise overlap (by normalised English source)")
    names = list(sets)
    clean = True
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = sets[a] & sets[b]
            pct = 100 * len(shared) / max(min(len(sets[a]), len(sets[b])), 1)
            flag = "" if not shared else "   <-- LEAKAGE"
            if shared:
                clean = False
            print(f"  {a} ∩ {b}: {len(shared)} shared ({pct:.1f}% of the "
                  f"smaller set){flag}")
    print("\nreleased splits are disjoint" if clean
          else "\nreleased splits OVERLAP -- these are the HinglishEval shared-task "
               "files, not used anywhere in this project; we derive our own "
               "splits from the primary HinGE corpus instead (--input)")


# ------------------------------------------------------------------------ splits


def make_splits(rows, ratios, seed):
    """Exact-match groups, merged further by MinHash near-dup clusters, then
    whole clusters assigned to splits."""
    exact_groups = defaultdict(list)
    for r in rows:
        exact_groups[dedup_key(r[0])].append(r)

    cluster_of = near_dup_clusters(list(exact_groups))
    clusters = defaultdict(list)
    for key, rows_for_key in exact_groups.items():
        clusters[cluster_of[key]].extend(rows_for_key)

    cluster_ids = sorted(clusters)          # sorted first => deterministic
    random.Random(seed).shuffle(cluster_ids)

    n = len(cluster_ids)
    n_train = int(n * ratios[0])
    n_dev = int(n * ratios[1])
    parts = {
        "train": cluster_ids[:n_train],
        "dev": cluster_ids[n_train:n_train + n_dev],
        "test": cluster_ids[n_train + n_dev:],
    }
    return ({name: [r for cid in ids for r in clusters[cid]]
             for name, ids in parts.items()},
            exact_groups, clusters)


def verify_disjoint(splits):
    """Belt and braces: prove the output is actually disjoint before writing."""
    keysets = {n: {dedup_key(r[0]) for r in rows} for n, rows in splits.items()}
    ok = True
    names = list(keysets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = keysets[a] & keysets[b]
            if shared:
                ok = False
                print(f"  FAIL {a} ∩ {b}: {len(shared)} shared keys")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit", nargs="+", help="report overlap in existing (released) split files, then exit")
    ap.add_argument("--input", help="the primary HinGE corpus as TSV")
    ap.add_argument("--outdir", default="data/processed")
    ap.add_argument("--manifest-dir", default="data/processed/manifests")
    ap.add_argument("--train", type=float, default=0.8)
    ap.add_argument("--dev", type=float, default=0.1)
    ap.add_argument("--test", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.audit:
        audit(args.audit)
        return
    if not args.input:
        ap.error("--input is required (or use --audit)")

    total = args.train + args.dev + args.test
    if abs(total - 1.0) > 1e-6:
        sys.exit(f"ratios must sum to 1.0, got {total}")

    rows = read_tsv(args.input)
    splits, exact_groups, clusters = make_splits(
        rows, (args.train, args.dev, args.test), args.seed)

    n_exact_dupe_groups = sum(1 for g in exact_groups.values() if len(g) > 1)
    n_minhash_merges = len(exact_groups) - len(clusters)
    print(f"rows                    : {len(rows)}")
    print(f"exact-normalised keys   : {len(exact_groups)}")
    print(f"  of which multi-row    : {n_exact_dupe_groups}")
    print(f"MinHash clusters        : {len(clusters)}")
    print(f"  exact keys merged by MinHash beyond normalisation: {n_minhash_merges}")

    print("\nverifying disjointness")
    if not verify_disjoint(splits):
        sys.exit("splits are not disjoint -- aborting, nothing written")
    print("  OK: no key appears in more than one split")

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    mdir = Path(args.manifest_dir)
    mdir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": str(args.input),
        "source_sha256": sha256_file(Path(args.input)),
        "seed": args.seed,
        "ratios": {"train": args.train, "dev": args.dev, "test": args.test},
        "dedup": {
            "exact": "NFKC, lowercase, punctuation stripped, whitespace collapsed",
            "near_duplicate": f"MinHash/LSH, char {MINHASH_SHINGLE_SIZE}-gram shingles, "
                               f"{MINHASH_NUM_PERM} permutations, "
                               f"Jaccard threshold {MINHASH_JACCARD_THRESHOLD}",
            "note": "clusters (exact-key groups further merged by MinHash) are "
                    "assigned whole to a single split",
        },
        "counts": {
            "rows": len(rows),
            "exact_keys": len(exact_groups),
            "minhash_clusters": len(clusters),
        },
        "splits": {},
    }

    print()
    for name, srows in splits.items():
        p = out / f"{name}.tsv"
        with open(p, "w", encoding="utf-8") as fh:
            for r in srows:
                fh.write("\t".join(r) + "\n")
        digest = sha256_file(p)
        manifest["splits"][name] = {"file": p.name, "rows": len(srows), "sha256": digest}
        print(f"  {name:<6} {len(srows):>6} rows  {digest[:16]}...  -> {p}")

    mpath = mdir / "hinge_split_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nmanifest -> {mpath}")
    print(f"Split files were written to {out}/ but are gitignored -- do not commit them.")
    print(f"Commit {mpath} only. It records the source hash, seed and dedup method, so")
    print("anyone with access to the source data reproduces byte-identical splits.")


if __name__ == "__main__":
    main()
