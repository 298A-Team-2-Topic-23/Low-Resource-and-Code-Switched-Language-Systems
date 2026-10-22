# 2.1 Data Management Plan

Author: Shevkar, Yash · Linear **298-35**

The licence record this section draws on is [`docs/datasheet.md`](../datasheet.md). Every count below was read off a file by `scripts/run_pipeline.py` on 8 October 2026 and is committed in [`reports/data_statistics.json`](../../reports/data_statistics.json) and [`data/processed/manifests/hinge_split_manifest.json`](../../data/processed/manifests/hinge_split_manifest.json). A published number appears only where it disagrees with a measurement, and both are kept.

There is no separate department template for this section in the repository. The five parts below are the ones the issue requires: collection, acquisition and provenance, storage, the split hazard, and use and licensing.

---

## Collection

HinGE is the only corpus this project has ingested (Srivastava & Singh, 2021). The release is `HinGE.pkl`, from the authors' Google Drive folder linked in the datasheet. The pipeline refuses pickles, because unpickling a downloaded file can run code. `scripts/convert_hinge_pkl.py` converts it once, allowing only pandas and numpy classes, and refuses the file unless its SHA-256 is `e78c8f48af3eea0b141e767082189b7b619e9cbe50ad8f0b2a4863b82ebc5960`. The CSV it writes is what stage 1 counts.

Counted off that CSV: **1,976** English–Hindi rows, and **4,799** human Hinglish references after the list-valued Hinglish column is expanded. The paper reports **4,803**. The two figures differ by four. Both stay in the record. Reconciliation is open, owned by Yash, and is a re-count of Table 1 of the paper against the file before Workbook 2 on 11 November 2026. Editing our count so that it matches the paper is not a reconciliation.

The committed pipeline uses the human-generated Hinglish column only. WAC and PAC are in the release and are not training targets. An earlier note described an 8,751-row flattening that added those columns. That file is not an input to `scripts/run_pipeline.py`.

Six filters then run, in a fixed order. A removed record is charged to the first filter that rejects it, so the table adds up.

| Filter | What it catches | Removed | Left |
|---|---|---:|---:|
| missing_field | empty English or Hinglish | 0 | 4,799 |
| not_romanized | Devanagari in the Hinglish column | 25 | 4,774 |
| untranslated | English copied through as Hinglish | 0 | 4,774 |
| length_bounds | under 2 or over 60 words | 87 | 4,687 |
| length_ratio | Hinglish/English length outside ⅓–3× | 11 | 4,676 |
| exact_duplicate | the same pair twice | 2 | **4,674** |

**125** records removed (2.6%), **4,674** kept.

Normalisation, applied once at ingest, is Unicode NFC and collapsed whitespace (`src/lrcs/text.py`). Spelling is not normalised. `nahi` and `nhi` remain different strings, because the claim under test is that this difference is what the tokenizer pays for. Collapsing it before training would erase the measurement.

Three further sources are in scope and have not been downloaded: the IIT Bombay English–Hindi corpus, which is the origin of HinGE's source sentences; Samanantar, the candidate parallel data for later synthetic generation; and Dakshina, the candidate romanization lexicon. The team-authored gold set has a schema, guidelines and a validator, and **0 of 800** items. The MixMT 2022 Subtask-1 test set, needed for the baseline reproduction, is not in this repository.

## Acquisition and provenance

Stage 1 records the path, the file timestamp, the byte count, the SHA-256, the rows in the file, and the references after expansion. Those fields for the CSV the pipeline actually read:

| Field | Value |
|---|---|
| Path | `data/raw/hinge.csv` |
| File timestamp | 2026-10-08T04:30:48Z |
| Ingested | 2026-10-08T04:32:08Z |
| Bytes | 1,591,630 |
| SHA-256 | `dcfaf37ca9d7528e27da7be6b0cfffafb8bbe7825fe4da45077b96236cd9c9c3` |
| Rows in the file | 1,976 |
| Human references | 4,799 |
| Hindi column present | yes |

The pickle this CSV was converted from is pinned at SHA-256 `e78c8f48af3eea0b141e767082189b7b619e9cbe50ad8f0b2a4863b82ebc5960`. The Drive folder is recorded in `docs/datasheet.md`. IIT Bombay, Samanantar and Dakshina have no retrieval record, because no file has been fetched.

## Storage

Three tiers, and the gitignore is what enforces them. Raw and processed sentences never enter the repository. Manifests do, so a split can be cited without redistributing licensed text.

| Tier | Path | In git | What is there |
|---|---|---|---|
| Raw | `data/raw/` | no | `HinGE.pkl` and the converted `hinge.csv` |
| Interim | `data/interim/` | no | Reserved. The current pipeline keeps cleaning in memory and does not write a separate interim file |
| Processed | `data/processed/hinge/{train,dev,test}.tsv` | no | The split files. Columns are `id`, `group`, `english`, `hindi`, `hinglish` |
| Manifests | `data/processed/manifests/` | yes | Parameters, record ids, and the SHA-256 of each split file |
| Statistics | `reports/data_statistics.json`, `reports/figures/` | yes | Measured counts and figures, not the sentences |
| Run logs | `runs/*.json` | yes | Seed, commit, packages, and elapsed time for each run |
| Gold-set schema | `data/goldtestset/` | yes | Guidelines, validator, and a header-only CSV. No HinGE sentences are in it yet |

