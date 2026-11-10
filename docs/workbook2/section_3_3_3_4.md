# 3.3 Data Pre-processing

Linear **298-63**. Written by Thomas Lnu, Shibin Biji.

Pre-processing is stage 2 of the pipeline (`src/lrcs/data/clean.py`). It decides which records
are usable as supervision, removes the rest with a stated reason for each, and tags every
surviving token with its language. Every count here comes from the real HinGE run of 8 October
(`reports/data_statistics.json` → `attrition`, run record
`runs/20261008T043208Z_data-pipeline_seed42.json`, input CSV SHA-256 `dcfaf37c…`). None was
typed in by hand.

## 3.3.1 What pre-processing removes, and how many

Stage 1 hands stage 2 **4,799** records, one per human reference. Six filters run in a fixed
order. **Each record is charged to the first filter that rejects it**, so a record that would
fail two rules is counted once. That is why the six removal counts below sum to exactly the
total, 125, rather than overstating it.

| # | Filter | In | Removed | Out | % removed | What it rejects |
|---|---|---|---|---|---|---|
| 1 | `missing_field` | 4,799 | 0 | 4,799 | 0.00% | English or Hinglish empty after normalisation |
| 2 | `not_romanized` | 4,799 | **25** | 4,774 | 0.52% | Reference more than 20% Devanagari: a Hindi sentence in the Hinglish column |
| 3 | `untranslated` | 4,774 | 0 | 4,774 | 0.00% | Reference identical to the English source, ignoring case and punctuation |
| 4 | `length_bounds` | 4,774 | **87** | 4,687 | 1.82% | Fewer than 2 or more than 60 words on either side |
| 5 | `length_ratio` | 4,687 | **11** | 4,676 | 0.23% | Hinglish-to-English word ratio above 3.0 or below 1/3 |
| 6 | `exact_duplicate` | 4,676 | **2** | 4,674 | 0.04% | Same (English, Hinglish) pair as an earlier record |
| | **Total** | **4,799** | **125** | **4,674** | **2.60%** | |

Attrition is small. HinGE is a curated, human-written corpus, so most filters are guards that
found little to remove. Two zeros are still informative:

- No reference is empty after normalisation.
- No annotator copied the English through untranslated.

Both are checked rather than assumed, so a future corpus that does contain these defects will
show them in this table.

The attrition table keeps three record ids per filter, for example `aac61091e3fa9cd4`,
`4179c759dc734cf5` and `c7b7363d5982a61f` for `not_romanized`. A removal can therefore be traced
to a specific record without the corpus text being redistributed.

## 3.3.2 Why each threshold is set where it is

The thresholds are pipeline defaults (`DEFAULTS` in `clean.py`), recorded in every run under
`params.clean`. Each was chosen for a reason about the task, not tuned to the corpus.

| Parameter | Value | Why this value |
|---|---|---|
| `max_devanagari` | 0.2 | The task output is **Romanized** Hinglish, so a mostly-Devanagari reference is mislabelled rather than hard: it would train the model to emit the wrong script. 0.2 rather than 0 tolerates a stray danda (।) or one quoted Devanagari word in an otherwise Romanized sentence. The corpus contains exactly that case: the kept reference with the most Devanagari (`23d8e2aaeba2a5a0`) glosses one word in brackets, `jeevan ke aam star(स्तर)`, and is a good Romanized reference. Both `not_romanized` samples in 3.3.4 have a share of 1.00. This matters later: Model 1's zero-shot smoke run produced Devanagari in 13 of 48 outputs, so the training references must not teach the same error |
| `min_words` | 2 | A one-word reference contains no code-switching. With a single token there is no switch point, so CMI and switch-point fraction (section 3.6) are undefined, and the pair teaches a lexical lookup rather than sentence generation |
| `max_words` | 60 | At 60 words a source, prompt and target stay well inside the 512-token training context of `models/train_qlora.py`, even at the Hinglish tokenizer fertility measured in section 3.6. Truncating longer references instead would cut the target and train on an incomplete sentence. The cost in coverage is one combined figure: `length_bounds` removed 87 records (1.82%) across both bounds. The kept data still spans 3–60 English words and 2–60 Hinglish words, with a 95th percentile of 37 and 39 (section 3.6), so the cap trims only the extreme tail |
| `max_ratio` | 3.0 | The mean Hinglish-to-English word ratio on this corpus is **1.062** (section 3.6): code-switching is close to length-neutral. A pair three times longer on one side is not a stylistic variant. One side carries content the other lacks, from a misalignment or a partial translation. The ratio is applied in both directions, and it removed 11 records (0.23%) |

