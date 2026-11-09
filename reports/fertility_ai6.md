# Requirement AI-6: fertility across all four text slices

Linear **298-75**. Measured 8 November 2026 by Waghmare, Sarvesh, with
`Qwen/Qwen2.5-7B-Instruct` from the local tokenizer cache. No network.

Regenerate everything here with two commands on a clean clone:

```bash
python3 scripts/make_slices.py
python3 analysis/tokenizer_fertility.py \
  --corpus en=data/slices/en.txt \
  --corpus hi_roman=data/slices/hi_roman.txt \
  --corpus hinglish=data/slices/hinglish.txt \
  --tokenizer Qwen/Qwen2.5-7B-Instruct --out reports/fertility.csv
```

## Verdict: AI-6 is **not met**

AI-6 requires six metrics reported for **four** slices: English, Devanagari Hindi, Romanized
Hindi, Romanized Hinglish. Three are now measured. The fourth cannot be built, and this is a
definite state rather than "partly met": the requirement names a slice for which no source exists
anywhere in the repository.

`docs/workbook2/carry_forward.md` previously recorded AI-6 as corrected from *met* to *partly met*.
It is now recorded as **not met, 3 of 4 slices, with a one-command path to met.**

| Slice | Status | Source | n lines |
|---|---|---|---|
| English | **measured** | `lrcs.data.synthetic` generate(n=1200, seed=42), english column | 1,200 |
| Romanized Hindi | **measured** | `data/codemix/parallel_fixture.tsv`, team-authored | 30 |
| Romanized Hinglish | **measured** | `lrcs.data.synthetic` generate(n=1200, seed=42), hinglish column | 1,169 |
| Devanagari Hindi | **absent** | none exists | 0 |

### Why the fourth slice is absent, checked rather than assumed

- `git grep` over the Devanagari Unicode block (U+0900–U+097F) across the whole repository returns
  **nothing**. There is no Devanagari text committed anywhere.
- The synthetic generator emits a `hindi` column that is **empty in all 1,200 rows** — verified by
  counting non-empty fields, not by inspection of a sample.
- `data/goldtestset/gold_set.csv` is specified with a Devanagari Hindi column but holds its header
  row and 0 of 800 items, so that column is empty too.
- HinGE's released `Hindi` column *is* Devanagari, but `HinGE.pkl` is not committed (`data/raw/` is
  gitignored) and is not on this machine.

**The one command that closes AI-6**, once the release is obtained from a team member who has it:

```bash
python3 scripts/convert_hinge_pkl.py data/raw/HinGE.pkl data/raw/hinge.csv \
  && python3 scripts/make_slices.py --hi-deva-from data/raw/hinge.csv
```

`--hi-deva-from` is implemented and covered by tests. Closing this requirement is now a matter of
obtaining a file, not of writing code.

## The measured table

From `reports/fertility.csv`:

| Slice | n lines | n words | word types | fertility | bytes/token | continuation | severe split | byte fallback | vocab coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| en | 1,200 | 11,413 | 372 | **1.1538** | 4.4654 | 0.1454 | 0.0011 | 0.0000 | **0.5323** |
| hi_roman | 30 | 165 | 128 | **1.9091** | 2.7746 | 0.7152 | 0.0121 | 0.0000 | **0.2188** |
| hinglish | 1,169 | 10,442 | 314 | **1.6528** | 3.2162 | 0.4926 | 0.0162 | 0.0000 | **0.5478** |

All six metrics AI-6 names are present for each measured slice. `spelling_variant_burden` remains
**1.832** and is a property of the lexicon rather than of a slice, so it is constant down the column.

### One result worth keeping

Fertility orders **hi_roman (1.909) > hinglish (1.653) > en (1.154)**. Romanized Hindi is the most
expensive slice and Hinglish sits between it and English — which is what the hypothesis predicts
and the script's docstring anticipated. Hinglish is cheaper than Romanized Hindi because it
contains English words the tokenizer already knows; the cost is carried by the Hindi-origin tokens,
not by code-mixing as such.

That ordering is the first direct evidence for *where* the burden sits, and it needed the third
slice to be visible at all. With only English and Hinglish measured, the question could not be asked.

## A correction the new measurement forces

**The headline coverage gap does not reproduce.** Workbook 1 sections 1.2 and 1.4 report vocabulary
coverage of **98.5% on English against 52.6% on Hinglish**. On these slices it is **53.2% against
54.8%** — the gap is gone, and English is marginally *worse*.

The cause is identifiable and it is not a bug. The 7 October slice had **67 distinct English word
types** across 9,866 words. This one has **372** across 11,413. A 67-type slice is almost entirely
in-vocabulary by construction, so 98.5% measured how repetitive that slice was, not how well the
tokenizer covers English.

| | 7 Oct slice | 8 Nov slice |
|---|---|---|
| English word types | 67 | 372 |
| English coverage | 0.9851 | 0.5323 |
| Hinglish word types | 78 | 314 |
| Hinglish coverage | 0.5256 | 0.5478 |

Hinglish coverage barely moved (52.6% → 54.8%), which is the tell: Hinglish coverage was always
measuring something real, and English coverage was not.

**The fertility gap survives, the coverage gap does not.** Fertility is 1.154 against 1.653, a ratio
of 1.43 where the earlier slice gave 1.024 against 1.501, a ratio of 1.47. The direction and rough
magnitude hold. Coverage should be dropped from the headline claim until it is measured on real
HinGE.

The superseded table is kept at `reports/fertility_1091_slice.csv` so this comparison is auditable.

## What this does not establish

These slices are **synthetic** for English and Hinglish, and 30 sentences for Romanized Hindi. So:

- Nothing here is a real-corpus measurement. AI-6 would still not be *met* on real data even with
  four slices, and the carry-forward row says so.
- `hi_roman` at n=30 has 128 word types in 165 words — nearly every word is distinct. Its coverage
  figure of 0.2188 is not a reliable estimate of anything and should not be quoted without the n.
  Its fertility is more robust than its coverage, because fertility averages over tokens rather
  than depending on type-level vocabulary hits.
- The point of this run is that the **measurement path for all four slices now exists and is
  reproducible**, and that the one missing input is named. It is not a claim about the corpus.

## Provenance

| Claim | Source |
|---|---|
| per-slice metrics | `reports/fertility.csv` |
| per-group variant costs, burden 1.832 | `reports/fertility.variants.csv` |
| slice sources, line counts, SHA-256, absence reason | `data/slices/manifest.json` |
| superseded 1,091-pair measurement | `reports/fertility_1091_slice.csv` |
| slice construction and script guards | `scripts/make_slices.py`, `tests/test_make_slices.py` |
