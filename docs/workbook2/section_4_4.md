# 4.4 Model Evaluation Methods

Linear **298-68**. Written by Thomas Lnu, Shibin Biji.

This section fixes how every model in section 4.1 will be scored, and it is committed **before
any real result exists**. On the day it merged, the only scored output in the repository was
three single-seed smoke runs on 48 synthetic lines with a 0.5B stand-in model
(`results/results.jsonl`, 22 October, commit `f8cb929`). `docs/COMPUTE_BUDGET.md` records those
runs as not reportable. No model had been scored on the HinGE test split, the gold set or MixMT
(298-53 and 298-54 were still open). A reader can check this ordering in the git log.

**This section will not be revised after results are seen.** If a metric or method later turns
out to be wrong, the correction goes in the carry-forward table with its date, and this text
stays as committed. A change to the primary metric after results exist would invalidate the
comparison the project is built on.

## 4.4.1 Metrics, and when each was committed

None of these metrics is new in Workbook 2. Each was named in writing before this section, and
the dates below are the commits that first did so, not the date of this section.

| Metric | Scale | Role | Why this metric | Measured on | First committed |
|---|---|---|---|---|---|
| **chrF++** | 0–100 | **Primary** | Character n-gram F-score plus word bigrams (`word_order=2`). Romanized Hinglish has no standard spelling (`nahi`, `nhi`, `nahin`), and character n-grams give partial credit for a variant spelling where BLEU's exact word match gives none | 800-item gold set; HinGE test split until the gold set exists | Harness `0ac53f8`, 25 Sep; Workbook 1 §1.2.4, `cd627d0`, 7 Oct |
| Normalised chrF++ | 0–100 | Secondary | chrF++ after spelling variants are collapsed to one form. The **gap** between raw and normalised chrF++ is the measurement of how much error is orthographic rather than semantic | Same as chrF++ | Same commits |
| ROUGE-L | 0–1 | Secondary; **reproduction gate** | The published baseline's own metric, needed to check the harness against Gahoi et al. (2022), Table 2 | MixMT Subtask-1 test set, 500 sentences; also every model on the HinGE test split | Same commits |
| WER | 0–1 | Secondary | The baseline's second published metric, so the reproduction is checked on two numbers, not one | MixMT Subtask-1; HinGE test split | Same commits |
| BLEU | 0–100 | Secondary, **not decisive** | Reported for comparability with prior machine-translation work. Expected to understate quality here, because it gives no credit for a spelling variant | HinGE test split; gold set | Same commits |
| Code-switching penalty | chrF++ points | Secondary | Monolingual chrF++ minus code-switched chrF++ on the same English sources: the cost of producing code-switched output. Measurable only because the gold set carries both a Devanagari Hindi and a Romanized Hinglish reference | 800-item gold set only | Harness `0ac53f8`, 25 Sep; Workbook 1 §1.1, `f63f656`, 7 Oct |

The metric suite is the one on the topic slide and in Workbook 1. COMET was considered and
excluded in Workbook 1 §1.2.4: its coverage of Romanized Hinglish is uncertain, and that
uncertainty is reported as a limitation rather than relied on.

Two further measurements in Workbook 1 are not output-quality metrics, but they are fixed here
for the same reason:

- **Perplexity is reported per byte, never per token.** M3 changes the vocabulary, so
  per-token perplexity would compare M3 and M2 on different units.
- **Human evaluation** (AI-10, AI-11): 150–250 segments rated blind, with system identity
  hidden and order shuffled per item. Raters score adequacy, fluency and code-switching
  naturalness, and Krippendorff's alpha is reported per dimension. The segment-level
  correlation between chrF++ and human adequacy is reported. A weak correlation would be a
  finding about the primary metric, not a reason to replace it.

## 4.4.2 What each metric is measured on

