# 4.1 Model Proposals

Linear **298-66**. Written by Savalia, Jenil Sanjaybhai.

We propose **six model configurations and one reproduced baseline** for one task: generating
Romanized Hinglish from an English sentence. Four are an ablation ladder, M1 to M4, where each
step adds one ingredient and so tests one explanation for why the task is hard. Control A and
Control B are trained models in their own right, with their own adapters, three seeds and rows
in the results table; they exist because an M3 gain cannot be attributed to anything without
them. The reproduced baseline is listed separately and is **not one of the four**.

*Status, 11 November: M1 and M2 have since been trained and scored on the real corpus across
three seeds (§4.5). This section proposes; it is not revised to report those results.*

## 4.1.1 The proposals at a glance

| # | Model | Concept | Architecture and algorithm | Built in | Owner | State |
|---|---|---|---|---|---|---|
| 1 | M1 zero-shot | Prompt the backbone with no training; 0-shot and 5-shot reported separately | Unmodified backbone, greedy decoding | 298A | Waghmare | **Complete, 3 seeds** |
| 2 | M2 PEFT | Add task supervision through parameter-efficient fine-tuning | QLoRA: rank 32, alpha 64, all seven linear projections, 4-bit NF4 base, loss masked to completion | 298A | Waghmare | **Complete, 3 seeds** |
| 3 | M3 vocab extension + CPT | Change how Hinglish is tokenized, then continue pretraining | SentencePiece diff supplies new tokens; embeddings start as the mean of constituent subwords; two-stage training with replay | 298B | Savalia (prov.) | Not started |
| 4 | M4 augmented | Change the training distribution with synthetic code-switched text | Back-translation plus Equivalence-Constraint synthesis, sampled to match the natural switch-point rate; M2 recipe | 298B | Shevkar (prov.) | Input stage run; not fit to train on |
| 5 | Control A | Continued pretraining **without** vocabulary extension | M3 with the original tokenizer | 298B | Savalia (prov.) | Not started |
| 6 | Control B | M2 given M3's compute | M2 recipe trained to M3's GPU-hour total | 298B | Waghmare (prov.) | Not started |
| — | Baseline, **not one of the four** | The published MixMT Subtask-1 system, rebuilt from its description | mBART with transliteration post-processing (Gahoi et al., 2022) | 298A | Thomas Lnu | Not run |

Requirement AI-8 says the models must differ in kind, not in hyperparameters. Each row below
changes the parameters updated, the tokenizer vocabulary or the training distribution:

| Model | Parameters updated | Vocabulary | Training distribution | Question it isolates |
|---|---|---|---|---|
| M1 | None | Original | None | How large is the problem? |
| M2 | LoRA adapters | Original | HinGE train split | Is it missing task supervision? |
| M3 | Embeddings + LM head, then adapters | **Extended** | HinGE plus replay | Is it the tokenizer and orthographic variance? |
| M4 | LoRA adapters | Original | HinGE plus **synthetic** | Is it the scarcity of code-switched text? |
| Control A | Embeddings + LM head, then adapters | Original | Same as M3 | Vocabulary, or only the extra training? |
| Control B | LoRA adapters | Original | Same as M2 | Method, or only more compute? |

## 4.1.2 What all six share

**Backbone.** `Qwen/Qwen2.5-7B-Instruct` throughout, chosen in §1.4: verified against its model
card, ungated (Apache-2.0), small enough for quantised training on one 40 GB card, and the
backbone our tokenizer measurement was taken on. 7.62B parameters, 152,064-token vocabulary,
hidden size 3,584, 28 layers, untied embeddings.

**Conventions.** Seeds 13, 42 and 1337; GPU-hours logged through `RunLogger`; splits read from
the SHA-256-frozen manifest (3,738 / 468 / 468). Perplexity is compared per byte, never per
token (AI-7), because M3 changes what a token is. One system prompt across all arms.

**A null result is an accepted outcome.** Success is +3 chrF++ over M1 with non-overlapping
error bars; under 1 chrF++, or overlapping bars, is published as a null result (AI-1, AI-2).

## 4.1.3 Model details

**M1 — zero-shot and 5-shot.** The English sentence alone under a fixed system prompt asking
for Roman-script Hinglish. The 5-shot condition adds five pairs drawn only from train, via an
explicit `--examples` file (FR-7). `models/generate_zeroshot.py` renders through the chat
template, left-pads into batches of 8 (right padding produces garbage), decodes greedily at
most 128 new tokens (FR-8), and writes one line per source. *Greedy decoding has a consequence
worth stating*: with 0 shots nothing depends on the seed, so the three 0-shot outputs are
identical by construction and their standard deviation is zero. Seeds vary only the 5-shot
exemplars. M1's 0-shot error bar therefore says nothing about sampling variation, which is one
reason AI-3's bootstrap intervals matter.