`exact_duplicate` uses the same key as the split stage (`dedup_key` in `src/lrcs/text.py`: NFKC,
lower-case, punctuation to space), so a pair that differs only in case or punctuation counts as
a repeat. Near-duplicates are deliberately **not** removed here. They are kept and grouped at
the split stage (section 3.5), so that every member of a cluster lands in one split. Deleting
them would throw away legitimate alternative references.

## 3.3.3 Language tagging

Every token of a surviving reference is tagged in the LinCE scheme (Aguilar et al., 2020). `lang1` is English and
`lang2` is Romanized Hindi; `ambiguous`, `ne` (named entity), `other` and `unk` cover the rest.
The tagger is a documented rule list, not a learned model. Its rules are applied in order and
listed in the `clean.py` docstring. Its Hindi markers include every surface form in
`analysis/spelling_variants.tsv`, so a variant spelling such as `nhi` is tagged as Hindi and
not left unknown.

On the real corpus the tagger resolves **68.2%** of tokens. The code-mixing statistics in
section 3.6 are computed only over resolved tokens, and that coverage figure is quoted with
them every time. Tagging adds one field, `tags`, which is why pre-processed records carry 7
fields against the 6 of a raw record.

## 3.3.4 Samples: what each filter removed, and what survived

These are real HinGE records, from `reports/samples/hinge/preprocessed.md` and
`reports/samples/hinge/edge_cases.md`. They were generated by `scripts/emit_stage_samples.py`
at seed 42 from the converted corpus (SHA-256 `dcfaf37c…`), so they come from the same input
as the counts in 3.3.1. Cells over 160 characters are truncated (…), and the word counts give
the real length.

**Before: records each filter removed.** `missing_field` and `untranslated` removed nothing,
so they have no samples.

| Filter | id | English | Hinglish reference | EN / HI words | Devanagari share |
|---|---|---|---|---|---|
| `not_romanized` | `25d14df58530e197` | The backend for this address book refused to perform this query.% s | इसलिए तुम ज्ञान का विषय नहीं हो सकतीं। | 12 / 13 | 1.00 |
| `not_romanized` | `d4e6e5e3e333e086` | causing no headiness or intoxication. | उस कंपनी के लिए व्यावृत्तियां जिनमें जनता पर्याप्त रूप से हितबद्ध है | 5 / 26 | 1.00 |
| `length_bounds` | `25653bce641a520e` | (b) where the marriage of his parents does not subsist, in the net wealth of that parent who maintains the minor child… | (b)Jaha uske parents ka vivah astitva me nahi he, in the net wealth of that parent… | 92 / 90 | 0.00 |
| `length_bounds` | `e55772ffc6ce674d` | Unto this, then, summon (O Muhammad). And be thou upright as thou art commanded… | Atah isi liye bulao, aur jaisa ki tumhe hukam diya gaya he swayam kaayam raho… | 72 / 79 | 0.00 |
| `length_ratio` | `375630323aae34bd` | Ancient sculptures and murals , as can be expected , abound with illustrations of this instrument . | At the end of the fourth day this state of extraordinary elation passed away and Rabindra ne is sthiti ka ativuman kar liya… | 14 / 51 | 0.00 |
| `length_ratio` | `cc3bc7a3e3098f60` | It was difficult not to think about what he had left behind. | Our Lord, we have heard the caller calling to belief, "Believe in your Lord!" So we believe. Ae hamare paalne vaale… | 12 / 41 | 0.00 |
| `exact_duplicate` | `b0e23483d3cbdf22` | Whether accelerated compositing should be enabled | Kya twarit compositing should be enabled | 6 / 6 | 0.00 |
| `exact_duplicate` | `c0474c83aeb9960b` | if culture changes us, as indeed it does, | agar sanskruti hume change karti ho, as indeed it does, | 8 / 10 | 0.00 |

