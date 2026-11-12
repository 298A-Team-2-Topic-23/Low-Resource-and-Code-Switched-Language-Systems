# 3.5 Data Preparation

Linear **298-64**. Written by Shevkar, Yash.

Stage 3 (`src/lrcs/data/splits.py`, `src/lrcs/data/leakage.py`) takes the 4,674 cleaned records
and divides them into splits that share no source sentence, exactly or as a near-duplicate,
checks that property with an independent gate, and freezes the result under SHA-256. Counts come
from the real HinGE run (`reports/data_statistics.json`, input SHA-256 `dcfaf37c…`); per-split
composition from `reports/split_balance_hinge.json`. None was typed in by hand.

## 3.5.1 Why the splits are derived, not downloaded

HinGE ships no splits. The only released split built on its sentences is the HinglishEval
shared-task release (Srivastava & Singh, 2022), and **those splits are not disjoint.** On the
same normalised key our gate uses:

| Released split pair | Shared English sources | Share |
|---|---|---|
| validation sources also in train | 285 of 376 | **75.8%** |
| test sources also in train | 552 of 707 | **78.1%** |
| test sources also in validation | 73 of 707 | 10.3% |

A model scored on that test split would be scored mostly on sentences it had trained on. The
78.1% figure is worse than the 75.8% quoted in Workbook 1, and both reproduce from the released
files (`reports/hinglisheval_overlap.json`). The project therefore never reads a released split.

## 3.5.2 How 4,674 records become three splits

The unit of assignment is a **group of source sentences**, never an individual record. Four
seeded, deterministic steps:

1. **Key every record by its English source** after NFKC, lower-casing and punctuation removal.
   HinGE averages 2.41 references per source and every reference shares the key, so all
   references of one sentence move together.
2. **Group near-duplicate sources** when exact Jaccard over character 4-gram shingles is ≥ **0.7**.
   MinHash (96 permutations, 32 bands of 3) proposes candidates and every candidate is verified
   exactly, so LSH can miss a pair but cannot wrongly merge one. On HinGE, **1,938 sources form
   1,937 groups** — exactly one near-duplicate pair was merged.
3. **Halt on a degenerate grouping.** If one group held over 5% of records the threshold would be
   chaining unrelated sentences; the stage exits 4 and writes nothing. HinGE's largest group holds
   8 records, 0.17%.
4. **Assign whole groups**, sorted then shuffled at seed 42, each going to whichever split is
   furthest below its 80/10/10 target. The gate then checks the result before anything is written.

## 3.5.3 The splits

| Split | Rows | % of total | Stratified on | Leakage check and result |
|---|---|---|---|---|
| Train | 3,738 | 79.97% | **Not stratified** — whole near-duplicate source groups assigned by seeded shuffle (§3.5.4) | Exact and near-duplicate (Jaccard ≥ 0.7) source overlap against dev and test: **0 exact, 0 near.** Gate passed |
| Validation | 468 | 10.01% | Not stratified, as above | Against train and test: **0 exact, 0 near.** Gate passed |
| Test | 468 | 10.01% | Not stratified, as above | Against train and dev: **0 exact, 0 near.** Gate passed |
| **Total** | **4,674** | **100%** | | 1,938 sources checked across all pairs, threshold 0.7 |

Rows are records, one per human reference. Unique sources per split: **1,549 / 192 / 197**. The
shares miss 80/10/10 by 0.03 points because a group cannot be divided.

## 3.5.4 Why the splits are not stratified, and what that costs

Stratification works on *records*, and the records of one source differ in exactly the features
one would stratify on — one reference can be heavily mixed and another barely. A stratified
assignment would therefore place different references of the **same English sentence** in train
and test. Cross-split leakage is the defect this corpus is already known for (§3.5.1), so we chose
the constraint that rules it out: a source group goes to exactly one split, whatever its features.

Three costs. Shares are approximate. Balance is left to the shuffle, **so it had to be checked**:

| | Train | Dev | Test |
|---|---|---|---|
| References per source | 2.41 | 2.44 | 2.38 |
| English words per record, mean / median | 15.3 / 12 | 15.7 / 12 | 14.1 / 11 |
| Code-Mixing Index, mean | 25.3 | 25.5 | 25.9 |
| Sentences containing both languages | 86.3% | 85.3% | 85.5% |
| Switch-point fraction | 0.240 | 0.245 | 0.237 |
| Tagger coverage | 68.3% | 67.1% | 68.6% |

The code-mixing profile — the quantity the project studies — agrees across splits to within one
CMI point and 0.008 SPF. **Test sentences are shorter** by about 1.2 English words. That is a
property of this seed's shuffle, reported rather than corrected, because re-drawing the split
until it looked better would be tuning on test. Length-sensitive results should be read with it
in mind. Third cost: with 197 test sources, any subgroup of a few percent has a handful of
sentences, and §4.4's bootstrap intervals are what make that visible.

