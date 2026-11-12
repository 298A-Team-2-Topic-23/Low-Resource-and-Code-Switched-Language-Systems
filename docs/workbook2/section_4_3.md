# 4.3 Model Comparison and Justification

Linear **298-69**. Written by Shevkar, Yash.

This section compares the six configurations and the reproduced baseline proposed in section 4.1,
in the same order, and justifies each one. Each model is justified by **what it rules out**, not by
how well we expect it to score. The project asks why quality drops on Romanized Hinglish, and there
are three competing explanations: missing task data, the tokenizer, and scarce code-switched text.
A model earns its place by isolating one of them. No model has been scored on the real corpus yet,
so every strength and limitation below is a design property, not a measured result.

## 4.3.1 Statistics, classical machine learning and deep learning

The rubric asks for statistical, machine-learning and deep-learning approaches. **All six
configurations and the baseline are deep learning.** That is a decision, and the reasons follow.
Statistical and classical methods are still used in the project, as components where they fit
better than a neural model, but not as the generator.

| Family | Candidate considered | What it could do here | Decision and reason |
|---|---|---|---|
| Statistical: rules and dictionaries | Word- or phrase-aligned substitution of English into Hindi, then transliteration. HinGE's own WAC and PAC generators work this way (Srivastava & Singh, 2021) | Produce Hinglish without any training | **Rejected as a model.** It has no subword tokenizer, so it cannot test the project's claim, which is about how a pretrained tokenizer handles spelling. HinGE's authors also report that its outputs carry deliberate noise and that at least half of sampled outputs were judged correct, which makes it a data source, not a competitor |
| Statistical: alignment | IBM Model 1 word alignment by EM | Find where English and Hindi word orders agree | **Used inside M4**, in `src/lrcs/data/codemix.py`, to locate switch points that satisfy the Equivalence Constraint. It needs no GPU, is deterministic and is easy to inspect |
| Statistical: inference | Bootstrap resampling over seeds and test items | Decide whether a difference is real | **Used in evaluation** (section 4.4, AI-3). Without it no comparison in this section can be called significant |
| Classical machine learning | Phrase-based or count-based translation, or nearest-neighbour retrieval of a training reference | Translate from 3,738 training references | **Rejected.** A count-based translation model learns from co-occurrence, and 3,738 references over 1,549 sources is far too few to cover open-domain English. Retrieval cannot work by construction: the leakage gate guarantees that no test source, or near-duplicate of one, appears in train (section 3.5), so the nearest training reference is always a different sentence. Neither has a subword tokenizer to measure |
| Classical machine learning | Word-level language identification and spelling normalisation | Tag or normalise tokens | **Used where it serves measurement**: a rule-based LinCE-style tagger for code-mixing statistics (section 3.3) and lexicon normalisation for the secondary metric (section 4.4). Neither generates text |
| Deep learning: encoder–decoder | mBART | Sequence-to-sequence translation | **Used only as the reproduced baseline** (Gahoi et al., 2022), to prove the harness reproduces a published number |
| Deep learning: decoder LLM | `Qwen/Qwen2.5-7B-Instruct` with prompting, adapters and vocabulary change | Generate Hinglish from English | **Adopted for all six configurations.** It is the only backbone whose tokenizer cost was measured (section 1.4), and pretraining supplies the broad English and Hindi knowledge that 3,738 references cannot |

The deciding argument is about method more than accuracy. The claim under test concerns how a
**pretrained subword tokenizer** treats spelling variants. Testing it requires holding the model
family fixed and changing one ingredient at a time. Comparing a rule system against a neural model
would change everything at once, and the comparison would answer nothing about the hypothesis.

## 4.3.2 The models compared

