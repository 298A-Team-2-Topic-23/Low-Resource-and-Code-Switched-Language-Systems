# Jenil — Workbook 1 brief

**Your issues: 298-32, 298-42, 298-43. 8 points.**

| Issue | What | Est | Due |
|---|---|---|---|
| [298-32](https://linear.app/298a-team-2-topic-23/issue/298-32) | §1.1 Background and Executive Summary | 3 | 5 Oct |
| [298-42](https://linear.app/298a-team-2-topic-23/issue/298-42) | **Assemble, sync-audit and submit T2.A4.docx** | 3 | 7 Oct |
| [298-43](https://linear.app/298a-team-2-topic-23/issue/298-43) | Commit minutes for every meeting | 2 | 8 Oct |

298-42 is the last gate before submission — everything else funnels through you.

Read [README.md](README.md) for setup and the PR workflow before you start.

---

## 298-32 — §1.1 Background and Executive Summary

Rubric 1 pt. Three clauses must all appear, in **prose, not notes**:

1. background, needs, importance, target problem, motivations, goals
2. approaches and methods
3. expected contributions and applications

Six paragraphs. It has to paste into the final report under the same heading with
no editing.

### State the hypothesis explicitly

> Quality loss on low-resource and code-switched text is usually blamed on missing
> data, and tokenizer inefficiency on non-Latin script. Hinglish is *already*
> written in Roman script — so if fertility is still high, neither explanation
> covers it. Our claim is **orthographic variance**: `nahi`, `nhi`, `nahii` and
> `nahin` are one word that the tokenizer sees as four unrelated vocabulary entries.

### State the scope, with out-of-scope items named

In: one language pair, one generation task (English → Romanized Hinglish), four
models, one reproduced baseline.

Out: a learned language-ID model for romanised Hinglish (its own research problem);
speech; other language pairs. Naming out-of-scope items is a rubric clause, and it
is also the answer when someone asks why the language tagger is a marker list.

### The four models, as an ablation ladder

| Model | Adds | Isolates |
|---|---|---|
| M1 Zero-shot | nothing | how large the problem is |
| M2 PEFT fine-tune | task supervision | is it just missing task data? |
| M3 Vocab extension + CPT | representation | is it the tokenizer? |
| M4 Augmented | distribution | is it scarcity of code-switched text? |

Say that **a null result is an acceptable outcome and is pre-committed to**. Success
is +3 chrF++ over zero-shot with non-overlapping error bars; under 1 chrF++, or
overlapping bars, is reported as a null. That is a strength, not a hedge.

There is a long draft from the abstract work to pull from — reuse it rather than
starting from a blank page.

---

## 298-43 — minutes

`docs/minutes/YYYY-MM-DD.md`, one per meeting from 29 September to 8 October,
**committed within 24 hours**. The commit timestamp is what makes them verifiable —
back-dating a file does not, because the commit date shows.

Each file: attendees, decisions, **board actions taken in the meeting**, action
items. Every action item must exist as a Linear issue with an assignee and a date.
Post a Linear Project Update after each meeting.

This is worth real marks. Progress Report 1 scored **1/3 on Minutes** because the
grader checked Linear and the repo and found nothing corroborating the report.

---

## 298-42 — assembly and submission

### Order of operations

1. All section PRs merged — chase them, do not wait
2. Assemble into one document in template order
3. Cover page naming **which member wrote which section**
4. Run the pre-submission gate
5. Submit `T2.A4.docx` to Canvas

```bash
make presubmit SINCE=2026-09-29
```

`reports/sync_audit.md` must show **zero blockers**, and it gets committed alongside
the document.

### Then by hand — this is the part that saves you

- click **every** PR link in the document and confirm it is merged
- confirm every closed Linear issue in this window has a linked artifact
- **the one-click test:** take each factual claim and ask whether a grader can
  disprove it by clicking once

### Claims that currently fail the one-click test

Do not let these into the document:

| Claim | Reality |
|---|---|
| Splits are derived / 298-11 done | PR #4 **closed unmerged**; no `scripts/make_splits.py` on main |
| 800-item gold set authored | `data/goldtestset/gold_set.csv` is a header row, **zero data rows** |
| 4,803 human Hinglish references (measured) | **4,799** measured; 4,803 is the published figure. State both |
| Branch protection active, reviews required | `main` is **not protected**; no PR has ever had an approving review |
| Backbone model identifier chosen | unverified against the official model card |
| M2 / GCM / baseline reproduction done | marked Done on the board, no file on main |

Several of these are marked Done in Linear. **The board and the repo disagree, and
the ISA checks both on 8 October.** Reconciling the statuses before Thursday is
worth more than any sentence you could write.

### Cover page

Name the author of each section. It is a rubric item and it is also how individual
contribution gets read:

| Section | Author | Issue |
|---|---|---|
| 1.1 Background | Jenil | 298-32 |
| 1.2 Requirements | Shibin | 298-33 |
| 1.4 / 1.5 Surveys | Yash | 298-34 |
| 2.1 Data Management | Yash | 298-35 |
| 2.2 Project Management | Sarvesh | 298-36 |
| 2.3 / 2.4 Resources, schedule | Prakhar | 298-37 |
| References, checklist, self-assessment | Shibin | 298-41 |

**Note:** `PLAN.md` refers to issues 298-50…298-61. Those numbers do not exist —
the board had reached 298-31, so these were created as **298-32…298-43**. Subtract
18 wherever the plan cites one.