## 3.5.5 The leakage gate

The splits are not trusted because of how they were built; they are checked after assignment and
**before anything is written**.

| Check | What it compares | Threshold | Result |
|---|---|---|---|
| Exact | Same normalised English key in two splits | Identity | **0** overlaps |
| Near-duplicate | Character 4-gram Jaccard across splits | **≥ 0.7** | **0** overlaps |
| Shared targets (reported, not gated) | Same Hinglish text under different sources | Identity | 0 |

Two choices make the gate meaningful rather than a restatement of step 2. **One threshold on both
sides**: with two values, a pair whose similarity fell between them would pass grouping as
"different" and then fail the gate as "leaked" on clean data — a bug that existed in an earlier
version. **An independent hash seed**: the gate re-runs MinHash with a different seed, so a pair
LSH missed during grouping gets a second, independent chance.

**On any overlap the gate halts**: exit 3, no manifest, no split files. It never only warns. This
is demonstrated, not asserted — `reports/rehearsals/2026-10-07/leakage-gate.log` injects one test
source into train and records the run stopping with "No manifest written", and
`test_leakage_gate_halts_on_exact_and_near_overlap` checks both overlap kinds.

*One reader trap*: test has 197 sources in 196 groups. That is the single merge from step 2 — two
sources differing only by a stray underscore were joined into one group of 4 records, which sits
entirely in test. Had they been assigned separately, one could have landed in train and the gate
would have halted the run.

## 3.5.6 Frozen and version-controlled

`data/processed/manifests/hinge_split_manifest.json` records, per split, the record count, unique
sources, groups, the file's SHA-256, and the full list of content-hashed record ids. An id means
the same pair on every machine, so a split can be cited without redistributing the corpus.

| Split | SHA-256 |
|---|---|
| train | `82c045f21bb5d55e5801d606448f5186ec10eaba806f214755cbc317dbc1eed5` |
| dev | `db0b17cca1443108180060ed5d669aef64a8e484b62f45d6173f4921cea3c68a` |
| test | `6ac5d302fe34dd66e99a190f707ca7af7818b36cc64e2162666548f9a0c14478` |

**The freeze is checked by regeneration, not declared.** The manifest has been reproduced
**byte-identical four times on three machines** — twice locally, once inside Colab on a T4, once
in CI — each from a fresh download, with identical id lists. `scripts/split_balance.py` refuses to
describe a split file whose hash does not match, so §3.5.4's table describes the frozen splits and
nothing else.

Rules that follow: **no tuning on test** (prompts, hyperparameters and checkpoints chosen on dev;
test scored once per final configuration); **few-shot examples and M3's added vocabulary come from
train only**; **synthetic training data is contamination-checked against test before generation**,
because the gate compares only our three splits with each other; and **changing split membership
is a recorded decision** requiring a dated rationale, with a new manifest hash every result would
have to cite.

## 3.5.7 Samples of the prepared data

From `reports/samples/hinge/prepared.md`, seed 42, in the five-column TSV layout the model scripts
read:

| Split | id | english | hinglish |
|---|---|---|---|
| train | `28e435d5…` | Is Taj Mahal in realty the Temple of Lord Shiva? | Is taj mahal in reality shiv ka mandir. |
| dev | `44bd818d…` | Please circulate deposit book to new members. | Kripya jama hundi new members ko circulate kar do. |
| test | `39507108…` | you can have a pack. | you can have ak basta. |
| test | `40fd6b7c…` | All data is encrypted with your sync passphrase | Sabhi data aapke passphrase ke sathe encrypt kiya jayega. |

The references keep their writers' own spellings — `ak` for *ek*, `sathe` for *saath*. That is
deliberate: orthographic variance is the phenomenon under study, so preparation never normalises a
reference (§3.4). The Devanagari `hindi` column travels with each record but is not a target.

## 3.5.8 Limitations

**One seed, one split.** Model variance is measured over three training seeds; split variance is
not. A second split seed would show how much §3.5.4's test-length difference matters. **The
threshold is lexical** — Jaccard over character 4-grams catches near-copies and light paraphrases,
not translations sharing meaning but few characters, so two sources saying the same thing
differently can sit in different splits. No semantic check runs. **The test split is small for
subgroup analysis**: at 197 sources, error analysis should use dev and test together, and the
800-item gold set (0 items today, 298-55) is the intended primary surface.

**Provenance.** Counts and gate result from `reports/data_statistics.json` and the split manifest;
composition from `reports/split_balance_hinge.json`; the HinglishEval overlap from
`reports/hinglisheval_overlap.json`; algorithms from `src/lrcs/data/splits.py` and `leakage.py`;
halt behaviour from `tests/test_pipeline.py` and the 7 October rehearsal log; samples from
`reports/samples/hinge/prepared.md`.
