# 4.3 Model Comparison and Justification

Linear **298-69**. Written by Shevkar, Yash.

This section compares the six configurations and the reproduced baseline of §4.1 and justifies
each. **Each model is justified by what it rules out**, not by how well we expect it to score.
The project asks why quality drops on Romanized Hinglish, and three explanations compete:
missing task data, the tokenizer, and scarce code-switched text. A model earns its place by
isolating one.

*Status, 11 November: M1 and M2 are now scored on the real corpus across three seeds (§4.5).
The design arguments below stand as written; where a row says "not yet run" it means M3, M4 and
the controls.*

## 4.3.1 Statistics, classical machine learning and deep learning

The rubric asks for all three families. **All six configurations and the baseline are deep
learning**, which is a decision with reasons. Statistical and classical methods are used as
components where they fit better, but not as the generator.

| Family | Candidate | Decision and reason |
|---|---|---|
| Statistical: rules and dictionaries | Aligned substitution then transliteration, as HinGE's own WAC/PAC generators do | **Rejected as a model.** No subword tokenizer, so it cannot test a claim about how a pretrained tokenizer handles spelling. Its authors report deliberate noise in the outputs, making it a data source, not a competitor |
| Statistical: alignment | IBM Model 1 by EM | **Used inside M4** to locate switch points satisfying the Equivalence Constraint. No GPU, deterministic, inspectable |
| Statistical: inference | Bootstrap over seeds and test items | **Used in evaluation** (§4.4, AI-3). Without it no comparison here can be called significant |
| Classical ML | Count-based translation or nearest-neighbour retrieval | **Rejected.** 3,738 references over 1,549 sources cannot cover open-domain English, and retrieval fails by construction: the leakage gate guarantees no test source or near-duplicate is in train, so the nearest training reference is always a different sentence |
| Classical ML | Word-level language ID and spelling normalisation | **Used where it serves measurement**: the LinCE-style tagger (§3.3) and lexicon normalisation for the secondary metric (§4.4). Neither generates text |
| Deep learning: encoder–decoder | mBART | **Baseline only**, to prove the harness reproduces a published number |
| Deep learning: decoder LLM | Qwen2.5-7B-Instruct with prompting, adapters and vocabulary change | **Adopted for all six.** The only backbone whose tokenizer cost was measured, and pretraining supplies knowledge 3,738 references cannot |

The deciding argument is method, not accuracy. The claim concerns how a **pretrained subword
tokenizer** treats spelling variants; testing it requires holding the model family fixed and
changing one ingredient at a time. Comparing a rule system against a neural model changes
everything at once and answers nothing.

## 4.3.2 The models compared

| Model | Targeted problem | Approach | Strengths | Limitations | What it rules out |
|---|---|---|---|---|---|
| **M1** 0/5-shot | How large is the gap before adaptation? | Unmodified backbone, fixed prompt, greedy, 128 new tokens | No training; the reference point every gain is measured from | 0-shot is deterministic, so its three-seed spread is zero by construction; produced Devanagari in 3 of 197 outputs | **Sizes the problem** |
| **M2** QLoRA | Is it simply missing supervision? | Rank-32 LoRA on seven projections over a 4-bit NF4 base; loss on completion only | Cheap; fits one card; recipe held fixed so later arms compare | Cannot change tokenization, so `nahi`/`nhi`/`nahin` stay unrelated; only 3,738 references | **Rules out "just add task data"** |
| **M3** vocab + CPT | Is it the tokenizer and orthographic variance? | SentencePiece diff adds K tokens, mean-initialised; embeddings then adapters, with replay | The **only** arm acting on the measured cost (burden 1.832 against a floor of 1.0); cheaper inference if fertility falls | Most expensive arm; new embeddings learned from a small corpus; forgetting risk; no CPT corpus named yet | **Tests the hypothesis** — counts only if it also beats both controls |
| **M4** augmented | Is it scarce code-switched text? | M2 recipe on HinGE plus back-translation and Equivalence-Constraint synthesis at SPF 0.2398 | Attacks scarcity without changing the model; generator has 28 tests | Synthetic text carries its own errors, including from Romanisation; needs contamination checking first | **Rules out data scarcity**, or confirms it |
| **Control A** | Vocabulary, or just extra training? | M3's stages, same data and steps, **original** tokenizer | Gives M3's result its meaning | No deployable model of its own | **Separates vocabulary from pretraining** |
| **Control B** | Or just more compute? | Unchanged M2 recipe to M3's GPU-hours | Cheapest test of the compute explanation | More epochs on 3,738 references may overfit — itself informative | **Separates method from compute** |
| **Baseline**, *not one of the four* | Does our harness reproduce a published number? | mBART on English+Hindi with transliteration, rebuilt from the paper | A published figure to check against | No code released; the headline 0.617 depends on an unreleased dictionary, so only rows 1 and 2 (0.391, 0.484) can be rebuilt | **Rules out a broken harness** |

Compute reservations are in `docs/COMPUTE_BUDGET.md`. They summed to 177 GPU-hours against §2.3's
145 cap; under 298-72 no arm was dropped — M3 trains one K on GPU (45→36) and Control B continues
each M2 seed rather than retraining (25→11), giving 154 against a cap made explicit as 145
training plus 20 inference. **Both controls, and so this section's attribution argument, are
intact.** Measured against that, M1 and M2 together cost 1.508 GPU-hours against a 27-hour
reservation, so the remaining estimates are probably loose.

## 4.3.3 What each comparison isolates