The samples show the filters catching worse defects than their names suggest:

- **Both `not_romanized` samples are also misaligned.** `इसलिए तुम ज्ञान का विषय नहीं हो
  सकतीं` ("so you cannot be the subject of knowledge") is not a translation of a sentence
  about an address book. These references are not just in the wrong script; they belong to a
  different sentence.
- **Both `length_ratio` samples are misaligned too.** The Hinglish describes Rabindranath's
  elation, or recites a prayer, while the English is about sculpture, or about leaving
  something behind. The 3.0 ratio was argued in 3.3.2 as a misalignment detector, and these
  two show it working as one.
- **The `length_bounds` samples are 72–92-word legal and scriptural passages.** They are
  correct, but they are long enough to dominate a training batch.

**After: records that survived, with their language tags.**

| id | English | Hinglish reference | Tags |
|---|---|---|---|
| `0cae6ed706b2f461` | There is another gurudwara in Great Nicobar at Campbell Bay . | There is another gurudwara Great Nicobar ke Campbell Bay me he. | lang1 lang1 lang1 lang1 lang1 lang1 lang2 lang1 lang1 lang2 lang1 other |
| `713f63f4f29b752c` | It will be easier if the boxes are fitted with bolts. | It will be easier if boxes ko band karne ke liye unme kabje aur kunde ho. | lang1 lang1 lang1 lang1 lang1 lang1 lang2 unk unk lang2 lang2 unk unk lang2 unk lang2 other |
| `40734577ca4987e6` | "So we led you astray because we were ourselves astray." | Hum khud gumhraj the so we led you astray. | lang2 unk unk lang2 lang1 lang1 lang1 lang1 lang1 other |

The `unk` tags show the tagger coverage limit from 3.3.3 at the token level. `band`, `karne`,
`kabje` and `kunde` are Hindi, but they are not in the marker list, so they stay unresolved
rather than being guessed.

**Two kept records show what pre-processing does not catch.** These come from
`edge_cases.md`.

| Why it is shown | id | English | Hinglish reference |
|---|---|---|---|
| Shortest kept reference | `189cf49b6403e723` | Central European (_ MacCE) | Centraleuropeay(_ MacCE) |
| Most Devanagari in a kept reference | `23d8e2aaeba2a5a0` | We must now utilize our enlarged capacities to raise the general standards of living. | Hame ab apni enlarged capacities ka upyog jeevan ke aam star(स्तर) ko uncha uthane ke liye krna hoga |

The first is a software-localisation string that passes all six filters. Filters check form
(script, length, ratio, duplication), not content, so domain noise of this kind remains in the
corpus. It is stated here rather than filtered, because no rule we could justify in advance
would remove it without also removing good short references. The second is the case the 0.2
Devanagari tolerance was set for (3.3.2).

The six rules are also covered by the test suite's own fixtures, one defect per filter, in
`test_each_filter_removes_its_own_defect` (`tests/test_pipeline.py`). The test asserts that
each filter removes exactly its own defect, and that ingested minus removed equals kept.

## 3.3.5 Validation

Pre-processing is validated by tests and by a gate, not by inspection. The full suite passes:
**114 tests, 2 skipped**, on `main` at the commit that adds this section. The tests that bear
on this stage are:

| Test | File | What it proves |
|---|---|---|
| `test_each_filter_removes_its_own_defect` | `tests/test_pipeline.py` | Each of the six filters fires on its own defect, and the counts add up |
| `test_tagger_rules` | `tests/test_pipeline.py` | The LinCE tagging rules resolve as documented |
| `test_pipeline_end_to_end` | `tests/test_pipeline.py` | Ingest, clean, split and statistics run as one command and write a manifest |
| `test_pipeline_halts_on_injected_leak_and_writes_no_manifest` | `tests/test_pipeline.py` | The leakage gate fails the run rather than warning |
| `tests/test_emit_stage_samples.py` | — | Sample selection is deterministic at a fixed seed |

