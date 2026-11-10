# 3.5 Data Preparation

Linear **298-64**. Written by Shevkar, Yash.

Data preparation is stage 3 of the pipeline (`src/lrcs/data/splits.py` and
`src/lrcs/data/leakage.py`). It takes the 4,674 cleaned records from stage 2 and divides them into
training, validation and test splits that share no source sentence, either exactly or as a
near-duplicate. It then checks that property with an independent gate and freezes the result under
SHA-256. Every count below comes from the real HinGE run (`reports/data_statistics.json`, run record
`runs/20261008T043208Z_data-pipeline_seed42.json`, input CSV SHA-256 `dcfaf37c…`). The per-split
composition figures come from `reports/split_balance_hinge.json`, which `scripts/split_balance.py`
generated on 9 November. None was typed in by hand.

## 3.5.1 Why the splits are derived, not downloaded

HinGE itself ships no train, validation or test split. The only released split built on its
sentences is the HinglishEval shared-task release (Srivastava & Singh, 2022), which sits in the same folder as
`HinGE.pkl` and reuses HinGE's English sources. **Those splits are not disjoint.** Compared on the
same normalised key our leakage gate uses, the released files give:

| Released split pair | Shared English sources | Share |
|---|---|---|
| validation sources also in train | 285 of 376 | **75.8%** |
| test sources also in train | 552 of 707 | **78.1%** |
| test sources also in validation | 73 of 707 | 10.3% |

(`reports/hinglisheval_overlap.json`, from `scripts/audit_hinglisheval_overlap.py`.) A model scored on
that test split would be scored mostly on sentences it had trained on. The test-set figure, 78.1%,
is stronger than the 75.8% quoted in Workbook 1, and both reproduce from the released files. The
project therefore never reads a released split. Stage 3 derives its own from the cleaned records,
and the rest of this section describes how.

## 3.5.2 How 4,674 records become three splits

The unit of assignment is a **group of source sentences**, never an individual record. Four steps,
all seeded and deterministic:

1. **Key every record by its English source.** The key is the source after NFKC normalisation,
   lower-casing and punctuation removal (`lrcs.text.dedup_key`). HinGE averages 2.41 human
   references per source, and every reference of one source shares the key. All references to
   one sentence therefore move together, so the same English sentence can never be trained on and
   tested on.
2. **Group near-duplicate sources.** Two keys are joined when the exact Jaccard similarity of their
   character 4-gram shingles is at least **0.7**. MinHash with 96 permutations in 32 bands of 3
   rows proposes candidate pairs, and every candidate is then verified by computing the exact
   Jaccard. LSH can therefore miss a pair but cannot wrongly merge one. Union-find turns verified
   pairs into groups. On HinGE, **1,938 unique sources form 1,937 groups**: exactly one
   near-duplicate pair was found and merged.
3. **Halt on a degenerate grouping.** If one group held more than 5% of the records
   (`--max-group-frac 0.05`), the threshold would be chaining unrelated sentences together and the
   ratios would be meaningless. The stage exits with code 4 and writes nothing. HinGE's largest
   group holds 8 records, 0.17% of the corpus.
4. **Assign whole groups.** Group ids are sorted, shuffled with seed 42, and each group in turn goes
   to whichever split is furthest below its target share of 80 / 10 / 10. The leakage gate
   (section 3.5.5) then checks the result before any file is written.

## 3.5.3 The splits

| Split | Rows | % of total | Stratified on | Leakage check and result |
|---|---|---|---|---|
| Train | 3,738 | 79.97% | **Not stratified.** Whole near-duplicate source groups assigned by seeded shuffle (section 3.5.4) | Exact and near-duplicate (Jaccard ≥ 0.7) source overlap against dev and test: **0 exact, 0 near**. Gate passed |
| Validation (dev) | 468 | 10.01% | Not stratified, as above | Against train and test: **0 exact, 0 near**. Gate passed |
| Test | 468 | 10.01% | Not stratified, as above | Against train and dev: **0 exact, 0 near**. Gate passed |
| **Total** | **4,674** | **100%** | | 1,938 sources checked across all split pairs, threshold 0.7 |

Rows are records, one per human Hinglish reference. Unique sources per split are 1,549 / 192 / 197.
The shares miss 80 / 10 / 10 by 0.03 points because a group cannot be divided to hit a target.

## 3.5.4 Why the splits are not stratified, and what that costs

We do not stratify, and the table says so rather than naming a stratum to fill the cell.
Stratification would assign records to splits by a feature such as sentence length, code-mixing
level or domain. Each split would then hold a proportional slice of every stratum. The problem is
that stratification works on records, and the records of one source sentence differ in exactly
those features. One reference of a source can be heavily mixed and another barely mixed. A
stratified assignment would therefore place different references, or close paraphrases, of the
**same English sentence** in train and in test. Cross-split leakage is the defect this corpus is
already known for (section 3.5.1), so we chose the constraint that rules it out: a source group
goes to exactly one split, whatever its features.

