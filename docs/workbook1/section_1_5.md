# 1.5 Literature Survey of Existing Research

Linear **298-34**. Author: Savalia, Jenil Sanjaybhai.

**Scope rule.** This survey cites only works that a team member has read, which is the list
in the References section (298-41). Works the project will depend on but that nobody has yet
read are listed at the end as a reading queue and are **not** cited. A citation a grader asks
about, and that nobody can discuss, costs more than a shorter matrix.

The works fall into five groups: the data and the baseline we compare against, the metrics we
score with, the adaptation methods we build on, the measures we use to describe code-mixing,
and the reliability and annotation work behind the human evaluation.

---

## 1.5.1 Literature matrix

| Work | Class | Contribution | Limitation | How we use it |
|---|---|---|---|---|
| Srivastava & Singh (2021), HinGE | Dataset | 1,976 English–Hindi sentence pairs with human-written Romanized Hinglish references, plus two rule-based generations (WAC, PAC) with human quality ratings | No licence stated; no train/dev/test split of its own; the downstream released splits overlap (285 of dev's 376 unique English sources also in train, per `docs/datasheet.md`); human-reference count is **4,803** in the paper but **4,799** counted off the released file — the reconciliation is open | Primary parallel supervision. Treated as CC-BY-NC-4.0-equivalent because its source pairs come from the IIT Bombay corpus. Splits are being re-derived by us; the released ones are not used |
| Gahoi et al. (2022), Gui at MixMT 2022 | Shared-task system | mBART fine-tuned on English **and** Hindi input, with Devanagari-to-Roman transliteration as post-processing; Table 2 reports ROUGE-L 0.617 and WER 0.633 on MixMT Subtask-1 | No code released, so the recipe must be re-implemented from the description; its two-input setting differs from our English-only task | The reproduced published baseline (AI-4), run twice: as published, and English-only as our comparable reference point. Its job is to prove the harness is correct, not to compete with M1–M4 |
| Popović (2017), chrF++ | Evaluation metric | Character n-gram F-score extended with word unigrams and bigrams; correlates better with human judgement than character-only chrF | Still a surface-overlap metric: two valid spellings of one word (`nahi`, `nhi`) are only partially matched | Primary metric, via `sacrebleu`. The spelling-variant weakness is exactly why we also report normalised chrF++ and treat the gap as evidence |
| Rei et al. (2020), COMET | Evaluation metric | Neural metric trained to predict human judgements from source, hypothesis and reference | Depends on the coverage of its pretrained encoder; for Romanized Hinglish that coverage is uncertain | Not used for now. Its exclusion is reported as a limitation (§1.2.4) rather than replaced silently |
| Hu et al. (2022), LoRA | Adaptation method | Freezes the pretrained weights and trains low-rank update matrices, cutting trainable parameters by orders of magnitude without added inference latency | The rank is a hyperparameter; adapters alone cannot change the tokenizer | Adapter form for M2, M4 and the second stage of M3; ranks 8 and 64 as ablations around the default 32 |
| Dettmers et al. (2023), QLoRA | Adaptation method | LoRA over a 4-bit NormalFloat base with double quantisation and paged optimizers; fine-tunes a 65B model on one 48GB GPU | Quantisation can cost quality and slows each step | The M2 recipe on one 40GB-class card; bf16-base LoRA kept as the fallback if quantisation measurably hurts |
| Das & Gambäck (2014) | Code-mixing measurement | Word-level language identification for code-mixed Indian social-media text; the Code-Mixing Index (CMI) | CMI counts the share of the dominant language and ignores how often or where the language switches | CMI in the tokenizer analysis and the data pipeline; complemented by switch-point fraction and burstiness, which capture what CMI ignores |
| Barnett et al. (2000), LIDES manual | Code-mixing measurement | Coding conventions for language-interaction data; the Multilingual Index (M-index) | Designed for transcribed speech, not for text produced by a model | M-index as a balance measure that, unlike CMI, is defined over any number of languages |
| Goh & Barabási (2008) | Statistical measure | A burstiness coefficient from −1 (regular) to +1 (bursty) over inter-event intervals | Not specific to language; meaningful only over enough runs to estimate a spread | Applied to monolingual run lengths, separating clause-level switching from word-by-word switching — which matters for how M4's synthetic data should look |
| Krippendorff (2011) | Reliability statistic | Computation of alpha for any number of raters, missing ratings and different measurement levels | A single coefficient can hide which items or raters disagree | Agreement in the human evaluation (AI-10), reported per dimension; pilot threshold α ≥ 0.67 |
| Rijhwani et al. (2020), Soft gazetteers | Low-resource NLP method | Gazetteer features built from an English knowledge base through cross-lingual entity linking improve NER in low-resource languages | Needs candidate retrieval across languages; evaluated on monolingual, not code-mixed, text | Background for named-entity handling: named-entity corruption is one category in our failure taxonomy, and our language tagger treats names with a simple rule rather than a learned NER model |

## 1.5.2 Published baseline

| Author | Year | Reported number | Exact table | Benchmark | Code obtained |
|---|---|---|---|---|---|
| Gahoi, Duneja, Padhi, Mangale, Rajput, Kamble, Sharma & Varma | 2022 | ROUGE-L **0.617**, WER **0.633** | Table 2 | WMT 2022 MixMT Subtask-1, 500-sentence test set | **No** |

The answer to "code obtained" is no, and it is tracked as a risk: the system is being
re-implemented from the paper's description. Our target is ROUGE-L within **0.01** of the
published value (`evaluation/run_eval.py --check-baseline` enforces it). If the reproduction
misses, that is reported with evidence as a finding, and no model result is interpreted
until the harness has been shown to reproduce the published number.

## 1.5.3 What the literature leaves open

Read together, these works give us a dataset (HinGE), a published system to reproduce
(Gahoi et al.), metrics for overlap (chrF++), measures for how mixed a text is (CMI, M-index,
burstiness), adapters that make the comparison affordable (LoRA, QLoRA), and a reliability
statistic for human judgement (Krippendorff's alpha). None of them measures what spelling
variation costs a tokenizer, and none separates a gain from vocabulary extension from a gain
from extra training. Those two gaps are the project's contribution: the
`spelling_variant_burden` metric, measured at 1.832 on the primary backbone
(`reports/spelling_variance.md`), and the M3-versus-control comparison. The code-mixing
measures also describe *how much* a sentence mixes languages but not *how it is spelled*,
which is why the evaluation adds the raw-versus-normalised chrF++ gap.

## 1.5.4 Reading queue — not cited

The following works bear directly on the plan but no team member has confirmed reading them.
They are excluded from the matrix and the references until someone has, and each will be
added in Workbook 2 only after it is read.

- GCM toolkit for synthetic code-mixed text — the M4 generation method
- Vocabulary-expansion work on initialising new embeddings from constituent subwords — the M3
  initialisation
- RomanSetu, on romanization and token fertility for Indic languages — the "script" explanation
  the hypothesis argues against
- GLUECoS and LinCE benchmarks — code-switching evaluation suites and the LinCE tag set used
  by the pipeline's language tagger
- The WMT 2022 MixMT shared-task overview and the University of Edinburgh's MixMT submission —
  the strongest published chrF++ reference on the same test set