**M2 — QLoRA fine-tune.** Train on real pairs with the base frozen (Hu et al., 2022; Dettmers
et al., 2023). If M2 closes the gap, the problem was missing supervision. Inputs are 3,738
references over 1,549 unique sources. A 4-bit NF4 base with double quantisation and LoRA of
rank 32, alpha 64, dropout 0.05 on **all seven linear projections** — about 80.7M trainable
parameters, 1.06% of the model. Prompt tokens are labelled -100 so loss falls on the completion
only, otherwise the model learns to reproduce the instruction; truncation is from the left at
512 tokens so the completion always survives. Up to 3 epochs, lr 2e-4, cosine, 3% warmup,
effective batch 32, gradient checkpointing, bf16 where native and fp16 otherwise. Scored by
reloading through `generate_zeroshot.py --adapter`, the same path as M1. **This recipe is held
constant**, because M3, M4 and Control B are comparable to M2 only if it does not move.

**M3 — vocabulary extension plus CPT.** The only arm that changes how `nahi`, `nhi` and `nahin`
are tokenized. A SentencePiece model is trained on the Hinglish train split and **diffed**
against the backbone vocabulary (Yamaguchi et al., 2026); the tokenizer is extended to
152,064 + K tokens and each new embedding row initialised as the **mean of its constituent
subwords**. Stage 1 updates only embeddings and LM head; stage 2 tunes LoRA adapters; both use
replay of pretraining-language text (Csaki et al., 2023). Fertility and spelling-variant burden
are re-measured on the extended tokenizer, which is the direct test that the extension did what
it was meant to (AI-5, AI-6).

*Three changes proposed from further reading, as Team Meeting 1 asked.* **K should be chosen by
measurement over a wider range**: Yamaguchi et al. test up to 5K and recommend 500–1K for
translation, warning that a larger vocabulary underfits in low-resource settings; our train
split is about one eighth of their corpus size and 8,000 tokens would equal 61% of the 13,204
Hinglish word types in the whole corpus, so many new tokens would see few updates. We propose
sweeping K over {500, 1K, 3K, 5K, 8K} at the tokenizer level, which needs no GPU, and fixing K
on validation before any GPU time. **Replay is below the tested range**: Csaki et al. compare
0%, 25% and 50% and find no significant difference between 25% and 50%, so our 10–20% is below
their lowest non-zero mix; we propose starting at 20%. **The continued-pretraining corpus is
not yet named** beyond the HinGE train split, which is the largest open question in the arm and
is carried in the gap register. Align initialisation gives slightly lower perplexity than Mean
in most languages; we keep Mean as simpler to verify and name Align as the fallback.

**M4 — augmented with synthetic code-switched text.** Pratapa et al. (2018) found that
theory-based synthetic data reduced perplexity while randomly generated code-mixed data did
not, so *how* text is sampled matters as much as how it is generated. Real HinGE pairs plus
back-translated pairs (Sennrich et al., 2016) and sentences licensed by the Equivalence
Constraint, under which a switch may occur only where the two word orders agree (Poplack,
1980), from Samanantar (Ramesh et al., 2022). The M2 recipe is unchanged so any difference comes
from the distribution. The contamination check runs first (298-58): HinGE's English comes from
the IIT Bombay corpus, which is part of Samanantar, and the check found one shard containing at
least 13.7% of HinGE's test sources, removing the 4 matching pairs. Hindi is romanised with a
romaniser checked against held-out Dakshina (Roark et al., 2020). Alignment uses IBM Model 1,
cut into maximal monotonic blocks, each realised in one language, dropping the two monolingual
realisations. Realisations are selected to match HinGE's switch-point fraction of **0.2398**
rather than sampled uniformly, which would produce far more switching than people write.

*Stated precisely*: this applies the Equivalence Constraint to alignments, not parse trees. It
approximates the constraint and is **not GCM toolkit output** (Rizvi et al., 2021); whether M4
moves to GCM is a 298B decision. On 9 November the pipeline produced 28,559 sentences from a
29,996-pair contamination-checked slice at SPF 0.2398, on target. Its own status note says the
output is not yet fit to train on.

**Control A** removes M3's new vocabulary and keeps the extra training: M3's stages with the
same data, replay and step counts, on the **original tokenizer**. If it matches M3, the gain
came from training, not vocabulary. **Control B** holds the method fixed and matches the budget
(AI-9): the M2 recipe trained until its logged GPU-hours equal M3's total for the same seed.
**Read together, an M3 gain is attributed to the vocabulary only if M3 beats both.** M3 above
Control A but not Control B means the method is no better than spending the same compute on M2.

**Reproduced baseline — Gahoi et al. (2022).** An mBART system from WMT 2022 MixMT Subtask-1,
reporting **ROUGE-L 0.617 and WER 0.633** on 500 sentences. Its job is to show our harness is
correct, not to compete: until the harness reproduces a published number, no model result can
be interpreted. `run_eval.py --check-baseline` enforces a 0.01 ROUGE-L tolerance. The authors
released no code and the checkpoint is unconfirmed, so the recipe is rebuilt from the paper
(298-52). The 0.617 also depends on a dictionary that was never released; with automatic
transliteration alone the paper reports **0.484**.