The leakage gate runs after the split. On the real corpus it found **0** exact and **0**
near-duplicate overlaps across all three split pairs.

---

# 3.4 Data Transformation

Linear **298-63**. Written by Thomas Lnu, Shibin Biji.

Transformation covers every change of form between the file the authors released and the TSV
the model scripts read. There are five. Each exists for a stated reason, and none changes what
a reference says.

**One rule governs all of them: spelling is never normalised in the corpus.** The orthographic
variance of Romanized Hinglish (`nahi`, `nhi`, `nahin`) is the phenomenon this project
measures. If the training data or the references were normalised, the spelling-variant burden
in section 3.6 would vanish from the data and the Model 3 hypothesis would have nothing to act
on. Spelling normalisation exists in exactly one place, inside the normalised-chrF++ metric in
`evaluation/run_eval.py`, which says so in a comment: *"used for the normalised metric ONLY.
Never normalise training data or the gold references themselves."* Every transformation below
is structural.

## 3.4.1 The transformations, and why each exists

| # | Transformation | Where | Why |
|---|---|---|---|
| 1 | **Pickle to CSV** | `scripts/convert_hinge_pkl.py` | HinGE is released only as a pandas pickle, and loading an untrusted pickle can run arbitrary code (see 3.4.2) |
| 2 | **Column selection** | Stage 1, `src/lrcs/data/ingest.py` | Of the released columns, only English, Hindi and the human Hinglish references are carried forward. The machine-generated WAC and PAC outputs and their ratings are not supervision for this task and are dropped |
| 3 | **Unicode NFC and whitespace collapse** | Stage 1, `normalise()` in `src/lrcs/text.py` | Gives one code-point sequence per grapheme, so two strings differ only when their text really differs. It is applied once, at ingest, so later stages cannot disagree about what a string is |
| 4 | **One record per reference** | Stage 1 | HinGE stores several human references for one English sentence in a single list cell. Supervision needs one (source, target) pair per row |
| 5 | **Split TSV layout** | Stage 3 | The five columns `id, group, english, hindi, hinglish` that the model scripts read |

## 3.4.2 Pickle to CSV, and why the pickle is not loaded directly

Python's own documentation warns that unpickling data from an untrusted source can execute
arbitrary code. The ingest stage refuses `.pkl` files for that reason, and
`test_ingest_refuses_pickles` checks it. The release still has to be opened once, so the
converter is the one controlled place where that happens. Three safeguards apply:

1. **Hash first.** With `--expected-sha256`, the file is refused before it is opened unless its
   SHA-256 matches the authors' release, `e78c8f48…bc5960`, recorded in `docs/datasheet.md`.
2. **Restricted unpickler.** The converter subclasses pandas' own compatibility unpickler and
   allows only pandas and numpy classes, plus `functools.partial` and `builtins.slice`.
   Anything else, such as `os.system`, raises before it is called.
3. **Tested against an attack.** `tests/test_convert_hinge_pkl.py` builds a pickle whose payload
   calls `os.system`, and asserts that it is refused and that no output file is written.

The converter writes every released column unchanged, so the CSV is a faithful copy. Selection
happens at ingest, where it is logged. On the real release, the conversion read 1,976 rows and
4,799 human references and wrote `data/raw/hinge.csv` (SHA-256 `dcfaf37c…`). That hash is the
`input_sha256` in the split manifest, which ties every split back to this conversion.

## 3.4.3 Unicode and whitespace normalisation, before and after

`normalise()` applies NFC and collapses any run of whitespace, including non-breaking spaces,
to a single space. Because it runs inside ingest, no un-normalised record exists afterwards to
show. These are the function's real outputs on two constructed strings:

| Input | Output | What changed |
|---|---|---|
| `"kya  tum⍽aaj   shaam free ho? "` (⍽ is a non-breaking space) | `"kya tum aaj shaam free ho?"` | Double space, non-breaking space, triple space and trailing space each become one space or none |
| `cafe` followed by a combining acute accent (5 code points) | `café` (4 code points) | The decomposed form becomes the precomposed one; the two now compare equal |