| Evaluation set | Size | State on `main` | Used for |
|---|---|---|---|
| 800-item team-authored gold set | 800 items, three columns | `data/goldtestset/gold_set.csv` holds 0 items (298-55) | The headline comparison (AI-1) and the code-switching penalty |
| HinGE test split | 468 references over 197 unique sources | Frozen. `data/processed/manifests/hinge_split_manifest.json`, SHA-256 `6ac5d302…`, seed 42 | Interim surface for every model until the gold set exists; reported alongside the gold set afterwards |
| MixMT Subtask-1 test set | 500 sentences | Not yet in the repository | The baseline reproduction gate only |

Because the gold set is empty, the first real numbers will come from the HinGE test split. They
are labelled with that split in every table, and are never presented as the gold-set result.
If the gold set falls short of 800 items, the 500-item fallback recorded in Progress Report 2
applies.

**Multiple references.** HinGE gives up to eight human Hinglish renderings of one English
sentence. The test split's 468 records cover only 197 sources, so scoring one line per
reference would count a source with five references five times. The committed method is to
score each **source once, against all of its references**:

- chrF++ and BLEU use sacreBLEU's multi-reference mode.
- ROUGE-L and WER take the best-matching reference for each source.

`evaluation/run_eval.py` currently takes a single aligned reference file, so this is an
implementation gap, recorded with the others in 4.4.5.

**MixMT test references.** These are not in the repository. If they cannot be obtained, the
reproduction is run on the HinGE held-out human split, as the project abstract already states,
and the change of test set is stated next to the number.

## 4.4.3 Method applied to every reported number

| Rule | Detail | Requirement |
|---|---|---|
| **Three seeds** | Every model is trained and decoded at seeds **13, 42 and 1337**. Each table cell is mean ± standard deviation over the three. A single-seed number is labelled as a smoke test and is never compared | AI-3, FR-3 |
| **Bootstrap intervals** | 1,000-sample paired bootstrap over test items, giving a 95% confidence interval for each metric and for each pairwise difference between systems | AI-3 |
| **Success threshold** | An adapted model must beat M1 zero-shot by **at least 3.0 chrF++** on the gold set, with non-overlapping error bars across the three seeds | AI-1 |
| **Null result** | A difference **under 1.0 chrF++**, or one with overlapping error bars, is published as a null result, not left out | AI-2 |
| **Greedy decoding** | `do_sample=False`, so the same seed and input give identical output. No per-model decoding search | FR-8 |
| **No tuning on test** | Hyperparameters, prompts, few-shot examples and checkpoints are chosen on the dev split (468 records, `db0b17cc…`). The test split is scored once per final configuration | DR-2 |
| **Frozen splits** | Splits are byte-identical under SHA-256 for seed 42, and the leakage gate fails the run if any exact or near-duplicate source crosses a split boundary. On the real run it found 0 of each | DR-2, DR-3 |
| **Every run is logged** | One JSON per run in `runs/`, recording the seed, git commit, package versions and GPU-hours | FR-5 |
| **Normalisation is metric-only** | Spelling normalisation is applied inside the normalised-chrF++ computation only, never to training data or references, because the variance is what the project studies | — |

## 4.4.4 How each model is evaluated

Every model in section 4.1 goes through the same harness, on the same splits, with the same
seeds. What differs is which comparison each one answers.

| Model | Scored on | Compared against | Question the comparison answers |
|---|---|---|---|
| M1 zero-shot, 0-shot and 5-shot | Gold set; HinGE test | Each other | How large is the problem before any training, and how much do five in-context examples recover? |
| M2 QLoRA | Gold set; HinGE test | M1 | Does task supervision clear the +3.0 chrF++ threshold (AI-1)? |
| M3 vocabulary extension + CPT | Gold set; HinGE test; per-byte perplexity | M2 **and Control A** | Does changing the tokenizer help? It counts only if M3 beats Control A |
| M4 synthetic augmentation | Gold set; HinGE test | M2 | Does more code-switched text help, once the back-translation source has passed the contamination check (298-58)? |
| Control A: CPT without vocabulary extension | Same as M3 | M3 | Separates the vocabulary effect from the extra-training effect |
| Control B: M2 at M3's GPU-hours | Same as M2 | M3 | Separates the method from simply spending more compute |
| Reproduced baseline (Gahoi et al., 2022) | MixMT Subtask-1, ROUGE-L and WER | The published 0.617 and 0.633 | Does our harness reproduce a published number? |

