# Contamination check for synthetic training data

Linear **298-58**, shared with **298-76**. Written by Shevkar, Yash, 9 November 2026.

Regenerate:

```bash
# the HinGE splits must be on disk (gitignored) and match the frozen manifest
python scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42
python scripts/prepare_parallel_corpus.py \
    --input data/raw/samanantar/hi-train-00000-of-00008.parquet --n 30000 --seed 42
```

Result: `samanantar_hi_slice.json` in this folder, with counts, hashes and thresholds and no
corpus text. The slice itself is `data/interim/samanantar/hi_slice.tsv`. It is gitignored and not
redistributed (licences: `docs/datasheet.md`).

## Why this exists

The leakage gate compares our three splits with each other. It cannot see a corpus brought in
from outside. Model 4 trains on synthetic pairs generated from an English–Hindi parallel corpus.
HinGE's English sources come from the IIT Bombay corpus, and Samanantar includes the IIT Bombay
corpus. If a dev or test source reached the synthetic data, it would enter training without
passing any gate, and every M4 number would be scored partly on training data.

The check therefore runs **before** anything is generated, and it is built once for both kinds of
synthetic data: back-translation (298-58) and code-mixing (298-76).

## What it checks

`src/lrcs/data/contamination.py` asks one question of every candidate pair: is it one of our
evaluation sources?

| Check | Compared | Threshold |
|---|---|---|
| `exact` | Normalised English key (`lrcs.text.dedup_key`) against every HinGE source | Identity |
| `near` | Character 4-gram Jaccard against every HinGE source; MinHash proposes, exact Jaccard decides | **0.7, read from the frozen split manifest**, not passed by hand |
| `hindi_exact` | Normalised Hindi text against every HinGE source's Hindi | Identity |

A hit on **dev or test** removes the pair. A hit on **train** is counted and kept, since training on
a train source again is not leakage. After removal, the same check runs again as a **gate**. Any
remaining hit halts with exit code 3 and nothing is written, the same halt-not-warn rule as the
split gate.

The threshold comes from the manifest on purpose. When dedupe and the split gate once used
different thresholds, pairs between the two values slipped through. Reading the value from the
same file the splits were made with prevents that drift here. The check also refuses split files
whose hashes do not match the manifest, because checking against anything but the frozen splits
proves nothing.

## The finding

Samanantar is measurably contaminated with our evaluation sentences. In one Hindi shard,
`hi/train-00000-of-00008.parquet` (1,265,714 pairs, one eighth of the Hindi data), exact English
matches alone give:

| HinGE split | Sources | Found in the shard | Share |
|---|---|---|---|
| train | 1,549 | 275 | 17.8% |
| dev | 192 | 33 | 17.2% |
| **test** | **197** | **27** | **13.7%** |

The whole shard is scanned by exact key only. A near-duplicate scan over 1.27M rows in pure
Python is too slow to be useful, so these shares are **lower bounds**. The full Samanantar Hindi
set is eight such shards.

**The Hindi-side check is not redundant.** Samanantar sometimes pairs the same Hindi sentence
with a **different English translation**. It happens most with religious text, where several
English translations exist. In those pairs the English Jaccard against our source is low, so the
English checks pass, while the Hindi sentence is ours word for word. In the shard, 107 rows match a
test source on the Hindi side against 28 on the English side.

## The slice that was prepared

| Step | Pairs |
|---|---|
| Shard | 1,265,714 |
| Removed by filters, each charged once | 39,952 Hindi side not Devanagari · 694,439 outside 4–25 words · 201,026 word ratio above 2.0 · 42,723 duplicate English source |
| Passed the filters | 287,574 |
| Seeded sample, seed 42 | 30,000 |
| Removed by the contamination check | **4**: 1 exact English match with dev, 3 Hindi-side matches with test |
| Gate re-check on the rest | **Passed**: 0 matches with dev or test |
| **Kept** | **29,996** |

The 4–25 word bounds keep sentences the aligner can cut: below 4 there is nothing to switch, and
above 25 sentences routinely exceed the generator's 12-block limit. The 2.0 ratio rejects pairs
whose two sides are unlikely to be translations of each other.

## Filters recorded but not applied here

Two back-translation filters named in the 298-58 brief need a model, and the source corpus is
staged before any model runs:

- **Round-trip chrF** needs the reverse Hinglish-to-English model, which is part of Model 4 (298B).
  It applies to back-translated **output**, not to this source corpus.
- **LaBSE or LASER cosine similarity.** Samanantar's mined pairs were already selected by
  cross-lingual sentence-embedding similarity (Ramesh et al., 2022). A second pass would need the
  embedding model and a GPU-scale run, and is deferred to the back-translation step.

Both are listed under `deferred_filters` in the report, so neither is silently skipped.

## Limits

- **One shard.** The other seven Hindi shards are unchecked. Anyone who pulls from them must run
  the same script.
- **Lexical near-duplicates only.** A paraphrase of a test sentence with little character overlap
  is not caught. No semantic check is run.
- **Generation must not undo this.** Code-mixing and back-translation only use pairs from the
  kept slice. 298-76 re-runs the gate on its final output as well.
