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

“Remaining” is unused planning allowance against the 80-hour lower bound, not
funded capacity or an allocated quota. The logged total is 0.112 GPU-hours;
unused allowance against the 145-hour upper bound is 144.888 GPU-hours.

## Allocation checkpoint — 22 October 2026 (298-10 / 298-51)

**Not ready for funded training.** The owner confirmed on 22 October that there is
no confirmed university allocation and no funded cloud fallback. No new GPU job
was run for this checkpoint. The existing free-Colab smoke records below remain
the only committed GPU execution evidence.

| Required evidence | Current state | What closes the gap |
|---|---|---|
| University response | Request reported submitted on 26 September in the 298-10 audit comment; quota unconfirmed | Written approval or formal refusal for this project |
| Concurrent slots | Unknown; request is three independent single-GPU jobs | Approved slot count, access period and account/project scope |
| Card and memory | Unknown; request includes at least one GPU with 40 GB or more VRAM | Exact card class and VRAM; confirm separately from host RAM |
| Hours / charge | No allocation or approved spend evidenced | Written GPU-hour allowance, charging basis and access instructions |
| Funded fallback | Not funded | Owner-approved purchase, usable balance and measured runtime hardware |
| Fallback training proof | Existing 0.5B/synthetic/free-T4 pilot only | A new training job on the funded runtime, saved adapter, reload/generation and run JSON |
| 24 GB contingency | Availability unknown | Profile memory before M3; record an agreed smaller common backbone if needed |

The September request date above is a board claim, not a newly verified submission
receipt. Earlier personal lab reservations do not establish this project's quota.
Keep both issues open until their acceptance evidence exists. Follow
[the allocation and fallback runbook](COMPUTE_ALLOCATION.md) for the request fields,
pilot commands and closure checklist. A successful synthetic pilot establishes
infrastructure only; it cannot close the real-corpus M1/M2 research issues.

### Budget discrepancy requiring a team decision

The arm estimates at the end of this file sum to **177 GPU-hours**, including
20 for inference/evaluation (157 excluding that row). That exceeds even a reading
of the abstract as 145 training hours **plus** 20 inference hours by 12 hours.
[Workbook 1 §2.3](workbook1/section_2_3_2_4.md) instead allocates 130 total hours
with a 145-hour cap, and `common/repro.py` uses 80–145 for its summary.

These are conflicting plans, not approved capacity. Retain the original numbers
for audit; agree which scope the cap covers and resize the allocations or obtain
an explicit budget revision before committing full-run spend. Controls remain in
scope. No purchase or revised methodological budget is authorized by this entry.

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

**Every GPU model row above is a smoke test on synthetic data with a 0.5B stand-in model.
None is a reportable model result.** The purpose was to prove the path executes on CUDA, including the
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