There is no shared object store. The raw file lives on the machine that ran the conversion, outside git. The only shared copy of the release is the authors' Drive folder. A lost laptop loses the sentences and not the manifests. The sentences are recovered from that folder and checked against the pinned SHA-256 before the pipeline is run again.

## The split hazard

HinGE publishes no train/dev/test split. A different, downstream release does: the INLG HinglishEval shared-task files, which reuse HinGE's English sources with a single Hinglish output each. Those files are not disjoint. The audit on 25 September 2026 found **285 of 376** unique English sources in the released dev file (**75.8%**) also in the released train file. They are not used anywhere in this project. The script that ran that audit is not on `main`. The finding is.

Our own splits are derived, and they are done. `python scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42` groups by the normalised English source, so every human reference of one sentence stays in one split. Near-duplicates are grouped when the exact Jaccard similarity of character 4-gram shingles is at least **0.7**. MinHash, 96 permutations, only proposes candidates. Every candidate is checked with exact Jaccard, so a hash collision cannot merge two sentences that are not actually similar. Whole groups are assigned by a seeded shuffle.

The leakage gate then re-checks with the same threshold and an independent hash seed. On this corpus it checked 1,938 sources and found **0** exact overlaps and **0** near-duplicate overlaps. A failure exits with code 3 and writes no manifest. The committed run passed. One near-duplicate pair was merged during grouping, which is why 1,938 sources became 1,937 groups. That pair sits inside test: 197 sources, 196 groups.

| Split | Records | Unique sources | Groups | SHA-256 of the split file |
|---|---:|---:|---:|---|
| train | 3,738 | 1,549 | 1,549 | `82c045f21bb5d55e5801d606448f5186ec10eaba806f214755cbc317dbc1eed5` |
| dev | 468 | 192 | 192 | `db0b17cca1443108180060ed5d669aef64a8e484b62f45d6173f4921cea3c68a` |
| test | 468 | 197 | 196 | `6ac5d302fe34dd66e99a190f707ca7af7818b36cc64e2162666548f9a0c14478` |

An earlier derivation, 7,004 / 867 / 880 rows over a human-plus-WAC-plus-PAC flattening, with 128 permutations, is on the unmerged branch `yash/298-11-hinge-splits`. It is not the split this project uses. The datasheet used to quote those counts against the committed manifest. That paragraph now matches the manifest.

## Use and licensing

| Source | Role | Measured size | Licence | Where it lives |
|---|---|---|---|---|
| HinGE | English→Hinglish supervision for M1–M4, and the pool the 800-item set will be drawn from | 1,976 rows; 4,799 human references; 4,674 after cleaning; CSV 1,591,630 bytes | Unstated. Treated as CC-BY-NC-4.0-equivalent | `data/raw/hinge.csv` on the machine that converted it; not in git |
| IIT Bombay English–Hindi corpus | Origin of HinGE's English and Hindi columns. Not ingested separately | Not ingested. No measured size | CC-BY-NC-4.0 | Not held |
| Samanantar | Candidate parallel data for synthetic generation (Model 4). Not downloaded | Not ingested. No measured size | CC-BY-NC-4.0 by team decision on 25 Sep 2026. AI4Bharat's own pages also say CC0 for the packaging; the more restrictive reading is the one we use | Not held |
| Dakshina | Candidate romanization lexicon. Not downloaded | Not ingested. No measured size | CC BY-SA 4.0, share-alike | Not held |
| Gold evaluation set | Held-out three-column set the success criterion is defined on | 0 of 800 items | Team-authored, not yet written. Any HinGE sentence copied into it stays non-commercial | `data/goldtestset/gold_set.csv`, header only, in git |
| MixMT 2022 Subtask-1 test set | The 500-sentence set the baseline reproduction is scored on | Not ingested. No measured size | Not yet recorded. The datasheet still owes this entry | Not held |

HinGE states no licence on the download page, in the paper, or in the AI4Bharat catalogue entry that links it. The English and Hindi columns are drawn from IIT Bombay, which is CC-BY-NC-4.0, so those columns are non-commercial at minimum. The Hinglish columns HinGE added have no licence of their own that we could find. Until the authors say otherwise, the whole release is treated as CC-BY-NC-4.0-equivalent: non-commercial, attribution by citation. Commercial reuse of the data or of models trained on it is out of scope. Confirming this with the authors is still open.

Samanantar is not used yet. Before any synthetic pairs are generated from it, its English sources have to be checked against our test split at the same Jaccard threshold of 0.7. A different threshold is how pairs slipped through an earlier version of the gate. The split gate cannot do this job: it only compares our splits with each other. That check is issue 298-58, due 9 November, and it does not exist yet. Generating first and checking afterwards would make every Model 4 number invalid.

Dakshina is not used yet. Its share-alike term is stricter than the other three. No Dakshina text goes into a committed file until the licence that file would have to carry is decided.

The gold set is empty. The +3 chrF++ success criterion is defined on it, so the criterion cannot be evaluated until the items exist. That authoring is not this issue.