| Comparison | The one thing that differs | Question answered |
|---|---|---|
| M2 vs M1 | Task supervision | Does training on real pairs help at all? |
| M3 vs M2 | Vocabulary **and** extra pretraining | Does the representation change help? Not yet attributable |
| M3 vs Control A | Vocabulary only | Is the gain from the new tokens? |
| M3 vs Control B | Method, at equal compute | Is it the method rather than the hours? |
| M4 vs M2 | Training distribution | Does more code-switched text help? |
| Baseline vs Gahoi rows 1–2 | Nothing, if the harness is right | Can the harness be trusted? |

Every comparison is decided by the rule fixed in §4.4 before any result existed. **Primary
metric:** chrF++. **A win:** at least +3 chrF++ with non-overlapping error bars across seeds 13,
42 and 1337, confirmed by 1,000-sample bootstrap. **A null:** under 1 chrF++, or overlapping bars.

| If we observe | We conclude |
|---|---|
| M3 beats M2, Control A and Control B by the margin | The vocabulary explanation is supported |
| M3 beats M2, but Control A matches M3 | The gain is extra pretraining; the tokenizer explanation is not supported |
| M3 beats M2 and A, but Control B matches M3 | The gain is compute; the method adds nothing at equal cost |
| M2 closes most of the gap and M3 adds under 1 chrF++ | Missing supervision was the main cause |
| M4 beats M2 by the margin | Scarce code-switched text is a cause, independent of the tokenizer |
| All arms within 1 chrF++ | A null result, reported as one |

## 4.3.4 The preferred model, and why

**M3 is preferred**, for a reason particular to this project: it is the only configuration that
acts on the quantity we measured. The tokenizer pays 1.832 tokens on average per spelling of a
Hinglish word against a floor of 1.0. M3 is designed to bring that down and then check whether
quality follows. M2 and M4 can improve scores but neither can say why. If M3 wins and beats both
controls, the result is an explanation, not only a better number.

The preference is conditional. M3 is preferred **as the test of the hypothesis**, not on expected
accuracy. If a cheaper arm matches it, the cheaper arm is the better system and the report says so.

## 4.3.5 When the preferred model would lose

Five concrete ways, each with the evidence that would show it.

1. **The added tokens are too rare to learn.** 3,738 references against 13,204 Hinglish word
   types means most candidate tokens are seen a handful of times, and their mean-initialised
   embeddings barely move. **M2 would match or beat M3, and Control B would show the extra hours
   did not help either.** Mitigation: the K sweep from 500 up, chosen on dev (§4.1).
2. **The cost sits in words writers already spell cheaply.** Weighted by real usage the tokenizer
   pays **1.395 tokens per occurrence** over the 15 most frequent groups against a burden of
   1.722 for the same groups; `hai` occurs 934 times at about one token. If those words matter
   little to chrF++, **M3 can improve fertility without moving quality** — a real finding about
   the hypothesis, not a failure of the arm.
3. **The evaluation set is too small to separate the arms.** The interim surface is 468
   references over 197 sources; the 800-item gold set holds 0 today (298-55). A true 2–3 chrF++
   gain can fall inside overlapping bars, and **under AI-2 we report "no significant difference"**.
4. **Continued pretraining causes forgetting.** With replay too low, general English and Hindi
   degrade while Hinglish fertility improves: **M3 wins on fertility and loses to M1 on fluency**,
   which the human evaluation would show. §4.1 raises replay to start at 20%.
5. **The arm is not run in full.** 298-72 resolved the budget without dropping a control, so this
   risk is reduced but not gone: Control A may cost M3's 36 hours rather than the 20 budgeted, and
   if it is cut to fit, **M3 becomes an unattributed result rather than the preferred one**.

## 4.3.6 A null result is an accepted outcome

Committed before any model was trained: AI-2 states that a difference under 1 chrF++, or
overlapping bars, is published as a null result. A controlled ablation that rules an explanation
out is a finding. If M3 and its controls are indistinguishable, the report will say that
orthographic variance as measured here does not explain the quality loss on this corpus. It will
not search for a metric or subset on which M3 happens to win.

## 4.3.7 Where this comparison is weakest today

- **Four of seven rows are still design arguments.** M1 and M2 are measured; M3, M4, both
  controls and the baseline are not.
- **One comparison the measured rows already complicate.** M2 beat M1 by +11.0 chrF++ while its
  code-mixing moved *toward* the human target only after three full epochs — at 0.16 epochs it
  moved away (§4.5). A chrF++ win and a code-switching win are not the same event, which
  strengthens the case for §4.4's two metric families and weakens any reading of the ladder on
  chrF++ alone.
- **The baseline gate can only be partly met.** Row 3 of Gahoi et al.'s Table 2 depends on an
  unreleased dictionary, so the reproduction is judged against rows 1 and 2. The MixMT test set
  it names was never released at all (§3.2, carry-forward).
- **M4 has not been trained.** Its generator has run on a real 29,996-pair slice, but the output
  is not yet fit to train on.

**Provenance.** Model list from §4.1; backbone choice from `docs/workbook1/section_1_4.md`;
compute from `docs/COMPUTE_BUDGET.md`; burden and per-occurrence cost from
`reports/fertility.variants.csv` and `reports/variant_cost_hinge.json`; split sizes and the
leakage guarantee from §3.5 and the split manifest; the decision rule from
`docs/workbook1/section_1_2.md` and §4.4; measured M1/M2 figures from
`reports/m1_m2_comparison.md`.
