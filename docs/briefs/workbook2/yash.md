# Yash Shevkar — Workbook 2

Four issues, 19 points, covering **four of the twelve rubric points**. You own the pipeline, so
Workbook 2's data engineering is mostly yours.

| Linear | Task | Points | Due | Rubric |
|---|---|---|---|---|
| **298-70** | Data warehouse + pipeline monitoring, for the source-to-warehouse demo | 8 | **8 Nov** | **4.5 Data Pipeline Demo — 2 pts** |
| 298-57 | Sections 3.1 Data Process and 3.2 Data Collection | 5 | 4 Nov | 3.1, 3.2 — 2 pts |
| 298-64 | Section 3.5 Data Preparation, with the split and leakage table | 3 | 5 Nov | 3.5 — 1 pt |
| 298-69 | Section 4.3 Model Comparison and Justification | 3 | 6 Nov | 4.3 — 1 pt |

Also still open from the previous period: **298-58** back-translation contamination check, 5 points, due 9 Nov.

---

## 298-70 — start here, it is worth two points

The rubric's 4.5 is not the template's 4.5. It reads: *data ingestion, data transformation,
**data warehouse**, data pipeline **monitoring and management**,* with full marks for
demonstrating the pipeline *"from source to data warehouse"*.

Ingestion and transformation are done and good — `scripts/run_pipeline.py`, four stages in
`src/lrcs/data/`, SHA-256 provenance, a leakage gate that halts the run, 38 passing tests, a real
HinGE run in 11.96 seconds.

**What does not exist: a warehouse, and any monitoring.** The pipeline terminates in local files.
`common/repro.py` writes a run record, which is provenance, not monitoring — nothing reports
freshness, row-count drift or stage latency.

Four pieces:

1. **Warehouse** — load each stage into a queryable store with a typed schema. DuckDB or SQLite
   is enough and keeps the repo self-contained; document the path to BigQuery or Postgres if
   Prakhar's cloud deployment lands. Tables for raw, pre-processed, transformed, prepared, plus
   the run log. The load must be idempotent.
2. **Demo queries** — five or six SQL queries a viewer can watch run: rows per stage, attrition
   per filter, split sizes with leakage status, CMI distribution, references per source. These
   double as evidence for sections 3.3 to 3.6.
3. **Monitoring** — one command reporting, per run, rows in and out per stage, wall-clock per
   stage, the gate result, and whether counts moved against the previous run beyond a threshold.
   Write it to a committed artifact so drift shows up in git history.
4. **Management** — how a run is scheduled, re-run and rolled back, and what happens when the
   gate fails. A `make`-style entry point and a paragraph beats a diagram of infrastructure we
   do not operate.

**Coordinate with Prakhar on 298-56.** His cloud prototype and this share a deployment, and the
Team Meeting 2 demo on 12 November shows both. If this slips past 8 November there is no time to
rehearse, and a demo that fails live scores worse than one that is simple and works.

---

## 298-57 — sections 3.1 and 3.2

Originally covered all of 3.1 to 3.6; narrowed on 28 October because six rubric points in one
5-point issue cannot be reviewed as a unit.

**3.1 Data Process** — the process and steps of collecting raw data and preparing the splits.
A **pipeline or lineage diagram is explicitly required**. Draw source file → ingest → clean →
group → split → manifest → statistics, with the leakage gate drawn as a gate that stops the run.
Generate it from a committed script so a reader can regenerate it.

**3.2 Data Collection** — sources, parameters, quantity, plus **raw samples** (top band asks for
samples "in a good format"). Figures are committed in `reports/data_statistics.json`:

| Item | Value |
|---|---|
| Source file | `data/raw/hinge.csv`, 1,591,630 bytes |
| SHA-256 | `dcfaf37ca9d7528e27da7be6b0cfffafb8bbe7825fe4da45077b96236cd9c9c3` |
| Rows in file | 1,976 |
| Records extracted | 4,799 (source paper reports 4,803) |
| Column mapping | English, Hindi, Human-generated Hinglish — inferred from header |

Cover the secondary sources already licence-checked in `docs/datasheet.md` (MixMT Subtask-1,
Samanantar, IIT Bombay, Dakshina) with quantities and licences, plus the team-authored 800-item
set as a source we create. State the 4,799 against 4,803 difference — do not smooth it over.

Samples come from **298-62**, due 2 November. Do not hand-copy rows.

---

## 298-64 — section 3.5, and the one cell that needs care

The template requires this table:

| Split | Rows | % of total | Stratified on | Leakage check and result |
|---|---|---|---|---|
| Train | 3,738 | 79.98% | | |
| Validation | 468 | 10.01% | | |
| Test | 468 | 10.01% | | |

**The splits are not stratified.** `src/lrcs/data/splits.py` groups records by near-duplicate
source cluster, shuffles group ids under a seed, then assigns each whole group to whichever split
is furthest below its record target. Assignment is by group, not by any stratum.

Write that plainly and justify it: stratifying by feature while splitting by record would put
paraphrases of the same source sentence on both sides, and leakage is the failure this corpus is
known for. Say what it costs — 79.98 / 10.01 / 10.01 rather than exactly 80/10/10, because whole
groups cannot be divided. **Do not write "stratified on language pair" to fill the cell.** A
justified "not stratified, grouped by source cluster" scores better than an inaccurate entry.

Leakage, from the statistics and manifest:

- 1,938 unique sources in 1,937 clusters; exactly 1 near-duplicate pair merged two sources
- 0 exact and 0 near-duplicate overlaps across every split pair, Jaccard ≥ 0.7, MinHash 96
  permutations, 3 rows per band
- per-split unique sources: train 1,549, dev 192, test 197 — test shows 197 sources in 196
  groups, which is that merged pair. Explain it; do not leave a reader to spot the mismatch.
- the gate **halts and writes no manifest** on failure, demonstrated in
  `reports/rehearsals/2026-10-07/leakage-gate.log` with an injected test source

The template also says splits are **fixed here and version-controlled**. State that they are
frozen as of this workbook and that no tuning on test is permitted, with the manifest hashes in
`data/processed/manifests/hinge_split_manifest.json` as the mechanism.

---

## 298-69 — section 4.3

Yours because you wrote the technology and literature surveys (298-34). **Wait for 298-66** to
settle the model list, then use the same six configurations plus the baseline in the same order.

One row per model: targeted problem, features, approach, strengths, limitations, justification.
The rubric names statistics, machine learning *and* deep learning — ours are all deep learning,
so say that and say why classical ML or statistical approaches were rejected. A grader looking
for three approaches and finding one unexplained reads it as incomplete.

Justify each arm by **what it rules out**, not by expected performance:

| Arm | Isolates |
|---|---|
| M1 | how large the problem is |
| M2 | is it simply missing task supervision? |
| M3 | is it the tokenizer and orthographic variance? |
| M4 | is it scarcity of code-switched text? |
| Control A | CPT without vocabulary extension — vocabulary, or just extra training? |
| Control B | M2 at M3's GPU-hours — method, or just more compute? |

Then the paragraph most teams skip: **under what conditions would our preferred model lose?**
M3 is preferred. It loses if the added tokens are too rare and the embeddings stay undertrained
(M2 wins, Control B reveals it); if the 1.832 burden turns out to be driven by a few
high-frequency groups rather than the long tail; if a small gold set leaves the intervals
overlapping, making the honest answer "no significant difference"; or if CPT without enough
replay causes forgetting, in which case M3 loses to M1 on fluency while winning on fertility.

State that **a null result is an acceptable outcome and the team has pre-committed to reporting
it**. It is in `CLAUDE.md` and it is the strongest thing in the section.
