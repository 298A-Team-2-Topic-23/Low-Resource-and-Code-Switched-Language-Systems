# Progress Report 2 — Part A: Project Status

Linear **298-46**. Owner: Sarvesh. Reporting period: Cycles 2 and 3, 25 September to
22 October 2026.

Every percentage below was checked against `main` at commit `b480fa6` rather than against
intention. Where the repository and the board disagree, the repository wins.

| Item | Planning | Investigation | Complete | Document |
|---|---|---|---|---|
| **1 Introduction** | | | | |
| 1.1 Project Background and Executive Summary | 100% | 95% | 95% | 95% |
| 1.2 Project Requirements | 100% | 95% | 95% | 95% |
| 1.3 Project Deliverables | 100% | 90% | 85% | 85% |
| 1.4 Technology and Solution Survey | 100% | 95% | 95% | 95% |
| 1.5 Literature Survey of Existing Research | 100% | 95% | 95% | 95% |
| **2 Data and Project Management Plan** | | | | |
| 2.1 Data Management Plan | 100% | 90% | 90% | 85% |
| 2.2 Project Management Plan (2.2.1–2.2.8) | 100% | 95% | 90% | 95% |
| 2.3 Project Resource Requirements and Plan | 100% | 85% | 60% | 90% |
| 2.4 Project Schedule | 100% | 90% | 85% | 90% |
| **3 Data Engineering** | | | | |
| 3.1 Data Process | 100% | 95% | 95% | 35% |
| 3.2 Data Collection | 100% | 95% | 95% | 40% |
| 3.3 Data Pre-processing | 100% | 95% | 95% | 35% |
| 3.4 Data Transformation | 100% | 90% | 90% | 35% |
| 3.5 Data Preparation | 100% | 95% | 95% | 40% |
| 3.6 Data Statistics | 100% | 95% | 95% | 50% |
| **4 Model Development** | | | | |
| 4.1 Model Proposals | 100% | 90% | 85% | 90% |
| 4.2 Model Supports | 90% | 70% | 55% | 40% |
| 4.3 Model Comparison and Justification | 100% | 85% | 70% | 85% |
| 4.4 Model Evaluation Methods | 100% | 90% | 85% | 85% |
| 4.5 First Model Implementation | 85% | 60% | 25% | 20% |
| 4.6 Baseline Reproduction | 80% | 55% | 10% | 20% |
| **5 Prototype and System Implementation** | 60% | 25% | 5% | 5% |
| **6 Benchmarking, Evaluation, and Failure Study** | 55% | 30% | 15% | 10% |
| **7 Reproducibility** | 100% | 90% | 85% | 60% |
| **8 298B Plan** | 55% | 25% | 10% | 5% |
| **References** | 100% | 90% | 95% | 95% |

---

## Explanation for the large gaps

**Rows 3.1 to 3.6 — Data Engineering. Complete is 90–95%, Document is 35–50%, a gap of
45 to 60 points on every row.**

This is the one place in the project where the engineering has run ahead of the writing,
and the reason is scheduling rather than neglect. The four-stage pipeline is merged
(`scripts/run_pipeline.py`, `src/lrcs/`), has been run end to end on the real HinGE corpus
in 11.96 seconds, and its outputs are committed: `reports/data_statistics.json`,
`data/processed/manifests/hinge_split_manifest.json`, the four EDA figures under
`reports/figures/`, two run records under `runs/`, and a 48-cell demonstration notebook.
The test suite covering it reports 27 passing tests.

What does not exist is the Section 3 prose. Sections 3.1 to 3.6 belong to Workbook 2, which
is due 11 November, and the writing is filed as **298-57** with a 6 November date. Writing
it now would mean writing Workbook 2 content into a progress report.

The numbers that section will carry are already measured and committed, so this is a
documentation lag against a known date, not unfinished work:

- 1,976 source rows yielding 4,799 human references, measured off the file against 4,803
  reported in the source paper
- six cleaning filters removing 125 records, each removal charged to the filter that
  rejected it, leaving 4,674
- 1,938 unique sources grouped into 1,937 near-duplicate clusters
- splits of 3,738 / 468 / 468 with zero exact and zero near-duplicate overlaps across all
  split pairs
- CMI 25.3, Switch-Point Fraction 0.240, M-index 0.693, 86.1% of sentences code-mixed,
  at 68.2% tagger coverage

**No other row differs by more than 40 points.** Row 2.3 runs the other way — Document 90%
against Complete 60% — because the resource plan is fully written while the GPU allocation
it depends on is still unconfirmed. That is a 30-point difference and is tracked as a
blocker in Part D rather than as a documentation gap.

---

## Rows that are deliberately low

Three rows would be easy to overstate, and are not.

**4.5 First Model Implementation, Complete 25%.** `models/generate_zeroshot.py` is merged
and its CPU paths are tested, but **no model has been trained and no generation run has
been scored**. `runs/` contains two pipeline records and no model records. Issue 298-24 was
previously marked Done without an artifact and is being reset; the scored run is 298-53,
due 3 November, and the QLoRA fine-tune is 298-54, due 9 November. Both are blocked on GPU
confirmation (298-51).

**4.6 Baseline Reproduction, Complete 10%.** The target is fixed and justified — Gahoi et
al. (2022), Table 2, ROUGE-L 0.617 — and `evaluation/run_eval.py --check-baseline` enforces
the 0.01 tolerance. But the reproduction has not been run, and the authors released no
code, so the mBART recipe is being rebuilt from the paper description. That work is 298-52,
due 7 November.

**5 Prototype and System Implementation, Complete 5%.** Nothing is deployed. The serving
stack is chosen and the requirements carry a numeric latency target, but Team Meeting 2 on
12 November requires a live prototype and there is none today. That is 298-56.

---

## Method

Percentages were assigned against four questions, applied row by row:

- **Planning** — is the approach decided and recorded somewhere a reader can check?
- **Investigation** — has the reading and experimentation behind it been done?
- **Complete** — does the artifact exist on `main` and run?
- **Document** — is the report prose for that section written?

A row was only marked above 80% on Complete if an artifact exists on `main` that a reader
can open. Issues marked Done on the Linear board without a corresponding artifact were
treated as incomplete; those six are being reset under 298-45, so that Part C and this
table agree with each other and with the repository.