## 4.1.4 The innovation claim

**The gap in prior work.** Tokenizer cost in Indic languages is usually discussed as a cost of
*script*: RomanSetu reports romanized text reducing fertility two- to four-fold against native
script (Husain et al., 2024). Hinglish is **already written in Roman script**, so that remedy
has been applied and script cannot be what remains. Our claim is that what remains is
**orthographic variance**: `nahi`, `nhi` and `nahin` are one word the tokenizer treats as three.

**The metric this project defines.** `spelling_variant_burden` takes each group of known
spellings of one word, computes mean tokens per spelling, and averages across groups. The floor
is 1.0. On Qwen2.5-7B-Instruct, over 72 groups and 227 surface forms, it measures **1.832**
(1.863 per form). It is a property of tokenizer and lexicon, so it needs no corpus, stays
comparable across backbones, and can be re-measured after M3. Re-run from scratch on 7 November
and reproduced exactly.

**RomanSetu's factor, now measured on our own corpus.** The argument above depends on
romanization's benefit already having been taken — that was a citation and is now a
measurement. Across the four AI-6 slices (10 November), Devanagari Hindi costs **4.636 tokens
per word at 1.2% vocabulary coverage** and the same content in Roman script costs **1.909 at
21.9%** — a **2.4× reduction**, inside Husain et al.'s two-to-four-fold range. Hinglish is
cheaper still at **1.636**, because it carries English words the tokenizer knows.

The ordering is `Devanagari 4.636 > Romanised Hindi 1.909 > Hinglish 1.636 > English 1.247`.
Script choice dominates, romanization captures that gain, and Hinglish is already romanized.
What is left is the 1.636-against-1.247 residue on text that is *already* romanized, and a
burden of 1.832 is the account this project gives of it. M3 acts on that residue; Control A
isolates it. Neither the metric nor the arm is novel alone — the contribution is measuring what
spelling costs and then separating a vocabulary gain from a compute gain, which §1.5.3 found no
surveyed work doing.

*One honest limit*: the Romanised-Hindi slice is a 30-line team fixture, because no corpus here
has that column. The 2.4× figure indicates direction and magnitude, not a corpus-grade
estimate; closing it needs Dakshina (298-76).

**What the evidence supports today.** The corpus behind each number decides how it can be used.

| Evidence | Value | Measured on | Status |
|---|---|---|---|
| Spelling-variant burden | 1.832 against a floor of 1.0 | Tokenizer + lexicon, no corpus | Reportable; reproduced 7 Nov |
| Cost per occurrence, usage-weighted | 1.395 over the top 15 groups (2,789 occurrences, 73% of lexicon occurrences) | **Real HinGE** | Reportable; partial coverage |
| Spelling dispersion | 28 of 72 groups have 2+ forms; 12.93% of 3,812 occurrences non-canonical | **Real HinGE** | Reportable, at 68.2% tagger coverage |
| Vocabulary size | 13,204 Hinglish types against 6,780 English | **Real HinGE** | Reportable |
| Fertility, English → Hinglish | 1.247 → 1.636 | **Real HinGE** | **Reportable**; re-measured 10 Nov |
| Fertility, Devanagari Hindi | **4.636** at 1.2% coverage | **Real HinGE** | **Reportable**; the fourth AI-6 slice |
| Coverage, English → Hinglish | 98.5% → 52.6% | **Synthetic**, 67 and 78 word types | Illustrative only |

The 7 October coverage figures are not real-corpus measurements and were committed before the
corpus was ingested. On a second synthetic slice the fertility direction holds but the coverage
gap disappears, so **the 98.5%-against-52.6% contrast must not be read as a finding**.

**What the real-corpus number adds.** Burden counts every listed spelling once, however rarely
written. Weighted by real usage the same tokenizer pays **1.395** tokens per occurrence against
a burden of 1.722 for those same 15 groups, because writers favour cheap spellings: `hai`
occurs 934 times at 1.03 tokens. Cost concentrates: `gaya`, `kuch`, `kahan`, `karna`, `koi` and
`diya` cost two or more per occurrence, while `kar`, `tha`, `tum`, `hum` and `na` already cost
one. This narrows the claim and sharpens M3's target — spelling variance does cost tokens on
real text, but less than the lexicon figure suggests, and the available saving sits in a limited
set of words. **It is therefore a live possibility that M3 buys little**, which is one of the
ways the preferred model can lose (§4.3). All of this shows the variants exist and what they
cost; it does not show that removing them improves generation. That is the M2-versus-M3
comparison, and until it runs the claim remains a hypothesis under test.

**Provenance.** Backbone facts from `docs/workbook1/section_1_4.md` and the model card;
recipes from `models/generate_zeroshot.py` and `models/train_qlora.py`; requirements from
`docs/workbook1/section_1_2.md`; M4's run from `reports/codemix/` and
`reports/contamination/README.md`; burden and per-occurrence cost from
`reports/variant_cost_hinge.json` and `reports/fertility.csv`; baseline figures from
`docs/workbook1/section_1_5.md`.
