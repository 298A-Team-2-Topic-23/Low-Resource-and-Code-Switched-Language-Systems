# Phase 3 — Singh, Prakhar

**New: 8 points.** Cycle 5: 298-72, 298-73. Cycle 6: 298-85.
**Still outstanding:** 298-67 (section 4.2, Urgent, due 10 November), 298-60 (branch protection,
overdue since 26 October), 298-51 and 298-10 (GPU allocation, open since 26 September), 298-56.

Your new load is the lightest on the team on purpose: you carry the heaviest outstanding one, and
both new Cycle 5 issues are small and unblock other people. That is the right shape for someone
already behind.

You own infrastructure, which in this phase means you own the thing standing in front of the entire
model ladder.

---

## First: the allocation is the project's critical path

298-10 was raised on 26 September. It has been open **forty-four days**. Behind it sit 298-53,
298-54, 298-74, 298-82 and 298-52 — every model issue on the board, belonging to three different
people.

Your PR #33 (`docs/COMPUTE_ALLOCATION.md`, `docs/COMPUTE_BUDGET.md`) is the right work and it is
still open with no review. It contains the checkpoint dates and the fallback runbook, which is
exactly what the team needs. **It needs merging more than it needs improving.**

If the allocation cannot be confirmed this week, the fallback has to be funded and tested rather
than documented. A runbook nobody has executed is a plan, not a fallback. 298-51's acceptance
criteria already say this.

---

## 298-72 — Resolve the compute-budget conflict
`https://linear.app/298a-team-2-topic-23/issue/298-72`
**2 points · due 11 November · Urgent · blocks 298-74**

`docs/COMPUTE_BUDGET.md` estimates the arms at **177 GPU-hours**:

```
M1 2 + M2 25 + baseline 15 + M3 45 + Control A 20 + Control B 25 + M4 25 + inference 20 = 177
```

Workbook 1 section 2.3 commits to a 130-hour target and a **145-hour hard cap**. That is a 32-hour
overrun, and the carry-forward table records it as `[PENDING: team decision]`.

(The arithmetic above has been checked independently and it does sum to 177. The conflict is real,
not a typo.)

The plan cannot be executed as written. Pick one, in writing:

1. **Raise the cap.** Section 2.3 requires "an explicit documented change to the abstract and logger
   budget" in those words. Name the new number and what it costs at $2/GPU-hour.
2. **Shrink an arm.** M3 at 45 hours is the largest item and the K sweep is why. Cutting it from
   five values to three is the cheapest real saving. Say what the experiment loses.
3. **Drop an arm.** Control A and Control B exist to separate the vocabulary effect from the
   extra-pre-training effect. Dropping either weakens the central claim; dropping both destroys it.
   If a control goes, section 4.3 must be rewritten to stop claiming what the control was there to
   show.

Acceptance: the decision and new arithmetic in `docs/COMPUTE_BUDGET.md` with who agreed to it; the
`[PENDING]` row in the carry-forward table replaced; section 2.3 amended if the cap moves, rather
than left contradicting it.

Two points, and it unblocks an 8-point issue. Nobody should start a 45-hour run against a budget
that is 32 hours overdrawn.

---

## 298-73 — Experiment-run contract: every run writes a run.json
`https://linear.app/298a-team-2-topic-23/issue/298-73`
**3 points · due 14 November · everyone's model work depends on this**

You set up experiment logging under 298-26. The logger currently records **0.112 GPU-hours, all
smoke tests**. When twelve runs start landing, the thing that will sink the results section is not
the training — it is being unable to say which commit, which split manifest and which seed produced
a number in a table.

Define the contract **before** the runs exist, so no run is repeated for want of metadata.

- A helper writing `runs/<model>/<seed>/run.json`: model id, arm, seed, git commit SHA, split
  manifest SHA-256, tokenizer id and vocab size, hyperparameters, timestamps, wall-clock and
  GPU-hours, peak memory, metrics.
- **A dirty-tree guard.** If the working tree is dirty the run records `"dirty": true` plus the SHA
  of `git diff`, so a number can never be silently attributed to a commit that does not contain the
  code that produced it.
- `scripts/run_summary.py` rolling every `run.json` up into hours spent against the cap from 298-72.

Acceptance: a CPU smoke run produces a valid `run.json` and the roll-up reads it; tests cover the
dirty-tree and no-GPU cases (`gpu_hours: 0.0`, not a crash); `docs/COMPUTE_BUDGET.md` points at the
roll-up instead of hand-maintained numbers.

298-83 generates the results table straight from these files. Without the contract, that table is a
set of assertions; with it, every cell has a provenance path.

---

## 298-85 — Rehearse the end-of-term demo twice on a fresh clone
`https://linear.app/298a-team-2-topic-23/issue/298-85`
**3 points · due 1 December**

298-40 did this for Team Meeting 1 and it is the reason that demo worked. Same discipline, one new
problem: the demo now shows model outputs, and the models need a GPU that may not exist.

Rehearse **twice, on a genuinely fresh clone**, `git clone` to last slide, timed, nothing carried
over from a working directory. The failure this catches is the one that always bites — a step that
works because of an untracked file on one machine. `data/raw/` is gitignored and `HinGE.pkl` is not
committed, so the demo either ships a committed fixture or states clearly that it reads a local
corpus the audience does not have.

A scripted fallback for every live step: no GPU → committed pre-generated outputs, labelled as such,
with the `run.json` that produced them; no corpus → committed fixtures, with the script saying which
it used (`scripts/emit_stage_samples.py` and the code-mix fixture already work this way); no network
→ nothing in the demo path downloads anything, verified by rehearsing with networking off.

**The standing risk, named plainly:** if the GPU never arrives, the demo shows a data pipeline, an
evaluation harness, a measured tokenizer problem and a stood-up code-mixing pipeline, with no model
results. That is a demonstrable, honest story and it should be **rehearsed as the primary plan**
rather than improvised as a disappointment on the day.

A rehearsal that finds nothing was probably not done on a clean clone. Log what broke.

---

## 298-60 — branch protection, and why it still matters

Overdue since 26 October. Checked against the GitHub API on 8 November: **35 pull requests have
merged, 0 carry a recorded review**, and branch protection on `main` still returns 404. Most were
merged by their own author. Progress Report 1 claimed both protection and a review rotation were in
place, which was the finding the ISA recorded against the team, and it is still open six weeks
later.

Individual contribution is graded off this workflow, so an unreviewed history weakens the evidence
for every member, not only the author.

Its due date has been moved to **12 November** — after Workbook 2 ships. The honest reason: with the
workbook due on the 11th and four teammates who have not reviewed anything, turning on a
one-approval gate today would block the submission. Enable it on the 12th and say so in the
carry-forward table, rather than leaving it off and unexplained.

If it still is not on by term end, 298-86 records it as never done with the self-merge count as the
evidence of what that cost. That is the honest version.

## Order of work

1. 298-67 — Workbook 2 section 4.2, due the 10th. It is the weakest row in PR2's Part A (Complete
   55%, Document 40%) and it needs three diagrams that do not exist yet.
2. 298-51 / #33 — get the fallback merged and funded, or the allocation confirmed. This blocks three
   other people.
3. 298-72 — two points, unblocks 298-74.
4. 298-73 — before any real run lands.
5. 298-60 on the 12th, then 298-85 in Cycle 6.
