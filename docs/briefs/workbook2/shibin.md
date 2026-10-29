# Shibin Biji Thomas Lnu — Workbook 2

Two issues, 6 points, covering **three of the twelve rubric points**. One of them has a hard
date that matters more than its size.

| Linear | Task | Points | Due | Rubric |
|---|---|---|---|---|
| **298-68** | Section 4.4 Model Evaluation Methods — commit the metrics | 3 | **1 Nov** | 4.4 — 1 pt |
| 298-63 | Sections 3.3 Pre-processing and 3.4 Transformation | 3 | 5 Nov | 3.3, 3.4 — 2 pts |

Also still open from the previous period: **298-52** baseline reproduction (8, due 7 Nov),
**298-59** bootstrap + lexicon normalisation (5, due 2 Nov), **298-23** normalised chrF++
(3, In Progress).

---

## 298-68 — the date is the point, not the size

Template 5 is unusually strict here:

> "metrics are committed here, **before you have results**. Use the metrics named on your topic
> slide unless you can argue for better ones. **Do not revise this section after seeing results.**"

**298-53 produces the first real scored run on 3 November.** If 4.4 merges after that, the
commitment is worthless and provably so — the git log shows which came first. 1 November gives
two days of slack. This is why a 3-point issue is due before the 5-point ones.

Yours because you own the harness (298-14) and 298-59.

The table, with real dates traceable to commits:

| Metric | Why | Measured on | Committed on |
|---|---|---|---|
| chrF++ (primary) | character n-gram F with word_order=2; robust to the spelling variance under study, where BLEU's exact word matching is not | 800-item gold set; HinGE test split as interim | Workbook 1, merged 7 Oct |
| Normalised chrF++ | the **divergence** from raw chrF++ measures how much error is orthographic rather than semantic | same | Workbook 1, 7 Oct |
| ROUGE-L | the baseline's own metric; required for the reproduction gate | MixMT Subtask-1, 500 sentences | Workbook 1, 7 Oct |
| WER | the baseline's second metric | MixMT Subtask-1 | Workbook 1, 7 Oct |
| BLEU | secondary, for comparability with prior work; not decisive | test split | Workbook 1, 7 Oct |
| CS penalty | chrF++ on monolingual minus chrF++ on code-switched; the three-column gold set makes it measurable | 800-item gold set | Workbook 1, 7 Oct |

Cite `docs/workbook1/section_1_2.md` and its commit rather than backdating anything. Date
anything newly named here as today.

Also state the method, not just the list: three seeds minimum with error bars; 1,000-sample
bootstrap intervals; the `--check-baseline` gate enforcing 0.01 ROUGE-L against Gahoi et al.
Table 2's 0.617; no tuning on test, splits frozen under SHA-256.

**Two things to state as pending rather than imply they exist:**

- Bootstrap resampling is **not implemented**. It is 298-59, due 2 November. Workbook 1's
  requirements commit to it, so name it as committed method with its issue number.
- `tokenise()` in `evaluation/run_eval.py` is built on `normalise()`, so **ROUGE-L and WER are
  currently computed on normalised tokens** — a different tokenisation from the paper's. You
  found this; it is blocker 4 in Progress Report 2's Part D. Describe the intended method and
  note the gap with its issue, rather than describing a harness we do not have.

Close with a line saying the section will not be revised after results, so a reader can check
the git log against it. That sentence is cheap and it is exactly what the template is testing.

---

## 298-63 — sections 3.3 and 3.4

Yours because you ran the pipeline on the real HinGE corpus (298-44) and converted the source
pickle, so you know what cleaning actually does to the data. Depends on **298-62** for samples;
write the prose in parallel and drop them in.

### 3.3 Data Pre-processing

Needs **before/after samples and how many rows each rule removed**. The counts are committed in
`reports/data_statistics.json` → `attrition`: 4,799 ingested, 125 removed, 4,674 kept, with
`attrition.table` giving six rows of per-filter breakdown. Every removal is charged to the filter
that rejected it, so the six sum to 125 — **say so**, because otherwise a reader cannot tell
whether a record rejected by two rules was double-counted.

Justify each threshold rather than listing it. From `params.clean`:

| Parameter | Value | Argue |
|---|---|---|
| `min_words` | 2 | why a one-word reference is not usable supervision |
| `max_words` | 60 | why, and what it costs in coverage |
| `max_ratio` | 3.0 | source-to-target length ratio; what a 3× divergence indicates |
| `max_devanagari` | 0.2 | the task output is Romanised, so a mostly-Devanagari reference is mislabelled |

The validation tooling is the test suite plus the leakage gate — 38 tests pass. Cite the test
files rather than asserting correctness.

### 3.4 Data Transformation

Needs **a reason for each transformation**, with samples. Cover:

- pickle → CSV (`scripts/convert_hinge_pkl.py`), and why loading the pickle directly was
  rejected as unsafe
- Unicode NFC normalisation and whitespace handling in `src/lrcs/text.py`
- the one-row-per-reference expansion turning 1,976 source rows into 4,799 records
- the TSV layout the model scripts consume: `id, group, english, hindi, hinglish`

**Get this right:** normalisation is applied to **the metric only**, never to training data or
gold references, because orthographic variance is the phenomenon under study.
`evaluation/run_eval.py` carries that warning in a comment. If 3.4 reads as though the corpus is
normalised, the whole hypothesis looks incoherent — and this is the section a grader would catch
it in.
