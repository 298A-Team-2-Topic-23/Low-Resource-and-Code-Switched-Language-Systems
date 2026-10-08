# Prakhar — Workbook 1 brief

**Your issues: 298-37, 298-40. 8 points.**

| Issue | What | Est | Due |
|---|---|---|---|
| [298-37](https://linear.app/298a-team-2-topic-23/issue/298-37) | §2.3 / §2.4 resources and schedule | 5 | 6 Oct |
| [298-40](https://linear.app/298a-team-2-topic-23/issue/298-40) | Rehearse the demo twice on a fresh clone | 3 | 7 Oct |

You open the demo. See [DEMO_RUNBOOK.md](../DEMO_RUNBOOK.md).

Read [README.md](README.md) for setup and the PR workflow before you start.

---

## Do this first — it takes ten minutes and it is worth marks

**`main` has no branch protection.** Verified:

```bash
gh api repos/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems/branches/main/protection
# {"message":"Branch not protected","status":"404"}
```

But Progress Report 1 claims twice that it is on — *"protected the default branch"*
and *"branch protection now active with one required non-author review and a
required status check"*. A grader with repo access disproves that in one click.

Related, and equally checkable: **no PR in this repository has ever received an
approving review.** Nine PRs, zero reviews, two self-merged. The workflow section
of the report says reviews are required.

Turn it on: Settings → Branches → Add rule for `main` → require a pull request with
**1 approval**, and dismiss stale approvals. Then make sure the next PR that merges
actually carries a non-author approval — the demo shows a merged PR with its
approval visible, and an empty Reviewers box is the first thing a grader notices.

`CONTRIBUTING.md` is also referenced in the report and does not exist. Either write
it or correct the minutes.

---

## 298-37 — §2.3 resources and §2.4 schedule

### §2.3 — resources

Table with **have/need, cost and justification per row**. Hardware, software, tools,
licences, with specifications.

| Resource | Spec | Have / Need | Cost | Justification |
|---|---|---|---|---|
| GPU | 40GB-class (A100 40GB / L40S) | | | M3 trains the embedding matrix, peaks ~30 GB |
| GPU slots | 3 concurrent, single-GPU jobs | | | jobs are independent, no interconnect needed |
| Compute | ~130 GPU-hours across both semesters | | | four models × three seeds + controls |
| CPU / storage | 64 GB RAM, 500 GB scratch | | | |
| Fallback | Colab Pro+ | | | if the cluster request is refused |

Say explicitly that jobs are single-GPU and independent — clusters reserve
NVLink-connected nodes for multi-GPU work, and saying you do not need them gets
the request queued sooner.

**If only 24GB cards are available, say so now.** M3 would then need gradient
checkpointing or a smaller backbone, and that is a week-7 problem if it surfaces
in week 7.

The compute budget section needs: what we have, what the project needs, how the gap
is closed. The abstract commits to **80–145 GPU-hours**; `common/repro.py --summary`
prints the running total against it:

```bash
python common/repro.py --summary runs/
```

### §2.4 — both charts, and the PERT must show the critical path

The rubric needs a **Gantt and a PERT**. A PERT with boxes but no dependencies and
no critical path does not score.

- **Gantt:** tasks, timeline, owners, deliverable status
- **PERT:** dependencies, earliest/latest times, float, **critical path identified**

Generate both from `scripts/charts.py`, commit them to `reports/figures/`, and
reconcile against the real Linear cycles — **Cycle 2 runs 28 Sep – 12 Oct, Cycle 3
runs 12–26 Oct.** All Workbook 1 work is Cycle 2.

The critical path is real and worth drawing honestly:

```
298-38 pipeline → 298-39 EDA figures → 298-42 assembly → submission
                ↘ 298-40 rehearsal → demo
```

298-38 is the one with no float. Everything else can slip a day; that cannot.

---

## 298-40 — rehearse twice, on a fresh clone

The plan says 5 October and 7 October. Both from a **fresh clone**, timed, on the
**real corpus** — not `--synthetic`.

### Check this before the rehearsal

**The pipeline kit does not run on Python 3.9.** Three modules use
`zip(..., strict=False)`, a 3.10+ signature. On 3.9 it dies at **stage 3, the split
stage** — one of the four graded components — and it fails *after* stages 1 and 2
print, so it looks fine until it isn't. At least one team machine is on 3.9.6.

```bash
python3 --version          # on every machine that might drive the demo
```

Fix if needed (`strict=False` is the default, so this changes nothing):

```bash
grep -rln "strict=False" src/ | xargs sed -i '' 's/, strict=False)/)/g'
```

Then confirm stage 3 prints its manifest lines. I measured a full clean run at
**8.3 seconds**, four stages, four figures, leakage gate passed.

### Rehearsal checklist

- every member speaks — parts are in the runbook
- three browser tabs open **before you walk in**: the merged pipeline PR with a
  **non-author approval visible**, the Linear cycle board filtered by assignee, and
  `reports/data_statistics.json`
- failure plan agreed out loud: synthetic fallback, offline operation, backup laptop
- a screen recording captured as a backup
- two people have it cloned and tested, and you have agreed which laptop is backup

### Failure plan

| If | Then |
|---|---|
| The real corpus will not load | `--synthetic` runs the identical pipeline. **Say so out loud.** |
| Wifi dies | Run locally. Nothing in the pipeline needs the network. |
| A laptop dies | Switch to the agreed backup. |
| The leakage gate halts | **Do not bypass it.** *"The gate caught an overlap and halted the pipeline — that is the gate working."* Then show the manifests. |

---

## One thing to reconcile before the demo

The board says **Done** for several issues with no corresponding file on main —
298-11 splits (PR #4 closed unmerged), 298-21 gold set (the CSV is a header row),
298-25, 298-17, 298-15/16. The ISA checks the board against the repo in the room.

Progress Report 1 scored the bottom band for exactly this. Fix the statuses before
Thursday, not after.
