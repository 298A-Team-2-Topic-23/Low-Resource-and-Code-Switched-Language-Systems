# Prakhar — Progress Report 2 brief

**You are on the critical path twice: once tonight, once for 12 November.**

| Issue | What | Est | Due |
|---|---|---|---|
| [298-45](https://linear.app/298a-team-2-topic-23/issue/298-45) | **Reset falsely-Done issues** — blocks Part C | 2 | **tonight** |
| [298-48](https://linear.app/298a-team-2-topic-23/issue/298-48) | Part C: work completed, reconciled to the board | 2 | **tonight** |
| [298-60](https://linear.app/298a-team-2-topic-23/issue/298-60) | Branch protection + review rotation | 2 | 26 Oct |
| [298-51](https://linear.app/298a-team-2-topic-23/issue/298-51) | **Confirm GPU or fund the fallback** | 2 | 24 Oct |
| [298-56](https://linear.app/298a-team-2-topic-23/issue/298-56) | Thin-slice cloud prototype | 8 | 9 Nov |

---

## 298-45 — do this first, everything waits on it

Six issues say Done with nothing on `main`. Reset each to Todo or In Progress with a
one-line comment saying what is actually missing:

| Issue | Reality |
|---|---|
| 298-21 Gold set | `gold_set.csv` is a header row, **0 of 800** items |
| 298-25 Model 2 QLoRA | no training script or run |
| 298-17 GCM synthetic pipeline | no file on `main` |
| 298-15 / 298-16 Baseline reproduction | no script, no scored run |
| 298-23 Normalised chrF++ | lexicon reaches the pipeline, harness still regex |

Then comment on 298-45 listing the six and their new states, so the correction is itself
evidenced. **Part C is false until this is done.**

## 298-48 — Part C

One row per member: issues genuinely closed this period, labels worked, a key artifact URL
that resolves. Take counts off the board *after* the reset.

State the gap rather than hiding it: **every one of the 23 merged PRs landed on 25
September or 8 October**, and Cycle 3 shows 0 of 13 points closed. The commit history says
this already — the report saying it first is the difference between candour and being caught.

Click every artifact link before submission.

## 298-51 — the GPU, and why it is urgent

Open since **26 September**. It blocks the baseline reproduction, Model 1 and Model 2 —
three of the four things Team Meeting 2 checks on 12 November.

Get a written answer this week: confirmed quota with slot count and card class, or a formal
refusal. **If refused, fund the cloud fallback and run one real training job on it before
November** — discovering it doesn't work on 10 November is the failure mode.

Ask explicitly whether 40GB cards are available. If it is 24GB only, say so immediately:
Model 3 then needs gradient checkpointing or a smaller backbone, and that is a decision for
now, not for week seven.

## 298-60 — the thing we have claimed twice and never done

Branch protection returns **404**. Twenty merged PRs, **zero** with a recorded review, most
merged by their own author. Progress Report 1 claimed both were in place; that was the ISA's
finding against us and it is still open a month later.

Individual contribution is graded off this workflow, so an unreviewed history weakens the
evidence for **every** member, not just the author. Turn on protection requiring one
non-author approval, commit `CONTRIBUTING.md` and `DECISIONS.md`, and make sure the next PR
after yours carries a real approval so the gate is demonstrably working.

## 298-56 — the prototype

Deploy something trivial early, even returning poor output, so the infrastructure path is
proven before the model is good. **The 12 November demo fails on infrastructure, not on
modelling.** FastAPI plus a light web interface on a managed host, request logging with
latency, p95 measured over 200 requests against the 2000 ms requirement, and a runbook so
someone else can redeploy it.
