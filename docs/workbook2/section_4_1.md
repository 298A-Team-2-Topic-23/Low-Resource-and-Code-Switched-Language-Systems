# 4.1 Model Proposals

Linear **298-66**. Written by Savalia, Jenil Sanjaybhai.

We propose **six model configurations and one reproduced baseline** for one task: generating
Romanized Hinglish from an English sentence. Four are the models of an ablation ladder, M1 to
M4, where each step adds one ingredient and so tests one explanation for why the task is hard.
The other two, Control A and Control B, are trained models in their own right. Each has its own
adapters, three seeds and a row in the results table, and they exist because an M3 gain cannot
be attributed to anything without them. The reproduced baseline is listed separately and is
**not one of the four models**.

This section proposes; it does not report results. No model has been trained or scored on the
real corpus. The runs under `runs/` are single-seed smoke tests on synthetic data with a 0.5B
stand-in model, and `docs/COMPUTE_BUDGET.md` records that none of them is a reportable result.

## 4.1.1 The proposals at a glance

| # | Model | Concept | Architecture and algorithm | Built in | Owner | State on `main` |
|---|---|---|---|---|---|---|
| 1 | M1 zero-shot | Prompt the instruction-tuned backbone with no training. Reported as 0-shot and 5-shot | Unmodified backbone, greedy decoding | 298A | Waghmare | Script merged; smoke-tested only |
| 2 | M2 PEFT | Add task supervision through parameter-efficient fine-tuning | QLoRA: rank 32, alpha 64, all seven linear projections, 4-bit NF4 base, loss masked to the completion | 298A | Waghmare | Trainer merged; smoke-tested only |
| 3 | M3 vocabulary extension + CPT | Change how Hinglish is tokenized, then continue pretraining | SentencePiece diff supplies new tokens; embeddings start as the mean of constituent subwords; two-stage training with replay | 298B | Savalia (provisional) | Not started |
| 4 | M4 augmented | Change the training distribution with synthetic code-switched text | Back-translation plus Equivalence-Constraint synthesis, sampled to match the natural switch-point distribution; M2 recipe | 298B | Shevkar (provisional) | Input stage run on a 30,000-pair real slice; not yet fit to train on |
| 5 | Control A | Continued pretraining **without** vocabulary extension | M3 with the original tokenizer | 298B | Savalia (provisional) | Not started |
| 6 | Control B | M2 given M3's compute | M2 recipe trained to M3's exact GPU-hour total | 298B | Waghmare (provisional) | Not started |
| — | Reproduced baseline, **not one of the four** | The published MixMT Subtask-1 system, rebuilt from its description | mBART with transliteration post-processing (Gahoi et al., 2022) | 298A | Thomas Lnu | Not run; no code exists |

Provisional owners are to be confirmed at the next team meeting.

Requirement AI-8 says the models must differ in kind rather than in hyperparameters. The table
below is the check on that: each row changes the parameters updated, the tokenizer vocabulary
or the training distribution, and each states what it rules out.

| Model | Parameters updated | Tokenizer vocabulary | Training distribution | Question it isolates |
|---|---|---|---|---|
| M1 | None | Original | None | How large is the problem? |
| M2 | LoRA adapters | Original | HinGE train split | Is it simply missing task supervision? |
| M3 | Embeddings and LM head, then adapters | **Extended** | HinGE train split plus replay | Is it the tokenizer and orthographic variance? |
| M4 | LoRA adapters | Original | HinGE plus **synthetic** text | Is it the scarcity of code-switched text? |
| Control A | Embeddings and LM head, then adapters | Original | Same as M3 | Vocabulary, or only the extra training? |
| Control B | LoRA adapters | Original | Same as M2 | Method, or only more compute? |

## 4.1.2 What all six share

**Backbone.** Every configuration uses `Qwen/Qwen2.5-7B-Instruct`, chosen in section 1.4 because
it is verified against its model card, ungated (Apache-2.0), small enough for quantised training
on one 40 GB card, and the backbone our tokenizer measurement was taken on. It has 7.62B
parameters (section 1.4), and its published `config.json` gives a 152,064-token vocabulary, hidden
size 3,584, 28 decoder layers and untied input and output embeddings.

