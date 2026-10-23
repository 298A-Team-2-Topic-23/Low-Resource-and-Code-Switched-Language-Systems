# Board reset: issues marked Done without an artifact

Linear **298-45**. Owner: Prakhar; performed by Sarvesh on 23 October 2026 while Prakhar was
unavailable. Audited against `main` at commit `14e2a59`.

Progress Report 1 lost marks because the report, the Linear board and the repository could
not corroborate each other. The rule adopted in response is in `docs/progress2/part_a_status.md`
and is applied here: **an issue is complete only if a reader can open its artifact on `main`
and run it.** An issue whose code is merged but whose result does not exist is in progress,
not done.

Eight issues failed that test. Each was reset and each carries a Linear comment naming what
is missing and the issue that now tracks the remainder. Nothing was deleted and no history
was rewritten — the comments are the audit trail.

| Issue | Was | Now | Why | Tracked by |
|---|---|---|---|---|
| 298-10 Submit GPU allocation request and confirm quota | Done | In Progress | Request submitted 26 Sep; quota never confirmed. All 0.112 GPU-hours in `docs/COMPUTE_BUDGET.md` were spent on a free Colab T4, not an allocated card | 298-51, 24 Oct |
| 298-15 Reproduce Gahoi baseline, two-input condition | Done | Todo | No mBART code anywhere in the repository; `grep -rli mbart` returns prose only. No run record, nothing scored against ROUGE-L 0.617 | 298-52, 7 Nov |
| 298-16 Reproduce Gahoi baseline, English-only condition | Done | Todo | Same: no code, no run, and blocked by 298-15 | 298-52, 7 Nov |
| 298-17 Stand up GCM synthetic code-mixing pipeline | Done | Todo | GCM appears only in prose and references. No generation code, no switch-point-matched sampler, no synthetic batch. Due 14 Oct, passed with nothing produced | re-plan into 298B; nearest 298A work is 298-58 |
| 298-21 Author 800-item three-column gold set | Done | Todo | `data/goldtestset/gold_set.csv` holds 1 row — the header. 0 of 800 items exist. Success criterion AI-1 is defined on this set | 298-55, 5 Nov |
| 298-23 Normalised chrF++ with spelling-variant lexicon | Done | In Progress | Nine regex rules work, but the lexicon is not wired in: they fully collapse 3 of its 72 groups, and two rules corrupt forms (`hy`→`y`, `hna`→`na`). `tokenise()` is built on `normalise()`, so ROUGE-L and WER are computed on normalised tokens too | 298-59, 2 Nov |
| 298-24 Build Model 1 zero-shot baseline | Done | In Progress | `generate_zeroshot.py` is merged and ran on a T4, but on synthetic data, 48 lines, one seed, a 0.5B stand-in. `COMPUTE_BUDGET.md`: "None of it is a reportable result" | 298-53, 3 Nov |
| 298-25 Build Model 2 QLoRA fine-tune | Done | In Progress | `train_qlora.py` is merged with 11 tests and ran 30 steps on a T4 — synthetic, one seed, 0.5B. The recipe calls for 2–3 epochs on the real corpus at three seeds | 298-54, 9 Nov |

## What the reset costs, and why it is still right

Returning these eight to the open column moved **33 story points** of unfinished work back
into Cycle 3, taking it from 14 issues and 43 points to 22 issues and 77 points. The board
now shows a cycle that will visibly miss its scope.

That is the correct outcome. The alternative was a Part C table that counted four of these
eight inside this reporting window and a Part A that contradicted it. A cycle that misses
scope is a scheduling fact; a board that reports finished work which does not exist is a
reporting failure, and it is the failure this project was already marked down for once.

## One issue moved the other way

**298-47** (Part B minutes) was `In Progress` with its artifact already merged — the commit
said `Refs 298-47` rather than `Closes`, so Linear never closed it. `docs/minutes/2026-10-08.md`
and `docs/minutes/2026-10-22.md` are on `main` via PR #29, so it was set to Done.

**298-50** (assemble and submit `T2.A5.docx`) stays open deliberately. The document is
assembled, but the issue is to *submit* it to Canvas, and that has not happened.

## Rule for the future

Write `Closes 298-NN` in the commit that lands the artifact, not `Refs`, so the board moves
when the work does. Where an issue cannot be closed by a commit — a submission, a written
confirmation from a third party — the owner states in a comment what the closing evidence
will be before the issue is picked up.
