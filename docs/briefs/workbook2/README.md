# Workbook 2 (Assignment 6) — work split

**Due 11 November 2026, 11:59 pm Pacific. File name `T2.A6.docx`. 12 points, three Canvas attempts.**

Workbook 2 *is* report sections 3 and 4. Template 5 governs the structure: sections 1 and 2 are
not rewritten, and anything revised since Workbook 1 goes in the carry-forward table.

One brief per member in this directory. Each lists your Linear issues with IDs, what the rubric
actually asks for, and what already exists in the repository so nobody re-derives a number that
is already committed.

## How the 12 points break down

| Rubric line | Pts | Issue | Owner |
|---|---|---|---|
| 3.1 Data Process | 1 | 298-57 | Shevkar |
| 3.2 Data Collection | 1 | 298-57 | Shevkar |
| 3.3 Data Pre-processing | 1 | 298-63 | Thomas Lnu |
| 3.4 Data Transformation | 1 | 298-63 | Thomas Lnu |
| 3.5 Data Preparation | 1 | 298-64 | Shevkar |
| 3.6 Data Statistics | 1 | 298-65 | Waghmare |
| 4.1 Model Proposals | 1 | 298-66 | Savalia |
| 4.2 Model Supports | 1 | 298-67 | Singh |
| 4.3 Model Comparison | 1 | 298-69 | Shevkar |
| 4.4 Model Evaluation Methods | 1 | 298-68 | Thomas Lnu |
| **4.5 Data Pipeline Demo** | **2** | **298-70** | **Shevkar** |
| Assembly, references, checklist, self-assessment | — | 298-71 | Savalia |

Supporting: 298-62 emits the stage samples that four of those rubric lines require.

## Three things that decide the grade

**1. 298-70 is worth two points and we cannot currently do it.** The rubric's 4.5 asks for a
demo "from source to **data warehouse**", plus pipeline **monitoring and management**. Our
pipeline ends in local files. There is no queryable store and nothing that reports drift or
stage latency. This is the only build-heavy item on the list, it is worth double any section,
and it has a live demo attached on 12 November. Start it first.

**2. 298-62 blocks four rubric lines.** Sections 3.2, 3.3, 3.4 and 3.5 each demand "present
sufficient samples". Nothing in the repository emits sample records today. Until that script
lands, four sections cannot be finished. Due 2 November for that reason.

**3. 298-68 must merge before 3 November.** The template says metrics are committed "before you
have results" and must not be revised afterwards. 298-53 produces the first scored run on
3 November, and the git history shows which came first. A metrics section merged after results
exist is provably not a commitment.

## One rubric trap worth knowing

4.1 Model Proposals gives the top band for "**5 or more** models", and only Good for three or
more. Template 5 asks for four models plus the baseline. **Four alone caps 4.1 at 0.8.** We
legitimately have six configurations, because Control A (CPT without vocabulary extension) and
Control B (M2 at M3's GPU-hours) are already mandatory under the project's own design — without
them an M3 gain cannot be attributed. List all six and keep the baseline on its own row, marked
as not one of the four.

## Load, stated honestly

Cycle 4 runs 26 October to 9 November — Workbook 2 is due two days after it closes. With these
ten issues added, the cycle holds roughly 135 story points, which five people cannot deliver in
twelve days.

About 29 of those points are duplicates left over from the 22 October board reset, and should be
taken out of the cycle rather than worked:

| Issue | Pts | Superseded by |
|---|---|---|
| 298-24, 298-25 | 8 | 298-53, 298-54 |
| 298-15, 298-16 | 8 | 298-52 |
| 298-21 | 8 | 298-55 |
| 298-17 | 5 | 298B work; overdue since 14 October |

That leaves about 106 points, roughly 21 each. Still tight. If something has to give, it should
be a named decision at the next meeting, not a section quietly left thin — the self-assessment
and gap register in 298-71 is where an honest shortfall belongs, and it costs fewer marks than
a section that overstates.

## Rules that apply to every section

- Write report prose, not notes. The template says so and the rubric bands turn on "clearly".
- Every number names the committed file it came from. Do not re-derive figures by hand.
- Every claim links to a commit, run, dataset version or Linear issue — it is a checklist row.
- Each section names the member who wrote it.
- Commit your section as Markdown under `docs/workbook2/`, then 298-71 builds the `.docx`.
- Use `Closes 298-NN` in the commit that lands the artifact, not `Refs`, so the board moves
  when the work does.
- Get one non-author review before merging. Of the 23 pull requests merged in the last
  reporting period, zero carried a review and 19 were self-merged. That is the first blocker in
  Progress Report 2's Part D and 298-60 is still open.