Case, punctuation and spelling are left untouched. `Main` and `main`, or `nahi` and `nhi`,
remain distinct in the corpus.

## 3.4.4 One source row to several records

The 1,976 released rows become **4,799** records, a mean of **2.41** references per source
(`references_per_source` in `data_statistics.json`). The spread is uneven:

| References per source | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Sources | 26 | 1,470 | 166 | 210 | 37 | 21 | 5 | 3 |

**Sample: one row becoming eight records** (`reports/samples/hinge/transformed.md`). Source row 3
carries the corpus's maximum of 8 human references for one English sentence:

| id | ref | hinglish (English source for all eight: *In the year 1985-86, the erstwhile Ministry of Welfare was bifurcated into the Department of Women and Child Development and the Department of Welfare.*) |
|---|---|---|
| `a28bb3f5730d9ef1` | 0 | In the year 1985-86, purvarti kalyan mantralay was bifurcated into mahila aevam baal vikaas vibhaag and kalyan vibhaag. |
| `cf40e184e12a52de` | 1 | Varsh 1985-86 mein erstwhile Ministry of Welfare ko department of women and child development aur department of welfare mein vibhaajit kiya gya tha. |
| `aebf2bd6f28fc7fe` | 2 | In the year 1985-86, purvarti kalyan mantralay ko department of women and child development aur department of welfare mein vibhajit kiya tha. |
| `8fd326de37710d1f` | 3 | Varsh 1985-86 mein erstwhile Ministry of Welfare was bifurcated into mahila aevam baal vikaas vibhaag and kalyan vibhaag. |
| `3f8e31225745a7b3` | 4 | varsh 1985-86 me erstwhile ministry of welfare ko department of Women and children development and department of welfare me bifurcate kiya gaya tha. |
| `dd28a087bc8ee44c` | 5 | In the year 1985-86, poorvavarti kalyan mantralay ko mahila aivam baal vikas vibhag and kalyan vibhag me bifurcate kiya. |
| `f996744fa1d6b3c7` | 6 | In the year 1985-86, poorvavarti kalyan mantralay was bifurcated into mahila aivam baal vikas vibhag and kalyan vibhag me vibhakt kiya gaya tha. |
| `b2fc7bf340568161` | 7 | poorvavarti kalyan mantralay ko year 1985-86 me mahila aivam baal vikas vibhag aur kalyan vibhag me bifurcate kiya gaya tha. |

These eight references are also the clearest argument for not normalising spelling in the
corpus. The same words appear as `purvarti` and `poorvavarti`, `vikaas` and `vikas`, `vibhaag`
and `vibhag`, `aevam` and `aivam`, and `gya` and `gaya`, all from human writers rendering one
sentence. The references also choose differently which words stay in English (`bifurcated`,
`department of welfare`) and which become Hindi (`vibhaajit`, `kalyan vibhag`). Normalising
the first would erase the orthographic variance that section 3.6 measures. The second is the
code-switching itself.

The reference-list cell is parsed with `ast.literal_eval`, which accepts literals only and never
evaluates code (`test_ingest_explodes_hinge_list_cells`). Each record keeps `row` and `ref`, its
source row and its index within that row's list, so it can be traced back to the release.
Expansion has two consequences that later sections depend on:

- **Splits are made by source, not by record.** All references of one English sentence go to
  the same split (`test_splits_are_disjoint_and_keep_references_together`). Otherwise a model
  could be tested on a sentence whose other references it was trained on.
- **Evaluation scores each source once, against all its references** (section 4.4). The test
  split holds 468 records but only 197 sources, so scoring per record would weight a source by
  how many references it happens to have.

## 3.4.5 Identifiers

Two identifiers are derived from content, so they mean the same thing on every machine and
every run:

- **Record id**: the first 16 hex digits of SHA-256 over the `dedup_key` of English and
  Hinglish (`record_id()` in `src/lrcs/text.py`). A whitespace-only difference cannot mint a
  new id. `I am going.` / `main ja raha hoon.` and `I am  going.` / `main ja raha hoon. ` both
  give `73597613f21a4495`.
