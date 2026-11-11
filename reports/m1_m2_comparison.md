# M1 against M2, on real data

Two independent runs of the same comparison. The second one overturned the first one's most
interesting finding, and this document keeps both, because the disagreement is the result.

| | Run A — laptop | Run B — A100 |
|---|---|---|
| Date | 10 November 2026 | 11 November 2026 |
| Hardware | Apple M4, 16 GB, MLX | NVIDIA A100-SXM4-40GB (Colab) |
| Base | `mlx-community/Qwen2.5-7B-Instruct-4bit` | `Qwen/Qwen2.5-7B-Instruct` |
| Quantisation | MLX affine 4-bit, group 64 | **bitsandbytes NF4, double** — the §4.1 recipe |
| Precision | — | bf16 (native; A100 is Ampere) |
| Training seen | 600 steps at batch 1 ≈ **0.16 epochs** | 351 steps at effective batch 32 = **3 epochs** |
| Seeds | 1 (42) | **3 (13, 42, 1337)** |
| Compute | 1.33 GPU-hours | 1.508 GPU-hours |

Run B is the reportable one: it is the recipe §4.1 actually specifies, at the scale it specifies,
with the seed count 298-54 asks for. Run A is kept because it is what exposed the question.

## 1. The headline: at three epochs, M2 improves on *both* axes at once

**Run A found a contradiction.** M2 won chrF++ by +14.538 while its code-mixing moved *away* from
human — CMI 15.40 → 11.88 against a human 25.86. Section 4 of this document recorded that the model
was deliberately undertrained and that the direction might reverse with a longer run.

**It reversed.** Run B, at three full epochs:

| Code-mixing metric | Human target | M1 zero-shot | **M2, 3 seeds** | M2 − human |
|---|---:|---:|---:|---:|
| CMI | 25.860 | 22.707 | **24.782** ± 0.42 | −1.078 |
| CMI (mixed only) | 30.256 | 32.415 | **28.550** ± 0.48 | −1.706 |
| % sentences mixed | 85.47% | 70.05% | **86.80%** ± 0.00 | +1.33 |
| Switch-point fraction | 0.2366 | 0.3063 | **0.2446** ± 0.004 | +0.008 |
| M-index | 0.6956 | 0.9228 | **0.6918** ± 0.024 | −0.004 |
| Tagger coverage | 0.686 | 0.718 | 0.729 ± 0.012 | +0.043 |

M2 lands essentially **on** the human target on every code-mixing measure. M-index differs from the
human references by 0.004; switch-point fraction by 0.008. For comparison, run A's M2 sat at CMI
11.88, SPF 0.0951, M-index 0.2978 — less than half the human value on two of the three.

And it does this while also winning the quality metrics:

| Metric | M1 0-shot (3 seeds) | M1 5-shot (3 seeds) | **M2 QLoRA NF4 (3 seeds)** |
|---|---:|---:|---:|
| **chrF++** (primary) | 40.666 ± 0.000 | 38.474 ± 1.004 | **51.683 ± 1.154** |
| chrF++ normalised | 41.796 ± 0.000 | 39.436 ± 1.017 | 52.948 ± 1.043 |
| BLEU | 23.120 ± 0.000 | 16.110 ± 1.829 | 38.749 ± 1.287 |
| ROUGE-L | 0.416 ± 0.000 | 0.362 ± 0.021 | 0.506 ± 0.012 |
| WER (lower better) | 0.750 ± 0.000 | 0.824 ± 0.020 | 0.639 ± 0.023 |
| chrF++ 95% CI | [38.565, 42.962] | [36.662, 40.336] | [49.641, 53.730] |

**+11.017 chrF++ from M1 to M2.** The 95% intervals do not overlap: M1 tops out at 42.962, M2
starts at 49.641.

**Devanagari leakage is eliminated, confirmed on three seeds.** M1 produced 3 Devanagari-bearing
outputs of 197; M2 produced **0, on all three seeds**. For a project targeting Romanised Hinglish
that is a categorical fix, invisible to every quality metric above.

## 2. What run A's contradiction actually was

Undertraining, not the recipe. Section 3 of the earlier version of this document proposed a
mechanism from reading outputs: humans write a Hindi frame with English content words inserted,
while run A's M2 wrote an English frame with Hindi function words inserted. The two runs together
support that reading:

| | Training seen | chrF++ | CMI | Reading |
|---|---:|---:|---:|---|
| Run A M2 | ~0.16 epochs | 57.808 | 11.88 | stays near the English source |
| Run B M2 | 3 epochs | 51.683 | 24.78 | code-switches like the references |

