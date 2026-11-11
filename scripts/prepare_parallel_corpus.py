#!/usr/bin/env python3
"""
Prepare the parallel source corpus for synthetic data, contamination-checked first.  [298-58]

Model 4's synthetic pairs -- back-translated and code-mixed -- are generated
from an English-Hindi parallel corpus. This script stages that corpus and runs
the contamination check BEFORE anything is generated from it:

  1. read one Samanantar shard (CC-BY-NC-4.0 by team decision, docs/datasheet.md),
     recording path, bytes, SHA-256 and rows
  2. scan the WHOLE shard for exact English or Hindi matches with any HinGE
     split -- cheap, and it measures how contaminated the source is
  3. filter, each pair charged to the first filter that rejects it
  4. draw a seeded sample
  5. remove every sampled pair that matches a dev or test source exactly or as a
     near-duplicate, at the threshold the splits were derived with
  6. re-run the check on what is left as a gate: any remaining hit halts with
     exit 3 and nothing is written

    python scripts/prepare_parallel_corpus.py \\
        --input data/raw/samanantar/hi-train-00000-of-00008.parquet --n 30000 --seed 42

Outputs:
  data/interim/samanantar/hi_slice.tsv           gitignored: english, hindi, samanantar_idx
  reports/contamination/samanantar_hi_slice.json committed: counts, hashes, thresholds

Needs pyarrow to read the parquet shard (requirements.txt).
"""

import argparse
import json
import random
import sys
import time
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative  # noqa: E402
from lrcs.data import contamination  # noqa: E402
from lrcs.text import dedup_key, devanagari_fraction, normalise, sha256_file, word_tokens  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "data" / "processed" / "manifests" / "hinge_split_manifest.json"
DEFAULT_PROCESSED = REPO_ROOT / "data" / "processed"
DEFAULT_OUT = REPO_ROOT / "data" / "interim" / "samanantar" / "hi_slice.tsv"
DEFAULT_REPORT = REPO_ROOT / "reports" / "contamination" / "samanantar_hi_slice.json"

# Filters, in order. Each rejected pair is charged to the first that fails, so
# the attrition table adds up -- the same rule as the cleaning stage.
PARAMS = OrderedDict([
    ("min_words", 4),            # shorter pairs give the aligner nothing to cut
    ("max_words", 25),           # longer ones exceed the generator's 12-block cap
    ("max_ratio", 2.0),          # Hindi/English word ratio; outside it, a misaligned pair
    ("min_hindi_devanagari", 0.8),
    ("max_english_devanagari", 0.0),
])
FILTERS = ("missing_field", "english_not_latin", "hindi_not_devanagari",
           "length_bounds", "length_ratio", "duplicate_source")

# Back-translation adds two filters that need a model to compute. They are
# recorded, not silently skipped, and applied when generation runs.
DEFERRED_FILTERS = OrderedDict([
    ("round_trip_chrf", "needs the reverse Hinglish-to-English model (Model 4, 298B); "
                        "applied to back-translated output, not to this source corpus"),
    ("labse_cosine", "not re-applied here: Samanantar's mined pairs were already selected by "
                     "cross-lingual sentence-embedding similarity (Ramesh et al., 2022); a "
                     "second pass needs the LaBSE model and a GPU-scale run, and is deferred "
                     "to the back-translation step"),
])


class PrepareError(RuntimeError):
    pass


def read_shard(path):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise PrepareError("pyarrow is needed to read {} (pip install pyarrow)".format(path)) from exc
    table = pq.read_table(str(path), columns=["idx", "src", "tgt"])
    return table.column("idx").to_pylist(), table.column("src").to_pylist(), table.column("tgt").to_pylist()


def rejection(english, hindi, seen):
    if not english or not hindi:
        return "missing_field"
    if devanagari_fraction(english) > PARAMS["max_english_devanagari"]:
        return "english_not_latin"
    if devanagari_fraction(hindi) < PARAMS["min_hindi_devanagari"]:
        return "hindi_not_devanagari"
    ne, nh = len(word_tokens(english)), len(word_tokens(hindi))
    if not (PARAMS["min_words"] <= ne <= PARAMS["max_words"]
            and PARAMS["min_words"] <= nh <= PARAMS["max_words"]):
        return "length_bounds"
    if nh / ne > PARAMS["max_ratio"] or ne / nh > PARAMS["max_ratio"]:
        return "length_ratio"
    key = dedup_key(english)
    if key in seen:
        return "duplicate_source"
    seen.add(key)
    return None


def whole_shard_exact_scan(english, hindi, split_sources):
    """Exact-key overlap of the entire shard with every HinGE split. No LSH, so it
    runs over a million rows in seconds; it is the contamination rate of the source."""
    out = OrderedDict()
    for name, pairs in split_sources.items():
        en_keys = {dedup_key(e) for e, _ in pairs}
        hi_keys = {dedup_key(h) for _, h in pairs if h and h.strip()}
        en_hits = sum(1 for e in english if e and dedup_key(e) in en_keys)
        hi_hits = sum(1 for h in hindi if h and dedup_key(h) in hi_keys)
        matched = {dedup_key(e) for e in english if e} & en_keys
        out[name] = OrderedDict([
            ("hinge_sources", len(en_keys)),
            ("shard_rows_matching_english", en_hits),
            ("shard_rows_matching_hindi", hi_hits),
            ("hinge_sources_found_in_shard", len(matched)),
            ("share_of_split_sources_found", round(len(matched) / len(en_keys), 4) if en_keys else 0.0),
        ])
    return out


