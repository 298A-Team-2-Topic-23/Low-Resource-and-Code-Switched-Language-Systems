# Sarvesh — Workbook 1 brief

**Your issues: 298-36, 298-39. 13 points.**

| Issue | What | Est | Due |
|---|---|---|---|
| [298-36](https://linear.app/298a-team-2-topic-23/issue/298-36) | §2.2 Project Management Plan, all eight subsections | 8 | 6 Oct |
| [298-39](https://linear.app/298a-team-2-topic-23/issue/298-39) | EDA figures + the spelling-variance evidence table | 5 | 6 Oct |

You also speak in the demo — stage 4, EDA. See [DEMO_RUNBOOK.md](../DEMO_RUNBOOK.md).

Read [README.md](README.md) for setup and the PR workflow before you start.

---

## 298-39 — EDA figures and the spelling-variance table

This one depends on Yash landing the pipeline (298-38). The code already exists in
`src/lrcs/analysis/eda.py`; your job is to run it, check the output, and make the
figures presentable.

```bash
PYTHONPATH=src python scripts/run_pipeline.py --synthetic --n-synthetic 1200
```

Four figures land in `reports/figures/`:

```
fig_length_distribution.png
fig_token_composition.png
fig_cmi_distribution.png
fig_length_ratio.png
```

**Every figure caption must name the script that produced it.** No hand-made charts.

### The spelling-variance table is the important part

This is the first direct evidence for the project hypothesis. On a 1,091-row
synthetic run it already produces:

```
spelling variance observed (evidence for the hypothesis):
  nahin    3 surface forms  [nahi=14, nahin=100, nhi=11]
  accha    3 surface forms  [accha=42, acha=33, achha=41]
  bahut    3 surface forms  [bahut=42, bhut=41, bohot=33]
  theek    3 surface forms  [theek=171, thik=19, thk=12]
  mujhe    1 surface forms  [mujhe=211]
```

That is the claim in one table: one word, several surface forms, and the tokenizer
treats each as unrelated vocabulary.

Connect it to work you already merged. `analysis/spelling_variants.tsv` holds the
v1 lexicon — 72 groups, 227 attested surface forms — and
`analysis/tokenizer_fertility.py` computes `spelling_variant_burden`, which measures
what those variants cost in tokens. On a smoke run that burden came out at **1.83**,
well above the 1.0 floor. The EDA table shows the variants *exist in the corpus*;
the burden metric shows they *cost us*. Say both.

Also report type-token ratio, hapax fraction and code-switched fraction — they come
out of the same run.

### What to say in the demo

> *"Type-token ratio, length distributions, code-switched fraction, mean CMI, four
> figures — all from this run, none hand-made. And here is the direct evidence for
> our hypothesis: theek appears as theek, thik and thk. One word, several surface
> forms, and the tokenizer treats each as unrelated vocabulary."*

---

## 298-36 — §2.2 Project Management Plan, all eight subsections

Rubric: 1 pt for 2.2 Development Methodology plus 1 pt for 2.3 Organization Plan.
**Each of 2.2.1 to 2.2.8 needs its own heading and its own paragraph.** A grader
looking for eight headings and finding five scores it incomplete.

There is a draft at [`docs/project_management_plan.md`](../project_management_plan.md)
(Jenil's, merged). It covers all eight headings but runs 44 lines — it is a skeleton.
Expand it; do not start over.

| § | Needs |
|---|---|
| 2.2.1 | Stakeholder analysis — **who decides differently, and what decision changes** |
| 2.2.2 | Business requirements with the numeric criteria |
| 2.2.3 | The intelligent-system life cycle **and** the actual Linear setup |
| 2.2.4 | WBS table: owner, deliverable, **Linear issue ID** |
| 2.2.5 | In scope, out of scope, and the priority order when they conflict |
| 2.2.6 | Risk register: likelihood, impact, trigger, mitigation, owner |
| 2.2.7 | Meeting cadence and how instructor feedback is tracked to closure |
| 2.2.8 | Evidence the plan is applied — **including what is NOT yet in place** |

### 2.2.4 — use the real issue IDs

The WBS table is where the document and the board meet. Use the actual numbers:

| Deliverable | Owner | Issue |
|---|---|---|
| §1.1 Background | Jenil | 298-32 |
| §1.2 Requirements | Shibin | 298-33 |
| §1.4/1.5 Surveys | Yash | 298-34 |
| §2.1 Data Management | Yash | 298-35 |
| §2.2 PMP | Sarvesh | 298-36 |
| §2.3/2.4 Resources, schedule | Prakhar | 298-37 |
| Data pipeline | Yash | 298-38 |
| EDA figures | Sarvesh | 298-39 |
| Demo rehearsal | Prakhar | 298-40 |
| References, checklist | Shibin | 298-41 |
| Assembly and submission | Jenil | 298-42 |
| Minutes | Jenil | 298-43 |

Note `PLAN.md` refers to 298-50…298-61. Those numbers do not exist — the board
had reached 298-31, so these were created as 298-32…298-43. **Subtract 18.** Use
the real ones here.

### 2.2.6 — the risk register must be honest

Real, current risks, not comfortable ones:

| Risk | Trigger | Mitigation | Owner |
|---|---|---|---|
| Splits not derived — PR #4 closed unmerged | no `scripts/make_splits.py` on main | re-open and land 298-11 | Yash |
| Backbone identifier unverified | no model card checked | verify before it enters any document | Sarvesh |
| Board claims Done for work not in the repo | ISA checks both on 8 Oct | reconcile statuses before the demo | all |
| Reference count unreconciled, 4,799 vs 4,803 | measured ≠ published | recount from Table 1 | Yash |
| Normalised chrF++ near-inert | regex collapses 3/72 lexicon groups | 298-23 lexicon-based rewrite | Shibin |

### 2.2.8 — this is where marks are won

The rubric wants evidence the plan is *applied*, and §2.5 is graded on **accuracy**.
A team that rates every row excellent and is found to have gaps scores worse than a
team that finds its own. So state plainly what is not in place:

- `main` has **no branch protection** — verified, the API returns 404
- **no PR has ever received an approving review**; two were self-merged
- PR #6 merged with an **empty body**, so it links to no Linear issue
- several issues are marked Done with no corresponding file on main

Then say what is being done about each, with an owner and a date. That reads as
control. Claiming the opposite reads as a team that has not looked.