| Model | Targeted problem | Features and approach | Strengths | Limitations | Justification: what it rules out |
|---|---|---|---|---|---|
| **M1** zero-shot and 5-shot | How large is the gap before any adaptation? | Unmodified backbone, fixed system prompt, greedy decoding, 128 new tokens; 5-shot examples drawn from train only | No training, about 2 GPU-hours for three seeds; the reference point every gain is measured from | 0-shot is deterministic, so its three-seed spread is zero by construction; the smoke run produced Devanagari in 13 of 48 outputs, which the prompt alone may not prevent | **Sizes the problem.** If M1 is already close to the references, there is little gap to explain |
| **M2** QLoRA | Is the gap simply missing task supervision? | Rank-32 LoRA on all seven linear projections over a 4-bit NF4 base; loss on the completion only; HinGE train split (Hu et al., 2022; Dettmers et al., 2023) | Cheap (about 25 GPU-hours for three seeds); fits one card; the trainer is merged and tested; its recipe is held fixed so later arms are comparable | Cannot change tokenization, so `nahi`, `nhi` and `nahin` remain unrelated entries; only 3,738 references to learn from | **Rules out "just add task data".** If M2 closes the gap to the target, the tokenizer and distribution explanations are unnecessary |
| **M3** vocabulary extension + CPT | Is it the tokenizer and orthographic variance? | Hinglish SentencePiece diff adds K tokens, initialised as the mean of their subwords; embeddings and LM head trained first, then adapters, with replay (Yamaguchi et al., 2026; Csaki et al., 2023) | The **only** arm that acts on the measured cost: spelling-variant burden 1.832 against a floor of 1.0; fewer tokens per sentence also makes inference cheaper if fertility falls | Most expensive arm (about 45 GPU-hours); new embeddings must be learned from a small corpus; continued pretraining risks forgetting; no continued-pretraining corpus is named yet beyond the train split | **Tests the project's hypothesis.** Its gain counts as evidence only if it also beats both controls |
| **M4** augmented | Is it the scarcity of code-switched text? | M2 recipe on HinGE plus synthetic pairs: back-translation (Sennrich et al., 2016) and Equivalence-Constraint code-mixing (Poplack, 1980) sampled to HinGE's switch-point fraction of 0.2398 (Pratapa et al., 2018) | Attacks data scarcity without changing the model; generator is built with 28 tests | Synthetic text can carry its own errors, including transliteration errors from the Romanisation step; it must be contamination-checked against test before generation (298-58, 298-76) | **Rules out data scarcity** as the cause, or confirms it. It changes the training distribution and nothing else |
| **Control A** CPT without extension | Is an M3 gain from the vocabulary, or only from extra training? | M3's two stages with the same data, replay and steps, and the **original** tokenizer | Gives M3's result its meaning | About 20 GPU-hours on top of M3, for no deployable model of its own | **Separates vocabulary from extra pretraining.** If A matches M3, the tokenizer story is wrong |
| **Control B** M2 at M3's GPU-hours | Is an M3 gain only more compute? | The unchanged M2 recipe trained until its logged GPU-hours equal M3's | Cheapest way to test the compute explanation; uses an already working trainer | About 25 GPU-hours; more epochs on 3,738 references may overfit, which would itself be informative | **Separates method from compute.** M3 above A but not above B means the method is no better than spending the same hours on M2 |
| **Baseline**, reproduced, *not one of the four* | Does our evaluation harness reproduce a published number? | mBART fine-tuned on English and Hindi input with transliteration afterwards, rebuilt from the paper; run as published and English-only (Gahoi et al., 2022) | A published figure to check the harness against | No code released. The headline 0.617 ROUGE-L depends on an unreleased dictionary, so only the paper's rows 1 and 2 (0.391 and 0.484) can be rebuilt (`docs/baseline/gahoi_reproduction.md`); it uses two input languages where our task uses one | **Rules out a broken harness.** No model result is interpreted until the reproduction lands within tolerance of a row we can rebuild |