**Conventions.** Every configuration runs under seeds 13, 42 and 1337, logs GPU-hours through
`RunLogger` in `common/repro.py`, and reads the splits frozen under SHA-256 in
`data/processed/manifests/hinge_split_manifest.json`: 3,738 train, 468 validation and 468 test.
Perplexity is compared per byte and never per token (AI-7), because M3 changes what a token is.
All arms use one system prompt, versioned in `models/generate_zeroshot.py` and
`models/train_qlora.py`.

**A null result is an accepted outcome.** Success is +3 chrF++ over M1 with non-overlapping error
bars; a difference under 1 chrF++, or overlapping bars, is published as a null result (AI-1, AI-2).

## 4.1.3 Model details

### Model 1: zero-shot and 5-shot backbone

**Concept.** Ask the backbone for the translation and record what it produces. M1 adds nothing,
so every later gain is measured against it.

**Features.** The input is the English sentence alone, under a fixed system prompt asking for
Roman-script Hinglish with no Devanagari. The 5-shot condition adds five example pairs drawn only
from the train split, through an explicit `--examples` file (FR-7). The two conditions are
reported separately because the success criterion has to be unambiguous about which one it means.

**Architecture.** The unmodified backbone, with no adapter and no change to the vocabulary.

**Algorithm.** (`models/generate_zeroshot.py`)

1. Render system prompt, optional examples and source through the model's chat template.
2. Left-pad into batches of 8, since batched generation with right padding produces garbage.
3. Decode greedily with `do_sample=False` and at most 128 new tokens (FR-8).
4. Write one line per source and score with `evaluation/run_eval.py`.

Greedy decoding has a consequence worth stating. With 0 shots nothing in the run depends on the
seed, so the three 0-shot outputs should be identical and their standard deviation zero by
construction. The seeds vary only the five examples drawn for the 5-shot condition. M1's 0-shot
error bar therefore says nothing about sampling variation, which is one reason the bootstrap
intervals required by AI-3 matter.

### Model 2: QLoRA fine-tune

**Concept.** Train on real code-switched pairs through parameter-efficient fine-tuning, leaving
the base weights frozen (Hu et al., 2022; Dettmers et al., 2023). If M2 closes the gap, the
problem was missing task supervision.

**Features.** English source and human Hinglish reference from the train split: 3,738 references
over 1,549 unique sources. The pipeline's TSV layout is `id, group, english, hindi, hinglish`, so
training passes `--src-col 2 --tgt-col 4`.

**Architecture.** A 4-bit NF4 base with double quantisation and LoRA adapters of rank 32, alpha 64
and dropout 0.05 on **all seven linear projections** of each layer: `q_proj`, `k_proj`, `v_proj`,
`o_proj`, `gate_proj`, `up_proj` and `down_proj`. That is about 80.7M trainable parameters, 1.06%
of the model (our arithmetic from `config.json`, to be confirmed by the first run record).

**Algorithm.** (`models/train_qlora.py`)

1. Render the prompt through the chat template and append the target and an end-of-sequence token.
2. Label every prompt token -100, so loss is taken on the completion only. Otherwise the model
   learns to reproduce the instruction.
3. Truncate from the left at 512 tokens, so the completion always survives.
4. Train for up to 3 epochs at learning rate 2e-4 with a cosine schedule and 3% warmup, batch 4
   with 8 accumulation steps for an effective batch of 32, and gradient checkpointing. Use bf16
   where the card supports it natively and fp16 otherwise.
5. Reload the adapter through `generate_zeroshot.py --adapter`, so M2 is scored through the same
   path as M1.

This recipe is held constant, because M3, M4 and Control B are only comparable to M2 if it does
not move.

### Model 3: vocabulary extension plus continued pretraining

**Concept.** M3 is the only arm that changes how `nahi`, `nhi` and `nahin` are tokenized. It adds
Hinglish subwords to the tokenizer and continues pretraining so the model learns them. Section
4.1.4 explains why this is the arm that acts on our measurement.

**Features.** Romanized Hinglish text from the train split only, so nothing from validation or
test reaches the vocabulary, plus replayed text in the backbone's pretraining language to limit
forgetting.

