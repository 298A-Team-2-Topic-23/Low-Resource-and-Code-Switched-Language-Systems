# 1.2 Project Requirements

Linear **298-33**. Owner: Shibin.

The template asks for requirements that are testable and measurable, and says
explicitly that success criteria are to be stated **as numbers**. Every row below
carries a test-and-measure column containing either a number or a procedure that
returns one. A requirement that cannot be failed is not a requirement.

The right-hand column names the Linear issue that implements each requirement, so
the document and the board can be checked against each other.

---

## 1.2.1 Functional requirements

| ID | Requirement | Test and measure | Issue |
|---|---|---|---|
| FR-1 | The system accepts an English sentence and returns Romanized Hinglish | 100% of 800 evaluation items return non-empty output; **0** Devanagari codepoints (U+0900–U+097F) in any output | 298-24 |
| FR-2 | A single command produces a scored run | `python evaluation/run_eval.py --hyp H --ref R --system S` exits 0 and prints chrF++, normalised chrF++, BLEU, ROUGE-L and WER | 298-14 |
| FR-3 | Scoring aggregates across seeds | Three hypothesis files produce mean ± standard deviation for all five metrics in one invocation | 298-14 |
| FR-4 | Misaligned files fail loudly | A hypothesis file with a different line count than the reference exits non-zero before scoring | 298-14 |
| FR-5 | Every run is seeded and logged | One JSON per run in `runs/`, each carrying seed, git commit, package versions and elapsed GPU-hours | 298-26 |
| FR-6 | The compute budget is evidenced, not asserted | `python common/repro.py --summary runs/` prints total GPU-hours against the 80–145 budget | 298-26 |
| FR-7 | Few-shot examples never come from dev or test | Examples are read only from an explicit `--examples` file; the script errors if `--shots > 0` without it | 298-24 |
| FR-8 | Baseline decoding is deterministic | Greedy decoding (`do_sample=False`); the same seed and input produce identical output | 298-24 |

## 1.2.2 AI-powered requirements

| ID | Requirement | Test and measure | Issue |
|---|---|---|---|
| AI-1 | An adapted model beats the zero-shot baseline | **+3 chrF++** over M1 on the 800-item held-out set, with **non-overlapping** error bars across seeds 13 / 42 / 1337 | 298-25 |
| AI-2 | A null result is reported rather than buried | **Under 1 chrF++**, or overlapping error bars, is published as a null result | 298-25 |
| AI-3 | Statistical significance is established, not assumed | Bootstrap resampling, **1000 samples**; mean ± std over exactly **3** seeds | 298-14 |
| AI-4 | The published baseline is reproduced within tolerance | ROUGE-L within **0.01** of **0.617**, and WER compared against **0.633** (Gahoi et al., 2022, Table 2, MixMT Subtask-1, 500 sentences) | 298-15 |
| AI-5 | The tokenizer cost of orthographic variance is quantified | `spelling_variant_burden` reported against a lexicon of ≥ 72 variant groups; **> 1.0** means the vocabulary pays for spelling noise. **Measured: 1.832** | 298-13 |
| AI-6 | Fertility is measured across all four text slices | Fertility, bytes/token, continuation rate, severe-split rate, byte-fallback rate and single-token vocabulary coverage reported for English, Devanagari Hindi, Romanized Hindi and Romanized Hinglish | 298-13 |
| AI-7 | Perplexity is comparable across vocabularies | Reported **per byte**, never per token — per-token perplexity cannot compare M2 to M3 | 298-25 |
| AI-8 | The four models are architecturally distinct | Each differs in parameters updated, tokenizer vocabulary or training distribution — **not** four hyperparameter settings | 298-24/25 |
| AI-9 | Compute is held constant across arms | Identical token and step budget per model, logged in GPU-hours; M2 additionally re-trained to M3's total | 298-26 |
| AI-10 | Human judgement is collected blind | 150–250 segments, system identities hidden, order shuffled per item, ~10% calibration items; **Krippendorff's alpha reported per dimension** | 298-12 |
| AI-11 | Metric validity is checked against humans | Segment-level correlation between chrF++ and human adequacy reported; a weak correlation on code-switched text is reported as a finding | 298-23 |

## 1.2.3 Data requirements

| ID | Requirement | Test and measure | Issue |
|---|---|---|---|
| DR-1 | Splits are disjoint | Leakage gate reports **0** shared keys across every split pair, or the pipeline halts non-zero | 298-11 |
| DR-2 | Splits are reproducible | The same `--seed` produces **byte-identical** SHA-256 digests in the manifest, across separate processes | 298-11 |
| DR-3 | Near-duplicates cannot straddle a boundary | Exact normalised match **and** MinHash/LSH at a shared threshold; whole clusters assigned to one split | 298-11 |
| DR-4 | Released HinGE splits are not used | Audit documents the overlap — **285 of dev's 376** unique English sources (**75.8%**) also appear in train | 298-11 |
| DR-5 | Row counts are measured, never quoted | Pipeline stage 1 prints the count read from the file. **4,799** measured against **4,803** published; both reported until reconciled | 298-19 |
| DR-6 | Provenance is recorded per source | Path, retrieval timestamp, byte count and SHA-256 for every source | 298-38 |
| DR-7 | No raw or annotated data is committed | `data/raw/`, `data/interim/` and `data/processed/` gitignored; `git check-ignore` confirms manifests and `runs/*.json` remain tracked | 298-26 |
| DR-8 | Every source carries a licence entry | **100%** of sources recorded in `docs/datasheet.md` before ingestion | 298-20 |
| DR-9 | Cleaning attrition is itemised | Every filter reports its own removals; **6** filters, no silent drops | 298-38 |
| DR-10 | The evaluation set is three-column | **800** items: English source, Devanagari Hindi reference, Romanized Hinglish reference | 298-21 |
| DR-11 | Code-mixing is characterised, not assumed | CMI, Switch-Point Fraction, M-index and burstiness computed; the measured SPF governs synthetic sampling for M4 | 298-22 |

## 1.2.4 Metrics, fixed before results

chrF++ is the **primary** metric, chosen for its tolerance of Romanized spelling
variance in a way BLEU is not. ROUGE-L and WER are secondary and required for
comparison with the published baseline. Normalised chrF++ is secondary, and the
**divergence between chrF++ and normalised chrF++ is itself the evidence of
orthographic instability**. COMET is excluded for now, with its uncertain coverage
for Romanized Hinglish reported as a limitation rather than quietly relied upon.

These were chosen and justified in writing **before any result was produced**, and
are not to be changed afterwards. Changing the primary metric after seeing results
invalidates the comparison.

## 1.2.5 Requirements not yet satisfied

Stated here rather than discovered at assessment. Each is tracked with an owner.

| ID | Status | Blocker |
|---|---|---|
| DR-1, DR-2, DR-3, DR-4 | **Not met** | PR #4 closed without merging; no `scripts/make_splits.py` or manifests on `main`. Splits are a requirement, not an achieved fact |
| DR-10 | **Not met** | `data/goldtestset/gold_set.csv` holds a header row and 0 of 800 items |
| AI-1, AI-2, AI-7 | Not yet testable | M2 not trained; blocked on splits and GPU allocation |
| AI-4 | Not yet testable | Baseline reproduction not run; Gahoi et al. released no code |
| AI-11 | Partially met | Normalised chrF++ currently collapses only 3 of the 72 lexicon groups (see 298-23) |
| AI-5, AI-6 | **Met** | Burden 1.832 measured; fertility reported in `reports/spelling_variance.md` |
| FR-2 to FR-6 | **Met** | Harness and reproducibility scaffolding merged and tested |