- **Group id**: assigned at the split stage. It is the lexicographically smallest `dedup_key`
  in a near-duplicate cluster, so it depends on content alone and not on set iteration order.
  Before this, group membership depended on set iteration order, which made the split
  non-deterministic until it was fixed in Cycle 2.

## 3.4.6 The layout the model scripts read

Stage 3 writes `data/processed/hinge/{train,dev,test}.tsv`. These files are gitignored, and
their SHA-256 digests are committed in `data/processed/manifests/hinge_split_manifest.json`.
Each file has five columns:

| Column | Content | Why it is carried |
|---|---|---|
| `id` | Record id (3.4.5) | Cites a record without redistributing its text |
| `group` | Near-duplicate group id | Keeps clusters in one split, and allows grouping by source at evaluation |
| `english` | Source sentence | Model input |
| `hindi` | Devanagari Hindi | The baseline reproduction's original two-input condition needs it (section 4.4) |
| `hinglish` | One human Romanized reference | Training target and reference |

The stage-2 `tags` field is not written to the split files. It feeds the code-mixing statistics
and is not model input. That is why the record goes from 7 fields to 5 between pre-processing
and transformation, as in the stage table of section 3.6.

**Sample: three records from the real split files** (`reports/samples/hinge/transformed.md`,
seed 42; the Hindi column is shown as released):

| id | group | english | hindi | hinglish |
|---|---|---|---|---|
| `083e973483d240c9` | the label used for menu items and buttons that activate this action | The label used for menu items and buttons that activate this action. | मेनू मद व बटन के लिये लेबल जो इस क्रिया को सक्रिय करता है. | The label used for menu items and buttons jo kriya ko activate karta hai. |
| `28e435d5f42aae3a` | is taj mahal in realty the temple of lord shiva | Is Taj Mahal in realty the Temple of Lord Shiva? | क्या ताजमहल वास्तव में शिव मंदिर है? | Is taj mahal in reality shiv ka mandir. |
| `b2fc7bf340568161` | in the year 1985 86 the erstwhile ministry of welfare was bifurcated into the department of women and child development and the department of welfare | In the year 1985-86, the erstwhile Ministry of Welfare was bifurcated into the Department of Women and Child Development and the Department of Welfare. | वर्ष 1985-86 में पूर्ववर्ती कल्याण मंत्रालय को महिला एवं बाल विकास विभाग तथा कल्याण विभाग में विभक्त किया गया था। | poorvavarti kalyan mantralay ko year 1985-86 me mahila aivam baal vikas vibhag aur kalyan vibhag me bifurcate kiya gaya tha. |

The `group` column is the `dedup_key` of the English source: lower-cased, with punctuation
removed. It is the same transformation that `exact_duplicate` uses (3.3.2). The `english` and
`hinglish` columns keep their original case and punctuation, because only the grouping key is
normalised.

## Provenance

| Claim | Source |
|---|---|
| Attrition counts, thresholds, example ids | `reports/data_statistics.json` → `attrition`, `params.clean`; run of 8 October, commit `c65faec` |
| References per source, length and ratio figures | `reports/data_statistics.json` → `references_per_source`, `lengths_words`; section 3.6 |
| Tagger coverage 68.2% | `reports/data_statistics.json` → `code_mixing` |
| Filter order and rules | `src/lrcs/data/clean.py` (298-38) |
| Normalisation, ids and the outputs in 3.4.3 and 3.4.5 | `src/lrcs/text.py`; outputs produced by running those functions |
| Pickle conversion and its safeguards | `scripts/convert_hinge_pkl.py`, `tests/test_convert_hinge_pkl.py`, PR #21 (298-44) |
| Input and split hashes, sources per split | `data/processed/manifests/hinge_split_manifest.json` |
| Every real sample record in 3.3.4 and 3.4 | `reports/samples/hinge/*.md`, generated by `scripts/emit_stage_samples.py --input data/raw/hinge.csv --seed 42` from HinGE.pkl SHA-256 `e78c8f48…` |
| Test count | `python -m pytest -q` on `main` at the commit adding this section |
| Devanagari in 13 of 48 zero-shot outputs | `runs/20261022T213153Z_model1-0shot_seed13.json`; `docs/COMPUTE_BUDGET.md` |