**The reproduction gate.** `python evaluation/run_eval.py --hyp <outputs> --ref <MixMT refs>
--check-baseline` compares ROUGE-L with **0.617** and WER with **0.633** (Gahoi et al., 2022,
Table 2), at a tolerance of **0.01**. A pass means the harness is validated. A failure is
printed as "outside tolerance; do not interpret model results yet". The baseline is run under
two input conditions:

- **English and Hindi input**, as in the paper, for comparability.
- **English only**, as our own reference point, because our models see English only.

Two facts about the published number are fixed here, before the reproduction runs:

- The 0.617 row includes a dictionary-based transliteration step whose dictionary was never
  released. With automatic transliteration alone, the same paper reports **0.484**. The
  reproduction is reported against both rows.
- A miss is a reportable finding (Progress Report 2, Part D). If the gate fails, model results
  are reported as uninterpreted measurements, and the tolerance is not widened to make the
  gate pass.

## 4.4.5 Committed but not yet implemented

The method above is the committed method. The harness on `main` does not yet do all of it.
Each gap is listed here with its issue, rather than described as if it already worked.

| Gap in `evaluation/run_eval.py` | Effect until fixed | Issue |
|---|---|---|
| **No bootstrap resampling.** The harness reports mean ± std over seeds and computes no confidence intervals | No difference between two systems can yet be called significant | 298-59 |
| **ROUGE-L and WER are computed on normalised tokens.** `tokenise()` calls `normalise()`, so both metrics see text after the spelling rules have run | The reproduction is scored on a different tokenisation from the paper's, which by itself could move ROUGE-L by more than the 0.01 tolerance | 298-59 |
| **Regex normalisation is near-inert, and two of its rules corrupt words.** Measured against `analysis/spelling_variants.tsv`, the rules fully collapse only **3 of 72** variant groups. They target vowel lengthening, while the dominant Hinglish pattern is vowel deletion (`nhi`, `kr`, `gya`). `hy`→`y` and `hna`→`na` damage correct words | The raw-versus-normalised gap currently measures little, so no normalised figure is quoted until the lexicon-driven version lands and its collapse coverage is reported | 298-59, 298-23 |
| **chrF++ is case-sensitive.** `Main` and `main` score as different words | Capitalisation differences count as errors | 298-59 |
| **Single-reference input** | Multi-reference scoring (4.4.2) is not possible yet | To be raised as an issue at the next meeting |

298-59 is accepted only with a test that **fails against the regex version and passes against
the lexicon-driven one**, so the fix is shown to change behaviour.

## Provenance

| Claim | Source |
|---|---|
| Metric suite and primary metric | `docs/workbook1/section_1_2.md` §1.2.4, commit `cd627d0`, 7 Oct; `README.md`, Evaluation design |
| Harness and code-switching penalty | `evaluation/run_eval.py`, commits `3e9ce8a` and `0ac53f8`, 25 Sep (298-14) |
| Seeds, thresholds, null-result rule | `docs/workbook1/section_1_2.md`, AI-1 to AI-4, AI-10, AI-11, FR-3, FR-5, FR-8, DR-2, DR-3 |
| Split sizes, hashes, sources per split | `data/processed/manifests/hinge_split_manifest.json`, commit `c65faec`, 8 Oct |
| Only smoke results existed at commit time | `results/results.jsonl` and `runs/`, commit `f8cb929`; `docs/COMPUTE_BUDGET.md` |
| Baseline target, tolerance, 0.484 row | Gahoi et al. (2022), Table 2; `PUBLISHED_BASELINE` in `evaluation/run_eval.py` |
| Harness gaps | Progress Report 2, Part D, blocker 4 (`docs/progress2/part_d_risks.md`, commit `cee6805`) |