def write_tsv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", encoding="utf-8", newline="") as fh:
        fh.write("english\thindi\tsamanantar_idx\n")
        for english, hindi, idx in rows:
            fh.write("{}\t{}\t{}\n".format(english.replace("\t", " "), hindi.replace("\t", " "), idx))


def prepare(args):
    started = time.time()
    threshold, split_sources = contamination.load_split_sources(args.manifest, args.processed_dir)
    src = Path(args.input)
    if not src.exists():
        raise PrepareError("{}: not found. Samanantar's Hindi shards are at "
                           "https://huggingface.co/datasets/ai4bharat/samanantar (docs/datasheet.md)"
                           .format(src))
    ids, english, hindi = read_shard(src)
    english = [normalise(e) for e in english]
    hindi = [normalise(h) for h in hindi]
    provenance = OrderedDict([
        ("source", "Samanantar, en-hi, Hugging Face ai4bharat/samanantar, hi/{}".format(src.name)),
        ("path", repo_relative(src)),
        ("bytes", src.stat().st_size),
        ("sha256", sha256_file(src)),
        ("rows", len(ids)),
        ("licence", "CC-BY-NC-4.0 (team decision, docs/datasheet.md)"),
    ])
    print("[1] {} rows from {}".format(len(ids), provenance["path"]))

    scan = whole_shard_exact_scan(english, hindi, split_sources)
    for name, s in scan.items():
        print("[2] whole shard vs HinGE {:<5}: {:>4} of {:>4} sources present ({:.1%}); "
              "{} English and {} Hindi row matches".format(
                  name, s["hinge_sources_found_in_shard"], s["hinge_sources"],
                  s["share_of_split_sources_found"], s["shard_rows_matching_english"],
                  s["shard_rows_matching_hindi"]))

    attrition = OrderedDict((f, 0) for f in FILTERS)
    seen, survivors = set(), []
    for i in range(len(ids)):
        reason = rejection(english[i], hindi[i], seen)
        if reason:
            attrition[reason] += 1
        else:
            survivors.append(i)
    print("[3] {} pass the filters: {}".format(
        len(survivors), ", ".join("{} {}".format(v, k) for k, v in attrition.items())))

    order = sorted(survivors)
    random.Random(args.seed).shuffle(order)
    sample = sorted(order[:args.n])
    if len(sample) < args.n:
        raise PrepareError("only {} pairs pass the filters; asked for {}".format(len(sample), args.n))
    print("[4] sampled {} pairs at seed {}".format(len(sample), args.seed))

    index = contamination.ContaminationIndex(split_sources, threshold, seed=args.seed)
    pairs = [(english[i], hindi[i]) for i in sample]
    kept_local, check = contamination.check_pairs(pairs, index)
    print("[5] contamination check at Jaccard >= {}: {} removed, {} kept".format(
        threshold, check["removed"], check["kept"]))
    kept = [sample[j] for j in kept_local]

    final = contamination.gate([(english[i], hindi[i]) for i in kept], index)
    print("[6] gate re-check on the kept pairs: PASSED, 0 matches with {}".format(
        " or ".join(final["protected_splits"])))

    out = Path(args.out)
    write_tsv(out, [(english[i], hindi[i], ids[i]) for i in kept])
    report = OrderedDict([
        ("issue", "298-58"),
        ("generated_by", "scripts/prepare_parallel_corpus.py"),
        ("seed", args.seed),
        ("input", provenance),
        ("hinge_manifest", repo_relative(Path(args.manifest))),
        ("filter_params", PARAMS),
        ("attrition", OrderedDict([("rows_in", len(ids))] + list(attrition.items())
                                  + [("passed_filters", len(survivors))])),
        ("whole_shard_exact_overlap", scan),
        ("sample", len(sample)),
        ("contamination_check", check),
        ("gate", final),
        ("deferred_filters", DEFERRED_FILTERS),
        ("output", OrderedDict([("path", repo_relative(out)), ("rows", len(kept)),
                                ("sha256", sha256_file(out)), ("committed", False)])),
        ("elapsed_seconds", round(time.time() - started, 1)),
    ])
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("    slice  -> {} ({} rows, gitignored)".format(repo_relative(out), len(kept)))
    print("    report -> {}".format(repo_relative(report_path)))
    return report


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", required=True, help="a Samanantar en-hi parquet shard")
    ap.add_argument("--n", type=int, default=30000, help="pairs to sample after filtering")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--processed-dir", default=str(DEFAULT_PROCESSED))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--report", default=str(DEFAULT_REPORT))
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        prepare(args)
    except contamination.ContaminationError as exc:
        print("HALTED: {}. Nothing written.".format(exc), file=sys.stderr)
        return 3
    except PrepareError as exc:
        print("prepare failed: {}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