This has three costs:

- **Shares are approximate.** 79.97 / 10.01 / 10.01 rather than exactly 80 / 10 / 10.
- **Balance is left to the shuffle, so it has to be checked.** It was. With 1,937 groups and a
  largest group of 8 records, a seeded shuffle should produce splits that look alike, and the
  measured composition agrees:

| | Train | Dev | Test |
|---|---|---|---|
| References per source | 2.41 | 2.44 | 2.38 |
| Sources with only one reference | 22 | 1 | 3 |
| English words per record, mean / median | 15.3 / 12 | 15.7 / 12 | 14.1 / 11 |
| Hinglish words per record, mean | 15.9 | 16.3 | 14.9 |
| Code-Mixing Index, mean | 25.3 | 25.5 | 25.9 |
| Sentences containing both languages | 86.3% | 85.3% | 85.5% |
| Switch-point fraction | 0.240 | 0.245 | 0.237 |
| Tagger coverage | 68.3% | 67.1% | 68.6% |

  (`reports/split_balance_hinge.json`.) The code-mixing profile, the quantity the project studies,
  agrees across the three splits to within one CMI point and 0.008 SPF. **Test sentences are
  shorter**, by about 1.2 words on the English side. That is a property of this seed's shuffle and
  is reported rather than corrected, because re-drawing the split until it looked better would be
  tuning on test. Length-sensitive results on the test split should be read with it in mind.
- **Rare strata may be thin.** With 197 test sources, any subgroup of a few percent of the corpus
  has only a handful of test sentences. Per-subgroup results on test will carry wide intervals, and
  the bootstrap intervals in section 4.4 are what make that visible.

## 3.5.5 The leakage gate

The splits are not trusted because of how they were built. They are checked, after assignment and
**before anything is written**, by `src/lrcs/data/leakage.py`:

| Check | What it compares | Threshold | Result on HinGE |
|---|---|---|---|
| Exact | Same normalised English key in two splits | Identity | **0** overlaps |
| Near-duplicate | Character 4-gram Jaccard between sources in different splits | **≥ 0.7**, the same value as grouping | **0** overlaps |
| Shared targets (reported, not gated) | Same Hinglish reference text under different sources in different splits | Identity | 0 |

Two design choices make the gate meaningful rather than a restatement of step 2:

- **One threshold on both sides.** `--dup-threshold` drives grouping and the gate. With two
  values, a pair whose similarity fell between them would pass grouping as "different" and then
  fail the gate as "leaked" on clean data. That bug existed in an earlier version.
- **An independent hash seed.** The gate re-runs MinHash with a different seed, so a
  near-duplicate pair that LSH missed during grouping gets a second, independent chance to be
  caught.

**On any overlap the gate halts the pipeline.** It exits with code 3 and writes no manifest and no
split files. It never only warns. This is demonstrated rather than asserted: the rehearsal log
`reports/rehearsals/2026-10-07/leakage-gate.log` injects one test source into train
(`--inject-leak 1`) and records the gate stopping the run with "No manifest written". The test
suite checks that the gate raises on both an exact and a near-duplicate overlap
(`tests/test_pipeline.py::test_leakage_gate_halts_on_exact_and_near_overlap`).

**One reader trap: test has 197 sources in 196 groups.** That is the single near-duplicate merge
from step 2. Two sources differing only by a stray underscore token
(`… with an _ empty subject line` and `… with an empty subject line`) were joined into one group of
4 records. The group sits entirely in test, which is exactly what grouping is for. If the two had
been assigned separately, one could have landed in train, and the gate would have halted the run.

## 3.5.6 Frozen and version-controlled

The splits are **fixed as of this workbook**. The mechanism is
`data/processed/manifests/hinge_split_manifest.json`, committed on 8 October (`c65faec`). For each
split it records the record count, unique sources, groups, the SHA-256 of the split file, and the
full list of record ids with their own hash. Record ids are content hashes of the normalised
English source and Hinglish reference (`lrcs.text.record_id`). An id therefore means the same pair
on every machine, and the split can be cited without redistributing the corpus.

| Split | SHA-256 of the split file |
|---|---|
| train | `82c045f21bb5d55e5801d606448f5186ec10eaba806f214755cbc317dbc1eed5` |
| dev | `db0b17cca1443108180060ed5d669aef64a8e484b62f45d6173f4921cea3c68a` |
| test | `6ac5d302fe34dd66e99a190f707ca7af7818b36cc64e2162666548f9a0c14478` |