The compute figures are the reservations in `docs/COMPUTE_BUDGET.md`. They summed to 177 GPU-hours
against the 145-hour cap in section 2.3. Under 298-72 no arm was dropped: M3 trains one K on the
GPU (45 to 36 hours) and Control B continues each M2 seed rather than retraining it (25 to 11), for
154 hours against a cap made explicit as 145 for training plus 20 for inference. Both controls, and
so the attribution argument of this section, are intact. The change is recorded in the
carry-forward table.

## 4.3.3 What each comparison isolates

The ladder is read as a set of pairwise comparisons. Each pair differs in exactly one ingredient,
so each answers one question.

| Comparison | The one thing that differs | Question answered |
|---|---|---|
| M2 vs M1 | Task supervision | Does training on real pairs help at all? |
| M3 vs M2 | Vocabulary **and** extra pretraining | Does the representation change help? Not yet attributable |
| M3 vs Control A | Vocabulary only | Is the gain from the new tokens? |
| M3 vs Control B | Method, at equal compute | Is the gain from the method rather than the hours? |
| M4 vs M2 | Training distribution | Does more code-switched text help? |
| Baseline vs Gahoi et al. (2022), rows 1 and 2 | Nothing, if the harness is right | Can the harness be trusted? |

Every comparison is decided by the rule fixed in section 4.4 and requirements AI-1 to AI-3, set
before any result exists. **Primary metric:** chrF++. **A win:** at least +3 chrF++ with
non-overlapping error bars across seeds 13, 42 and 1337, confirmed by 1,000-sample bootstrap
intervals. **A null result:** under 1 chrF++, or overlapping bars.

How the main outcomes would be read:

| If we observe | We conclude |
|---|---|
| M3 beats M2, Control A and Control B by the success margin | The vocabulary explanation is supported: spelling variance costs quality, and extending the vocabulary recovers it |
| M3 beats M2, but Control A matches M3 | The gain is extra pretraining. The tokenizer explanation is not supported |
| M3 beats M2 and Control A, but Control B matches M3 | The gain is compute. The method adds nothing at equal cost |
| M2 closes most of the gap and M3 adds under 1 chrF++ | Missing supervision was the main cause; the tokenizer effect is too small to measure here |
| M4 beats M2 by the success margin | Scarce code-switched text is a cause, independent of the tokenizer result |
| All arms within 1 chrF++ of each other | A null result, reported as one |

## 4.3.4 The preferred model, and why

**M3 is the preferred model**, for a reason particular to this project. It is the only
configuration that acts on the quantity we measured. The tokenizer pays 1.832 tokens on average per
spelling of a Hinglish word, against a floor of 1.0 (`reports/fertility.variants.csv`). M3 is
designed to bring that number down and then check whether quality follows. M2 and M4 can improve
scores, but neither can say why. If M3 wins and also beats both controls, the result is an
explanation, not only a better number.

The preference is conditional. M3 is preferred **as the test of the hypothesis**, not on expected
accuracy. If a cheaper arm matches it, the cheaper arm is the better system, and the report will
say so.

## 4.3.5 When the preferred model would lose

There are five concrete ways M3 could lose, each with the evidence that would show it.

1. **The added tokens are too rare to learn.** The train split has 3,738 references. The whole
   corpus has 13,204 Hinglish word types (`reports/data_statistics.json`), so most candidate tokens
   would be seen only a handful of times. Their embeddings, which start as subword means, would
   barely move. **M2 would match or beat M3, and Control B would show that the extra hours did not
   help either.** The K sweep proposed in section 4.1, from 500 tokens up and chosen on dev, is the
   mitigation.
2. **The cost sits in a few words that writers already spell cheaply.** Burden counts every listed
   spelling once, however rarely it is used. Weighted by real usage on HinGE, the tokenizer pays
   **1.395 tokens per occurrence** over the 15 most frequent groups, against a burden of 1.722 for
   those same groups (`reports/variant_cost_hinge.json`). Writers favour cheap spellings: `hai`
   occurs 934 times at about one token. The saving available to M3 is therefore concentrated in a
   limited set of words. If those words matter little to chrF++, **M3 can improve fertility without
   moving quality.** That would be a real finding about the hypothesis, not a failure of the arm.
