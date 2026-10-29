# Sarvesh Waghmare — Workbook 2

Two issues, 10 points. One of them blocks four other rubric lines, so it goes first.

| Linear | Task | Points | Due | Rubric |
|---|---|---|---|---|
| **298-62** | Emit committed stage samples for sections 3.2 to 3.5 | 5 | **2 Nov** | unblocks 3.2–3.5 — 4 pts |
| 298-65 | Section 3.6 Data Statistics: stage table, imbalance and correlation plots, coverage gap | 5 | 6 Nov | 3.6 — 1 pt |

Also carried over: **298-53** M1 on three seeds (5, due 3 Nov), **298-54** M2 QLoRA on three
seeds (8, due 9 Nov) — both blocked on the GPU allocation (298-51).

---

## 298-62 — do this first, four sections are waiting on it

Four rubric lines — 3.2, 3.3, 3.4 and 3.5, a third of the total — each say "present sufficient
samples ... in a very good format". **Nothing in the repository emits sample records.**
`grep -rln sample --include='*.py' src scripts` matches only `scripts/build_report.py`, which is
the report builder. Yash, Shibin and I are all blocked on this, which is why it is due before
every section issue.

Build `scripts/emit_stage_samples.py`, writing committed artifacts under `reports/samples/`:

| Stage | Artifact | Must show |
|---|---|---|
| Raw | `raw.md` | records as ingested, source row id, all three columns |
| Pre-processed | `preprocessed.md` | **before/after for each of the six cleaning filters** |
| Transformed | `transformed.md` | each transformation, input and output side by side |
| Prepared | `prepared.md` | train, dev and test samples, labelled by split |

Rules:

- **Deterministic** under the pipeline seed, so a reviewer can regenerate them. No hand-picking.
- **Include the awkward rows.** A sample set showing only clean records misrepresents the data,
  and a grader reading the attrition table alongside it will notice.
- Devanagari and Roman must both render — set the encoding explicitly.
- Six to ten records per stage is "sufficient"; more is noise.

`reports/data_statistics.json` → `attrition.table` already holds six rows of per-filter removal
counts summing to 125 of 4,799. The counts exist; the **examples** do not. Pair each filter with
one record it rejected and the reason — section 3.3 needs both.

Acceptance: script runs from a clean clone, deterministic, all four stage artifacts committed,
per-filter before/after present, prepared samples labelled, plus a test asserting two runs at the
same seed produce identical output. Respect the `.gitignore` rules in `docs/datasheet.md` — only
the sample files get committed, not raw or processed data.

---

## 298-65 — section 3.6

Three things, and two of them do not exist yet.

### 1. The stage table is incomplete

The template wants rows **and columns** per stage. The statistics JSON has row counts but no
column counts:

| Stage | Rows | Columns | Notes |
|---|---|---|---|
| Raw | 1,976 file rows / 4,799 records | 3 | one row per source sentence, three reference columns |
| Pre-processed | 4,674 | ? | 125 removed by six filters |
| Transformed | 4,674 | ? | expanded to one row per reference |
| Prepared | 3,738 / 468 / 468 | ? | grouped split, frozen under SHA-256 |

Add column counts to the statistics output so the table is **generated**, not hand-filled. And
explain the 1,976-versus-4,799 distinction in the Notes column — a reader watching rows go 4,799
→ 4,674 → 3,738 needs to know the first is references, not sentences.

### 2. Missing plots

The rubric asks for "distribution, **imbalance** and **correlation** plots". What is committed —
sentence lengths, CMI distribution, switch-point fraction, spelling variants — is all
**distribution**. Still needed:

- **Imbalance** — references per source sentence is uneven (4,799 over 1,976, with group sizes
  capped by `max_group_frac` 0.05). Plot references-per-source and group-size distributions, and
  say what the imbalance means for training.
- **Correlation** — at least one real correlation view. Candidates: CMI against sentence length,
  switch-point fraction against CMI, fertility against spelling-variant count per sentence.
  **Report what you find, including a null or weak result.** A flat scatter is a finding;
  inventing a relationship is not.

Extend `scripts/charts.py` so both regenerate, and commit the figures.

### 3. Coverage gap — explicitly required, and nothing in the repo addresses it

> "name any population or coverage gap in the data, and who it would disadvantage if the system
> were deployed"

Real gaps, all defensible from committed figures:

- HinGE is Hindi–English only. Tamil, Bengali, Marathi and Punjabi code-switching have the same
  problem and would not be served — large speaker populations, no coverage.
- The tagger covers **68.2%** of tokens, so 31.8% of code-mixing measurement is unverified, and
  coverage is likely worst for rarer spellings. The measurement is weakest exactly where the
  hypothesis matters most.
- **86.1%** of sentences are code-mixed, so monolingual Hindi and monolingual English inputs are
  under-represented — a deployed system would be least tested on the simplest inputs.
- HinGE's source text is formal and literary register. Conversational, abbreviated,
  transliteration-heavy social usage is absent, and that is where real Hinglish lives.
- No speaker demographics recorded, so regional and age-linked spelling conventions cannot be
  checked for representation.

Name who each gap disadvantages. Write it as an honest limitation, not a disclaimer paragraph.

---

## A note on the carried-over model work

298-53 and 298-54 are the first real results and both sit behind the GPU allocation, which has
been unconfirmed since 26 September. 298-53 is due **3 November** — the same window as Shibin's
298-68, which must commit the metrics *before* those results exist. If 298-53 lands early,
298-68 has to be merged first or the metric commitment is void. Worth a word with Shibin and
Prakhar rather than discovering it in the git log.