**The freeze has been checked by regeneration, not only declared.** On 9 November the authors'
release was downloaded again (`HinGE.pkl`, SHA-256 `e78c8f48…`, matching the hash pinned in
`docs/datasheet.md`), converted with `scripts/convert_hinge_pkl.py`, and run through
`scripts/run_pipeline.py --seed 42` from `main`. All three split files came out **byte-identical**
to the hashes above, with identical id lists. `scripts/split_balance.py` refuses to describe a split
file whose hash does not match the manifest, so the composition table in section 3.5.4 is a
description of the frozen splits and nothing else.

Rules that follow from the freeze, consistent with section 4.4:

- **No tuning on test.** Prompts, few-shot examples, hyperparameters and checkpoints are chosen on
  dev. Test is scored once per final configuration.
- **Few-shot examples and M3's added vocabulary come from train only.**
- **Synthetic training data is checked against test before it is generated** (298-58, 298-76).
  Back-translated or code-mixed text built from a corpus that contains a test source would leak
  that source past this gate, because the gate only compares our three splits with each other.
- **Changing split membership is a recorded decision.** The project's change-control rule
  (`docs/project_management_plan.md`, 2.2.8) requires a dated rationale and reviewer
  acknowledgement, and a changed split would carry a new manifest hash that every result would
  have to cite.

## 3.5.7 Samples of the prepared data

Two records per split, from `reports/samples/hinge/prepared.md`. That file is generated by
`scripts/emit_stage_samples.py` at seed 42 from the real corpus, eight records per split, sorted
by id before sampling so the selection is reproducible. The layout is the five-column TSV the model
scripts read: `id, group, english, hindi, hinglish`. The `group` column is the group's canonical
key, the smallest normalised source in the group, and is what kept these records' paraphrases in
the same split.

| Split | id | english | hinglish |
|---|---|---|---|
| train | `28e435d5f42aae3a` | Is Taj Mahal in realty the Temple of Lord Shiva? | Is taj mahal in reality shiv ka mandir. |
| train | `40734577ca4987e6` | "So we led you astray because we were ourselves astray." | Hum khud gumhraj the so we led you astray. |
| dev | `44bd818debce1cfc` | Please circulate deposit book to new members. | Kripya jama hundi new members ko circulate kar do. |
| dev | `b29447435d816dbf` | The prevailing colour of this breed is black and white. | iss breed ka samanya rang black aur white hota hai. |
| test | `39507108a31e8c89` | you can have a pack. | you can have ak basta. |
| test | `40fd6b7cae02b0a5` | All data is encrypted with your sync passphrase | Sabhi data aapke passphrase ke sathe encrypt kiya jayega. |

The references keep their writers' own spellings: `gumhraj`, `ak` for *ek* and `sathe` for *saath*.
That is deliberate. Orthographic variance is the phenomenon under study, so preparation never
normalises a reference (section 3.4). The Devanagari `hindi` column travels with each record but is
not a training target. The full sample file, with the group key and the Hindi column, is the one to
cite.

## 3.5.8 Limitations

- **One seed, one split.** The splits are derived at seed 42 only. Model variance is measured over
  three training seeds, but split variance is not measured. A second split seed would show how
  much the test-length difference in section 3.5.4 matters. That would be a separate analysis, not
  a replacement split.
- **The near-duplicate threshold is lexical.** Jaccard over character 4-grams catches near-copies
  and light paraphrases, not translations that share meaning but few characters. Two English
  sources that say the same thing in different words can sit in different splits. No semantic
  check is run.
- **The test split is small for subgroup analysis.** At 197 sources, the error analysis should use
  dev and test together, and the gold evaluation set (0 of 800 items today, 298-55) is the
  intended primary surface.

## Provenance

| Claim | Source |
|---|---|
| Split counts, grouping, gate result | `reports/data_statistics.json`; `data/processed/manifests/hinge_split_manifest.json` |
| Per-split composition | `scripts/split_balance.py` → `reports/split_balance_hinge.json` |
| HinglishEval overlap | `scripts/audit_hinglisheval_overlap.py` → `reports/hinglisheval_overlap.json` |
| Grouping and assignment algorithm | `src/lrcs/data/splits.py` |
| Gate algorithm and halt behaviour | `src/lrcs/data/leakage.py`; `tests/test_pipeline.py`; `reports/rehearsals/2026-10-07/leakage-gate.log` |
| Regeneration check, 9 November | `HinGE.pkl` SHA-256 pinned in `docs/datasheet.md`; `scripts/convert_hinge_pkl.py`; `scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42` |
| Samples | `scripts/emit_stage_samples.py` → `reports/samples/hinge/prepared.md` |