3. **The evaluation set is too small to separate the arms.** The interim surface is the HinGE test
   split: 468 references over 197 sources (section 3.5). The 800-item gold set has 0 items today
   (298-55). With intervals that wide, a true gain of 2 to 3 chrF++ can fall inside overlapping
   bars. **The honest answer would then be "no significant difference", and under AI-2 we report
   it that way.**
4. **Continued pretraining causes forgetting.** If replay is too low, the backbone's general English
   and Hindi degrade while Hinglish fertility improves. **M3 would then win on fertility and lose
   to M1 on fluency and adequacy**, and the human evaluation in section 4.4 would show it. Section
   4.1 raises replay to start at 20%, because lower values are outside the range Csaki et al.
   (2023) tested.
5. **The arm is not run in full.** The reserved compute exceeds the cap by 32 GPU-hours. If 298-72
   cuts a control arm to fit, an M3 gain can no longer be attributed. **M3 would then be reported as
   an unattributed result rather than preferred**, and the missing arm named in the results table.

## 4.3.6 A null result is an accepted outcome

The team committed to this before any model was trained: AI-2 states that a difference under
1 chrF++, or overlapping error bars, is published as a null result. A controlled ablation that rules
an explanation out is a finding. If M3 and its controls are indistinguishable, the report will say
that orthographic variance, as measured here, does not explain the quality loss on this corpus. It
will not search for a metric or subset on which M3 happens to win. The metrics and the decision rule
are fixed in section 4.4, which was merged before any scored run, so the git history shows which
came first.

## 4.3.7 Where this comparison is weakest today

- **No results exist.** Every row in section 4.3.2 is a design argument. The first scored runs are
  M1 (298-53) and M2 (298-54), both waiting on GPU access (298-51).
- **The tokenizer evidence is partly synthetic.** Burden (1.832) and the per-occurrence cost (1.395)
  are real-corpus or corpus-free figures. The fertility gap, 1.653 against 1.154, comes from
  regenerable synthetic slices (`reports/fertility_ai6.md`). The once-quoted coverage contrast,
  98.5% against 52.6%, did not survive re-measurement and must not be used to motivate M3.
- **The baseline gate can only be partly met.** Row 3 of Gahoi et al.'s Table 2 depends on an
  unreleased dictionary, so the reproduction is judged against rows 1 and 2.
- **M4 has not been run on a real corpus.** The generator has run only on a 30-sentence fixture. A
  real-corpus run with Romanisation is 298-76.

## Provenance

| Claim | Source |
|---|---|
| Model list, order and recipes | `docs/workbook2/section_4_1.md` |
| Backbone choice and rejected alternatives | `docs/workbook1/section_1_4.md` |
| Compute reservations and the 177 vs 145 conflict | `docs/COMPUTE_BUDGET.md`; `docs/workbook2/carry_forward.md` |
| Burden 1.832, per-occurrence cost 1.395, same-group burden 1.722 | `reports/fertility.variants.csv`; `reports/variant_cost_hinge.json` |
| Fertility on synthetic slices | `reports/fertility_ai6.md` |
| Split sizes and leakage guarantee | `docs/workbook2/section_3_5.md`; `data/processed/manifests/hinge_split_manifest.json` |
| Decision rule, seeds, bootstrap | `docs/workbook1/section_1_2.md` (AI-1 to AI-3); `docs/workbook2/section_4_4.md` |
| Baseline rows that can be rebuilt | `docs/baseline/gahoi_reproduction.md` |
| 0-shot Devanagari outputs, 13 of 48 | `docs/COMPUTE_BUDGET.md` |
