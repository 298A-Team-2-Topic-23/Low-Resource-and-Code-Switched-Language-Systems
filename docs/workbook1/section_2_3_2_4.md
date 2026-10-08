# 2.3 Resources and 2.4 Schedule

Linear [298-37](https://linear.app/298a-team-2-topic-23/issue/298-37).
Owner: Prakhar. Repository evidence checked on 7 October 2026 against main
`d41d6d8`. Resource availability and commercial quotes still need team confirmation.

## 2.3 Resource requirements

“Have” means a repository artifact is present. Hardware access is not inferred
from a requested allocation. USD costs below are either no additional licence
fee, unknown pending quotation, or explicitly labelled planning assumptions.

| Resource | Specification | Have / need | Cost | Justification |
|---|---|---|---|---|
| Training GPU | At least 40 GB VRAM per GPU; A100 40 GB class | Need; allocation unconfirmed | Cluster charge / cloud quote pending | Brief estimates M3 embedding training peaks near 30 GB; measure peak before approving full training |
| GPU slots | Three concurrent, independent single-GPU jobs | Need; concurrency unconfirmed | Included in compute allowance below; no double counting | Seeds 13, 42, 1337 can run independently; no multi-GPU interconnect or NVLink reservation required |
| Compute allowance | 130 GPU-hours target across 298A and 298B; hard upper bound 145 | Need; no committed training-run JSON on checked main | $260 at an assumed $2/GPU-hour; $290 at the 145-hour cap | Four models, three seeds, controls and evaluation; illustrative ceiling, not a vendor quote |
| CPU / storage | 64 GB host RAM; 500 GB scratch; separate backup for manifests and logs | Need; actual demo / cluster specs unconfirmed | Existing institutional capacity: no incremental charge if granted; otherwise quote pending | Tokenisation, dataset staging, temporary outputs and checkpoints; raw data remains outside Git |
| Demo laptop and backup | Python 3.10+; CPU pipeline; local licensed CSV/TSV and installed dependencies | Need two tested machines; allocation pending | Existing machines: no incremental purchase if available | Offline demo and hardware failure recovery; default system Python may be 3.9 |
| Research software | Pinned torch 2.6.0, transformers 4.57.6, tokenizers 0.22.2, accelerate 1.10.1, peft 0.17.1, sacrebleu 2.6.0; remaining pins in requirements.txt | Have pins and scripts; CUDA environment needs validation | No additional package licence fee budgeted | Consistent training / scoring environment; select compatible CUDA build on the allocated GPU |
| Chart tooling | matplotlib 3.9.4 + numpy 1.26.4; requirements-charts.txt | Have generator in this PR | No additional package licence fee budgeted | Regenerates the Gantt, PERT and machine-readable timing table without the training stack |
| Collaboration tools | GitHub repository and issue-linked PRs; Linear cycles | Have repository; current Linear state not queried here | Existing accounts; no upgrade budgeted | Independent review, ownership and artifact tracking |
| Data / model licences | Datasheet records source terms; exact backbone still unverified | Have datasheet; need model-card and data-use confirmation | No paid licence budgeted; unresolved terms remain a dependency | Licence approval precedes redistribution and model selection; budget availability does not establish permission |
| Fallback compute | Colab Pro+ or quoted single-GPU cloud allocation with measured VRAM / runtime limits | Contingency only; no subscription confirmed | Subscription / GPU-hour quote pending; purchase requires team decision | Use if institutional request fails; do not assume any subscription guarantees a 40 GB GPU or three slots |

### Compute budget and closing the gap

The abstract and `common/repro.py` commit to **80–145 GPU-hours**. Use **130** as
this section's working allocation. Main's README also contains a 120–170 plus
20-hour estimate; that conflicts with the abstract. This PR reconciles its
budget paragraph to the logger's 80–145 limit rather than silently adding budgets.

| Work package (planning estimate) | GPU-hours |
|---|---:|
| M1 zero-shot, three seeds / inference configurations | 6 |
| M2 QLoRA, three seeds | 24 |
| M3 vocabulary extension + CPT, three seeds | 36 |
| M4 augmentation and adaptation, three seeds | 24 |
| CPT without vocabulary extension control | 12 |
| M2 compute-matched control (24 existing + 12 extra = M3's 36) | 12 |
| Published-baseline reproduction and evaluation | 6 |
| Retry / profiling reserve | 10 |
| **Total target** | **130** |

These are allocations, not measured runtimes. Generation and CPT are charged
inside the relevant model allocation. Three GPUs shorten elapsed time; they do
not multiply a 130 GPU-hour allowance into 390 GPU-hours. Failed GPU runs count.
CPU preprocessing uses `n_gpus=0` when logged.

What we have: pinned software, reproducibility logging and a repository.
What we need: a confirmed 40 GB allocation, three independent slots and a
130 GPU-hour allowance. Prakhar closes the gap by requesting institutional
capacity and recording allocation, unit rate and quota before training. If
refused, obtain a fallback quote and team approval; the $2/hour example is only
a sensitivity assumption. At $1/$2/$3 per GPU-hour, 130 hours costs $130/$260/$390.
No funds or GPU availability are claimed as approved.

If only 24 GB cards are offered, profile M3 with gradient checkpointing and a
smaller batch. If peak memory remains too high, agree a smaller common backbone
for all compared models and record the methodological impact before training.
Do not wait until the M3 week to discover this constraint.

Record every training run with `RunLogger`, including failures, and review:

```bash
python common/repro.py --summary runs/
```

No training usage is evidenced by committed JSON on checked main. An empty
summary means “no runs recorded”, not proof that no external compute was used.
At 130 hours, review the remaining 15-hour headroom; do not exceed 145 without
an explicit documented change to the abstract and logger budget.

## 2.4 Schedule

All Workbook 1 issues belong to **Cycle 2, 28 September–12 October 2026**.
**Cycle 3 is 12–26 October**. The Gantt includes both cycle bands; it does not
move incomplete Workbook 1 work to Cycle 3. It shows owners, planned dates and
artifact status observed in the repository, rather than presenting old Linear
statuses as a live board query.

The planning milestones are workbook submission on **7 October** (the existing
management plan) and ISA/demo on **8 October** (the brief). Exact submission time
must be checked against the course portal. The 6 October due date for this issue
is already past; this section is recorded on 7 October and is not backdated.
Cycle 3 is the recovery / model-preparation window; training waits for verified
splits, licences, baseline validation and compute allocation.

![Workbook Gantt](../../reports/figures/workbook1_gantt.png)

### Dependencies and critical path

The dependency plan is:

- 298-38 pipeline → 298-39 EDA figures → 298-42 assembly → submission.
- 298-38 pipeline → 298-40 rehearsal → demo.
- All required writing and references must also be ready before final assembly.

![Workbook PERT](../../reports/figures/workbook1_pert.png)

The PERT uses elapsed **calendar days from 28 September**. Durations are planning
assumptions, not Fibonacci story points or measured execution times. Terminal
deadlines are day 9 (submission) and day 10 (demo). The forward pass calculates
ES/EF; the backward pass calculates LS/LF; total float is LS − ES.

| Task | Duration | ES | EF | LS | LF | Float |
|---|---:|---:|---:|---:|---:|---:|
| 298-38 pipeline | 5 | 0 | 5 | 0 | 5 | **0** |
| 298-39 EDA | 2 | 5 | 7 | 5 | 7 | **0** |
| 298-42 assembly | 2 | 7 | 9 | 7 | 9 | **0** |
| Submission milestone | 0 | 9 | 9 | 9 | 9 | **0** |
| 298-40 rehearsal window | 4 | 5 | 9 | 6 | 10 | **1** |
| Demo milestone | 0 | 9 | 9 | 10 | 10 | **1** |

**Critical path: 298-38 → 298-39 → 298-42 → submission.** Pipeline has no
float; EDA and assembly also have zero float in this dependency calculation.
The brief's shorthand that everything else can slip a day cannot apply to
those downstream tasks without moving the submission. Rehearsal has one day
of float. This baseline is already at risk: main lacks the pipeline; a pipeline
branch exists, but no complete workbook or team rehearsal is evidenced.
The charts show the plan, not a claim that its original dates were met.

Regenerate both charts and the auditable CSV from the repository root:

```bash
python -m pip install -r requirements-charts.txt
python scripts/charts.py
```

Outputs: `reports/figures/workbook1_gantt.{png,svg}`,
`workbook1_pert.{png,svg}`, and `workbook1_pert.csv`. Update dates, durations
and artifact statuses in the generator when the team confirms a revised plan.
Shibin and Jenil are the requested review pair for this issue.