A model that has barely moved off its base keeps the English source's words, and chrF++ rewards
exactly that, because the references share those words too. Three epochs later it has learned to
restructure into Hindi word order, which costs surface n-gram agreement and buys genuine
code-switching.

**This is a real trade-off between the two metric families, and it is the project's most defensible
finding.** It is also why §4.4 committed to both before any result was in: run A's chrF++ alone
would have been read as "M2 learned to code-switch", and it had not.

**Caveat on that comparison.** Runs A and B differ in quantisation, inference precision and
framework as well as in training length, so the 57.808 → 51.683 drop is *consistent with* the
mechanism, not a controlled demonstration of it. Only the within-run M1→M2 contrasts are clean.
Isolating length alone would need run B's recipe at 0.16 epochs, which has not been done.

## 3. Few-shot prompting makes M1 worse

M1 5-shot scores **below** M1 0-shot on every metric: chrF++ 38.474 against 40.666, BLEU 16.110
against 23.120, WER 0.824 against 0.750. The smoke profile showed the same direction on a 0.5B
stand-in. Five in-context Hinglish examples do not help this base model and measurably hurt it,
which makes the 0-shot condition the honest M1 baseline and is worth a line in §4.3.

## 4. What this still does not establish

- **M1 0-shot's "± 0.000" is not evidence of stability.** Decoding is greedy, so the seed cannot
  change the output; all three seeds produced identical text. Three seeds of M1 0-shot is
  structurally redundant compute, and the zero should be read as "seed is inapplicable here", not
  as a measured variance. M1 5-shot does vary (± 1.004) because the exemplars are seed-sampled, and
  M2 varies (± 1.154) because training does.
- **No paired bootstrap on run B yet.** The +11.017 is a difference of means with non-overlapping
  per-system intervals, not a paired test over test items. Run A's +14.538 [10.776, 18.241] was
  paired. Producing the equivalent for run B needs `run_eval.py --vs-hyp`, which was not called in
  the notebook, and the generated outputs were not collected from the runtime — see §6.
- **Checkpoint selection was not validated.** Run B trains three epochs and keeps the final
  adapter. No validation loss was computed during training, so there is no evidence the final
  checkpoint is the best one. Run A's curve showed validation worsening after iteration 450, so the
  concern is live. Training loss alone (1.4951 / 1.5011 / 1.5004 across seeds, strikingly
  consistent) cannot answer it.
- **One corpus, one language pair.** Everything here is HinGE Hindi–English.

## 5. What it establishes for Team Meeting 2

1. The spec-faithful recipe — NF4 double quantisation, rank 32, alpha 64, all seven projections —
   runs, converges, and produces a large improvement on the committed primary metric, on three
   seeds, with a run record each.
2. **Fine-tuning on real Hinglish teaches genuine code-switching**, to within 0.004 M-index of human
   references, not merely surface agreement with them.
3. Training eliminates Devanagari leakage outright.
4. The project's two metric families measure different things and can move in opposite directions.
   Run A is the demonstration, and it is a stronger argument for the evaluation design than any
   result where the metrics agree.
5. Compute: **2.93 GPU-hours cumulative** against the 145-hour cap, across laptop, T4 smoke and
   A100.

## 6. Provenance

| Item | Value |
|---|---|
| Corpus | HinGE, `LingoIITGN/HinGE` rev `e25a1038`, CC-BY-4.0, input SHA-256 `dcfaf37c…` |
| Splits | `hinge_split_manifest.json`, 3,738/468/468, hashes reproduced in Colab, leakage gate passed |
| Test set | 197 sources, 468 references, mean 2.376 per source |
| Recipe (run B) | `models/train_qlora.py`, 3 epochs, effective batch 32, max_len 512, lr 2e-4 |
| Recipe (run A) | `configs/m2_lora_qwen7b.yaml` |
| Run B records | `runs/20261111T21*.json`, `runs/20261111T22*.json`, `runs/20261111T23*.json` |
| Run A records | `runs/20261110T2*.json` |
| Scores | `results/results.jsonl`, `reports/codemixing_systems.json` |
| Notebook | `notebooks/m1_m2_colab.ipynb`, profile `a100` |

**Known gap in the evidence chain.** The notebook's collection cell zips run records and scores but
**not the generated outputs** (`out/m1.*.txt`, `out/m2.*.txt`). Those are the primary artefact —
every number here is derived from them, the §2 qualitative reading came from them, and the paired
test in §4 needs them. They died with the runtime. Run B's text cannot be re-examined or re-scored
without re-running it. The collection cell should carry them, and until it does, no run of this
notebook is fully reproducible after the fact.