**Architecture.** The backbone with an extended vocabulary of 152,064 + K tokens. The input
embedding and LM head are separate matrices of about 545M parameters each, and K new tokens add
K × 3,584 parameters to each: 10.8M at K = 3,000 and 28.7M at K = 8,000 (our arithmetic). After
training, the LoRA adapters follow the M2 form.

**Algorithm.**

1. Train a SentencePiece model on the Hinglish train split and take the **diff** against the
   backbone vocabulary, keeping the most frequent pieces not already present. This follows the
   vocabulary-construction step of Yamaguchi et al. (2026).
2. Extend the tokenizer and resize the embedding and LM-head matrices.
3. Initialise each new row as the **mean of the embeddings of its constituent subwords** under the
   original tokenizer (Yamaguchi et al., 2026, "Mean").
4. **Stage 1:** update only the embeddings and LM head.
5. **Stage 2:** tune the LoRA adapters, the two-stage procedure compared by Yamaguchi et al. (2026).
   Both stages use 10–20% replay of pretraining-language text, the data mixing studied by Csaki et
   al. (2023).
6. Re-measure fertility and spelling-variant burden on the extended tokenizer, which is the direct
   test that the extension did what it was meant to (AI-5, AI-6).

**Proposed changes from further reading.** At Team Meeting 1 the instructor and ISA asked the team
to do more research and implement what it finds. Reading the vocabulary-expansion literature for
this section raised three points against the recipe as first written, and we propose acting on them.

- **K should be chosen by measurement, over a wider range.** The plan names 3,000 to 8,000 added
  tokens. Yamaguchi et al. (2026), working with about 30K sentences per language, test up to 5K and
  recommend 500 to 1K as a starting point for translation, warning that a larger vocabulary risks
  underfitting in low-resource settings. Csaki et al. (2023) replace about 5,000 tokens and report
  diminishing returns beyond that, but on a 96 GB Hungarian corpus. Our train split has 3,738 references, about one eighth of
  Yamaguchi et al.'s size, and 8,000 tokens would equal 61% of the 13,204 Hinglish word types in
  the whole corpus (`reports/data_statistics.json`). Many new tokens would see few training
  updates. We propose sweeping K over {500, 1K, 3K, 5K, 8K} at the tokenizer level, which needs no
  GPU, and fixing K on the validation split before any GPU time is spent.
- **Replay is below the range tested.** Csaki et al. (2023) compare 0%, 25% and 50% English: mixing
  mitigates forgetting, and they find no significant difference between 25% and 50%. Our 10–20% is
  below the lowest non-zero mix they tested, so we propose starting at 20% and treating anything
  lower as unvalidated.
- **The continued-pretraining corpus is not yet named.** No committed document specifies text for
  this stage beyond the HinGE train split, and continued pretraining normally assumes much more.
  This is the largest open question in the arm, and it is carried in the gap register.

Yamaguchi et al. (2026) also report that Align initialisation gives the lowest perplexity in most
languages, with small gaps from Mean. We keep Mean, which is simpler to implement and verify, and
name Align as the alternative if the new tokens train poorly.

### Model 4: augmented with synthetic code-switched text

**Concept.** If the problem is that code-switched text is scarce, more of it should help, provided
it resembles what people write. Pratapa et al. (2018) found that theory-based synthetic data,
sampled into training, reduced a language model's perplexity while randomly generated code-mixed
data did not. So how the text is sampled matters as much as how it is generated.

**Features.** Real HinGE pairs plus two synthetic sources: back-translated pairs (Sennrich et al.,
2016) and code-mixed sentences licensed by the Equivalence Constraint, under which a switch may
occur only where the word orders of the two languages agree (Poplack, 1980). Samanantar is the
parallel source (Ramesh et al., 2022; `docs/datasheet.md`).

**Architecture.** The M2 architecture and recipe, unchanged, so that any difference comes from the
training distribution. Generation additionally needs a reverse Hinglish-to-English model.

**Algorithm.**

1. Run the contamination check first (298-58). HinGE's English comes from the IIT Bombay corpus
   (Kunchukuttan et al., 2018), which is part of Samanantar, so test sources could leak into
   synthetic training data. The check found that one Samanantar shard contains at least 13.7% of
   HinGE's test sources, and removed the 4 matching pairs from the slice used
   (`reports/contamination/README.md`).
