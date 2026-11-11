# Compute budget

Every training and inference run is logged here in the same commit as the run, so the
GPU-hour claim in the report is evidenced rather than asserted. The machine-readable source
is `runs/*.json`, one record per run; this file is the human-readable roll-up.

**Hard cap: 165 GPU-hours** across both semesters: **145 for training** and **20 for
inference and evaluation**. The plan uses **154**, leaving 11 in reserve. Decided under
[298-72](https://linear.app/298a-team-2-topic-23/issue/298-72) on 11 November 2026; the
decision and its arithmetic are [below](#budget-decision--298-72-11-november-2026).
`python common/repro.py --summary runs/` prints the running total against it.

## Running total

| | GPU-hours |
|---|---|
| Spent to date | **0.112** |
| Planned, all arms | 154 |
| Hard cap | 165 |
| Unspent against the cap | 164.888 |

“Unspent” is planning allowance, not funded capacity or an allocated quota: no allocation
or fallback is confirmed (next section). The logged total is 0.112 GPU-hours, all smoke tests.

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

Allocations, not measured runtimes. The 177-hour column is kept for audit.

| Arm | Before 298-72 | Now | Status |
|---|---|---|---|
| M1 zero-shot, 3 seeds, 0- and 5-shot | 2 | **2** | 298-53, not started on the real corpus |
| M2 QLoRA, 3 seeds | 25 | **25** | 298-54, blocked on 298-51 |
| Baseline reproduction (mBART-large-cc25), both input conditions | 15 | **15** | 298-52 |
| M3 vocabulary extension + CPT, 3 seeds, **one K** | 45 | **36** | 298B |
| Control A: CPT without vocabulary extension | 20 | **20** | 298B, required for attribution. See open risk 1 |
| Control B: each M2 seed **continued** to M3's GPU-hours | 25 | **11** | 298B, required for attribution |
| M4 augmented, 3 seeds | 25 | **25** | 298B |
| Inference and evaluation | 20 | **20** | throughout; chrF++ scoring itself is CPU work |
| **Total** | **177** | **154** | |
| Reserve against the 165 cap | — | **11** | failed runs count against it |

Both control arms stay. Without Control A an M3 gain cannot be attributed to the vocabulary
rather than the extra training, and without Control B it cannot be separated from simply having
had more compute.

Synthetic generation and continued pretraining count **inside** the budget of the arm that
uses them, not as separate lines.

## Budget decision — 298-72, 11 November 2026

**The conflict.** The reservations above summed to **177 GPU-hours**. Workbook 1 section 2.3
committed to a 130-hour target and a **145-hour hard cap**, and said not to exceed it "without
an explicit documented change to the abstract and logger budget". The plan could not be run as
written: 32 hours over the cap.

**Options considered.**

| Option | Plan | Cap | What it costs |
|---|---|---|---|
| Raise the cap only | 177 | 180 | Nothing cut. $360 at $2/GPU-hour; widest change to the commitment |
| Shrink to fit 145 total | 144 | 145 | Also cuts the baseline to 8 hours (unmeasured), M2 and M4 to 24 and inference to 18, leaving **1 hour** of reserve. One failed seed breaks it |
| **Two cuts, cap made explicit (chosen)** | **154** | **165** | Below |

**The decision.**

1. **M3 trains one vocabulary size on the GPU: 45 → 36.** Section 4.1 proposes sweeping
   K over {500, 1K, 3K, 5K, 8K} *at the tokenizer level, which needs no GPU*, and fixing K on the
   dev split before any GPU time is spent. The Phase 3 brief attributes the 45 hours to the K
   sweep; on the GPU, only the chosen K needs training. **What the experiment loses:** if the dev-chosen K trains poorly, there is no budgeted
   second K. Section 4.1 already names the mitigation (Align initialisation instead of Mean),
   which costs no extra GPU arm.
2. **Control B continues each M2 seed instead of retraining it: 25 → 11.** Section 4.1 defines
   Control B as the M2 recipe trained until its GPU-hours equal M3's, and section 2.3 already
   charged it "as the increment beyond M2's own run". The 25-hour figure re-ran M2 from scratch.
   The increment is M3 − M2 = 36 − 25 = **11**. **What the experiment loses:** Control B's
   learning-rate schedule becomes two segments (M2's full cosine, then a second schedule) rather
   than one longer run. A reviewer could argue the continued run is under-tuned; the results
   section must state the schedule. `models/train_qlora.py` has no resume-from-adapter option
   yet, so this arm needs one.
3. **The cap is made explicit: 145 for training plus 20 for inference and evaluation, 165
   total.** Workbook 1 counted inference inside 145; this file has carried "plus roughly 20 for
   inference and evaluation" since 298-26. The 145-hour figure the abstract commits to is now the
   **training** cap. Section 2.3 is amended in place (with the original text kept) and
   `common/repro.py` reports against 165.

**Arithmetic.** 2 + 25 + 15 + 36 + 20 + 11 + 25 + 20 = **154**. Training alone is 134 against the
145 training cap. 165 − 154 = **11 hours of reserve**. At the $2/GPU-hour planning assumption the
cap costs **$330**, against $290 at the old 145-hour cap: $40 more, and only if the hours are
actually used. No purchase is authorised by this entry; funding still follows
`docs/COMPUTE_ALLOCATION.md`.

**Open risks carried with the decision.**

1. **Control A may cost what M3 costs.** It runs M3's two stages on the original vocabulary, so
   at equal steps it would take about M3's 36 hours, not 20. That would put the plan at 170, over
   the cap. Control A must be step-matched to M3 to isolate the vocabulary, so the 20-hour
   figure, not the step count, is what gives. **The first measured M3 seed settles it, and
   Control A is not scheduled until that measurement exists.** If it is 36, the team decides
   between a further cap change and fewer Control A seeds, and records the decision here.
2. **Every figure is an estimate.** No 7B job has run. After the first real M2 seed, replace
   the per-seed figures with measured ones (298-73's roll-up projects from them) and re-check
   the total before M3 is scheduled.

**Sign-off.** Proposed by Singh, Prakhar Kumar, 11 November 2026. Agreed by:

| Member | Agreed | Date |
|---|---|---|
| Singh, Prakhar Kumar | yes | 11 Nov 2026 |
| Thomas Lnu, Shibin | | |
| Savalia, Jenil Sanjaybhai | | |
| Shevkar, Yash | | |
| Waghmare, Sarvesh | | |

To be confirmed at Team Meeting 2 on 12 November. Until the table is complete, the plan is the
owner's proposal, not a team commitment.
