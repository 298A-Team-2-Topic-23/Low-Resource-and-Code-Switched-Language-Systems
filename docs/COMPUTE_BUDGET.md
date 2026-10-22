# Compute budget

Every training and inference run is logged here in the same commit as the run, so the
GPU-hour claim in the report is evidenced rather than asserted. The machine-readable source
is `runs/*.json`, one record per run; this file is the human-readable roll-up.

**Budget: 80–145 GPU-hours** across both semesters, plus roughly 20 for inference and
evaluation. `python common/repro.py --summary runs/` prints the running total against it.

## Running total

| | GPU-hours |
|---|---|
| Spent to date | **0.112** |
| Budget (lower bound) | 80 |
| Remaining | 79.9 |

Essentially nothing is spent, because no training has run on the real corpus yet. The
allocation itself is still unconfirmed — see 298-51, open since 26 September.

## Runs

| Date | Run | Seed | GPU | Precision | GPU-h | Notes |
|---|---|---|---|---|---|---|
| 2026-10-08 | data-pipeline | 42 | CPU | — | 0.000 | synthetic smoke |
| 2026-10-08 | data-pipeline | 42 | CPU | — | 0.000 | real HinGE corpus, 11.96 s |
| 2026-10-22 | data-pipeline | 42 | Tesla T4 | — | 0.000 | synthetic, Colab; the pipeline is CPU-only work |
| 2026-10-22 | model1-0shot | 13 | Tesla T4 | — | 0.013 | 48 lines; 13 outputs contained Devanagari |
| 2026-10-22 | model1-5shot | 13 | Tesla T4 | — | 0.008 | 48 lines; 0 Devanagari |
| 2026-10-22 | model2-qlora | 13 | Tesla T4 | bf16 (emulated) | 0.085 | 30 steps, loss 1.974, 17.6M trainable |
| 2026-10-22 | model2-qlora-0shot | 13 | Tesla T4 | — | 0.006 | adapter reloaded and scored |

**Every row above is a smoke test on synthetic data with a 0.5B stand-in model. None of it
is a reportable result.** The purpose was to prove the path executes on CUDA, including the
4-bit NF4 quantised branch, which could not be tested on the team's Apple Silicon machines.

### A note on the 2026-10-22 precision

That run recorded `bf16` on a Tesla T4. A T4 is Turing and has no bf16 silicon;
`torch.cuda.is_bf16_supported()` counts emulated support by default and answered True, so
training went through a software path and thirty steps of a 0.5B model took 301 seconds.
The trainer now asks for native support only and falls back to fp16 on Turing. Later T4
rows should read `fp16`, and a row that still reads `bf16` on a pre-Ampere card means the
fix has regressed.

## What the budget is reserved for

| Arm | Estimate | Status |
|---|---|---|
| M1 zero-shot, 3 seeds, 0- and 5-shot | ~2 | 298-53, not started on the real corpus |
| M2 QLoRA, 3 seeds | ~25 | 298-54, blocked on 298-51 |
| Baseline reproduction (mBART), both input conditions | ~15 | 298-52 |
| M3 vocabulary extension + CPT, 3 seeds | ~45 | 298B |
| Control A: CPT without vocabulary extension | ~20 | 298B, required for attribution |
| Control B: M2 re-trained to M3's GPU-hours | ~25 | 298B, required for attribution |
| M4 augmented, 3 seeds | ~25 | 298B |
| Inference and evaluation | ~20 | throughout |

The two control arms account for roughly 45 GPU-hours between them. They are not optional:
without Control A an M3 gain cannot be attributed to the vocabulary rather than the extra
training, and without Control B it cannot be separated from simply having had more compute.

Synthetic generation and continued pretraining count **inside** the budget of the arm that
uses them, not as separate lines.