2. Romanise the Hindi side, since the generator refuses Devanagari input, with a romaniser
   checked against held-out Dakshina romanisations (Roark et al., 2020;
   `reports/codemix/transliteration_spotcheck.json`). Dakshina's share-alike licence still needs
   a decision before anything derived from it is released (`docs/datasheet.md`).
3. Align with IBM Model 1, cut the alignment into maximal monotonic blocks, and realise each block
   in one language or the other, dropping the two monolingual realisations
   (`src/lrcs/data/codemix.py`).
4. Select realisations so the batch matches HinGE's switch-point fraction of 0.2398 rather than
   sampling uniformly, which would produce far more switching than people write.
5. Train with the M2 recipe on the combined data.

**Stated precisely.** Step 3 applies the Equivalence Constraint to alignments rather than parse
trees. It approximates the constraint and is **not output of the GCM toolkit** (Rizvi et al., 2021),
which `docs/datasheet.md` names as the intended generator. Whether M4 moves to GCM itself is a 298B
decision. On 9 November the pipeline ran on a 29,996-pair contamination-checked Samanantar slice
and produced 28,559 sentences at a switch-point fraction of 0.2398, on target (298-76,
`reports/codemix/samanantar_stats.json`). Its own status note says the output is not yet fit to
train on, and no model has been trained on it (`reports/codemix/README.md`).

### Control A: continued pretraining without vocabulary extension

**Concept and purpose.** M3 differs from M2 in two ways: it has a new vocabulary and it receives
more training. Control A removes the first and keeps the second. If Control A matches M3, the gain
came from the extra training and not from the vocabulary.

**Architecture and algorithm.** M3's steps 4 and 5 with the same data, replay and step counts, and
the **original tokenizer**. Stage 1 updates the existing embedding and LM-head rows.

### Control B: M2 at M3's GPU-hours

**Concept and purpose.** Control B asks whether "M3 wins" only means "M3 received more compute". It
holds the method fixed and matches the budget (AI-9).

**Architecture and algorithm.** The M2 recipe, unchanged, trained until its logged GPU-hours equal
M3's total for the same seed. Section 2.3 charges this as the increment beyond M2's own run.

**Reading the two together.** An M3 gain is attributed to the vocabulary only if M3 beats **both**
controls. M3 above Control A but not Control B means the method is no better than spending the same
compute on M2.

### Reproduced baseline: Gahoi et al. (2022), not one of the four

**Concept and purpose.** An mBART system from WMT 2022 MixMT Subtask-1. Table 2 reports **ROUGE-L
0.617 and WER 0.633** on 500 sentences. Its job is to show that our evaluation harness is correct,
not to compete with M1 to M4: until the harness reproduces a published number, no model result can
be interpreted. `evaluation/run_eval.py --check-baseline` enforces a 0.01 ROUGE-L tolerance.

**Architecture and algorithm.** mBART fine-tuned on English and Hindi input, with Devanagari-to-Roman
transliteration afterwards, run twice: as published, and English-only as our comparable reference
point. The authors released no code and the exact checkpoint is unconfirmed, so the recipe is being
rebuilt from the paper under 298-52. The published 0.617 also depends on a dictionary step whose
dictionary was never released; with automatic transliteration alone the paper reports 0.484
(`docs/progress2/part_d_risks.md`).

## 4.1.4 The innovation claim

**The gap in prior work.** Tokenizer cost in Indic languages is usually discussed as a cost of
script: RomanSetu reports that romanized text reduces token fertility by a factor of two to four
against native script (Husain et al., 2024). Hinglish is **already written in Roman script**, so that
remedy has already been applied, and script cannot be what remains. Our claim is that what remains
is **orthographic variance**: `nahi`, `nhi` and `nahin` are one word that a tokenizer treats as
unrelated entries.

**The metric this project defines.** `spelling_variant_burden` takes each group of known spellings
of one word, computes the mean tokens per spelling, and averages across groups. The floor is 1.0,
where every spelling costs one token. On `Qwen/Qwen2.5-7B-Instruct`, over 72 groups and 227 surface
forms (`analysis/spelling_variants.tsv`), it measures **1.832**; averaged per form instead of per
group it is 1.863 (`reports/variant_cost_hinge.json`). It is a property of tokenizer and lexicon, so
it needs no corpus, stays comparable across backbones, and can be measured again after M3. We
re-ran it from scratch on 7 November and it reproduced exactly.

**The design that tests it.** M3 acts on the measurement and Control A isolates it. Neither the
metric nor the arm is innovative alone: the contribution is measuring what spelling costs and then
separating a gain from vocabulary from a gain from extra training, which section 1.5.3 found no
surveyed work doing.

**What the evidence supports today.** The evidence is uneven, and the corpus behind each number
decides how it can be used.

| Evidence | Value | Measured on | File | Status |
|---|---|---|---|---|
| Spelling-variant burden | 1.832 against a floor of 1.0 | Tokenizer and lexicon; no corpus | `reports/fertility.variants.csv` | Reportable; reproduced 7 Nov |
| Token cost per occurrence, weighted by what writers actually use | 1.395 over the top 15 groups: 2,789 occurrences, 73% of lexicon occurrences | **Real HinGE** | `reports/variant_cost_hinge.json` | Reportable; partial coverage |
| Spelling dispersion | 28 of 72 groups have 2+ forms; 12.93% of 3,812 occurrences are non-canonical | **Real HinGE** | `reports/data_statistics.json` | Reportable, at 68.2% tagger coverage |
| Vocabulary size | 13,204 Hinglish types against 6,780 English, on similar token counts | **Real HinGE** | `reports/data_statistics.json` | Reportable; code-mixing also contributes |
| Fertility, English to Hinglish | 1.024 to 1.501 | **Synthetic**, 1,091 pairs | `reports/fertility.csv` | Illustrative only |
| Coverage, English to Hinglish | 98.5% to 52.6% | **Synthetic**, 67 and 78 word types | `reports/fertility.csv` | Illustrative only |
| The same two on another synthetic slice | Fertility 1.150 to 1.660; coverage 54.6% to 53.0% | **Synthetic**, 801 lines | `reports/fertility_recheck_synthetic.csv` | Shows these figures move with the slice |

The fertility and coverage figures are the ones most often quoted for this project, and they are not
real-corpus measurements. `reports/spelling_variance.md` says so, and they were committed on
7 October before the real corpus was ingested. On a second synthetic slice the direction of the
fertility gap holds, but the coverage gap disappears, so **the 98.5% against 52.6% contrast must not
be read as a finding**. Re-measuring both on real HinGE needs one command and no GPU, and it is in the
gap register.

**What the real-corpus number adds.** Burden counts every listed spelling once, however rarely it is
written. Weighted by real usage, the same tokenizer pays 1.395 tokens per occurrence over the groups
we can weight, against a burden of 1.722 for those same 15 groups, because writers favour cheap
spellings: `hai` occurs 934 times and averages 1.03 tokens. Cost concentrates in particular words.
`gaya`, `kuch`, `kahan`, `karna`, `koi` and `diya` cost two or more tokens per occurrence in practice,
while `kar`, `tha`, `tum`, `hum` and `na` already cost one.

This narrows the claim and gives M3 a sharper target. Spelling variance does cost tokens on real text,
but less than the lexicon figure alone suggests, and the saving available to M3 sits in a limited set
of words. It is therefore a live possibility that M3 buys little, which is one of the ways the
preferred model can lose (section 4.3). All of this shows that the variants exist and what they cost. It does not
show that removing them improves generation. That is the M2-versus-M3 comparison, and until it runs
the claim remains a hypothesis under test.

## Provenance

| Claim | Source |
|---|---|
| Backbone facts | `docs/workbook1/section_1_4.md`; `config.json` on the model card |
| M1 and M2 recipes | `models/generate_zeroshot.py`, `models/train_qlora.py` |
| Requirements cited (AI-, FR-) | `docs/workbook1/section_1_2.md` |
| Compute charging for Control B | `docs/workbook1/section_2_3_2_4.md` |
| M4 input stage, contamination and the real-corpus run | `src/lrcs/data/codemix.py`, `reports/codemix/`, `reports/contamination/README.md` |
| Burden, per-occurrence cost, recheck | `analysis/variant_cost_hinge.py`, `reports/variant_cost_hinge.json`, `reports/fertility_recheck_synthetic.csv` |
| Baseline figures | `docs/workbook1/section_1_5.md`, `docs/progress2/part_d_risks.md` |
