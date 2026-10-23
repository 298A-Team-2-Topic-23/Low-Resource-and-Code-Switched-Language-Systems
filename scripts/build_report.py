"""Build T2.A5.docx to Template 3, the official department Progress Report format.

Usage:  python scripts/build_report.py [--out reports/progress2/T2.A5.docx]

Template 3 says "keep Parts A and B exactly as they are", so this builds only what the
template defines: the header block, Part A's row set and four percentage columns, Part B's
Section / Achievements / Issues / Recommended Solutions grid, Part C's four columns, and
Part D's four columns followed by three to five next-period outcomes. Nothing else.

It needs no .docx template file, so it runs from a clean clone. Figures come from the
sources under docs/progress2/ and docs/minutes/, all verified against main.
"""
import argparse
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

FONT = "Times New Roman"
ROOT = Path(__file__).resolve().parent.parent

TITLE = ("Low-Resource and Code-Switched Language Systems: An Adaptation and "
         "Evaluation Framework for Hindi–English (Hinglish) Generation")
MEMBERS = ("Savalia, Jenil Sanjaybhai; Shevkar, Yash; Singh, Prakhar Kumar; "
           "Thomas Lnu, Shibin Biji; Waghmare, Sarvesh")
REPO = ("https://github.com/298A-Team-2-Topic-23/"
        "Low-Resource-and-Code-Switched-Language-Systems")
LINEAR = "https://linear.app/298a-team-2-topic-23/team/298/overview"

# ---------------------------------------------------------------------- Part A
# Strings are section-heading rows; tuples are item rows with the four percentages.
PART_A = [
    "1  Introduction",
    ("1.1  Project Background and Executive Summary", 100, 95, 95, 95),
    ("1.2  Project Requirements", 100, 95, 95, 95),
    ("1.3  Project Deliverables", 100, 90, 85, 85),
    ("1.4  Technology and Solution Survey", 100, 95, 95, 95),
    ("1.5  Literature Survey of Existing Research", 100, 95, 95, 95),
    "2  Data and Project Management Plan",
    ("2.1  Data Management Plan", 100, 90, 90, 85),
    ("2.2  Project Management Plan (2.2.1–2.2.8)", 100, 95, 90, 95),
    ("2.3  Project Resource Requirements and Plan", 100, 85, 60, 90),
    ("2.4  Project Schedule", 100, 90, 85, 90),
    "3  Data Engineering",
    ("3.1  Data Process", 100, 95, 95, 35),
    ("3.2  Data Collection", 100, 95, 95, 40),
    ("3.3  Data Pre-processing", 100, 95, 95, 35),
    ("3.4  Data Transformation", 100, 90, 90, 35),
    ("3.5  Data Preparation", 100, 95, 95, 40),
    ("3.6  Data Statistics", 100, 95, 95, 50),
    "4  Model Development",
    ("4.1  Model Proposals", 100, 90, 85, 90),
    ("4.2  Model Supports", 90, 70, 55, 40),
    ("4.3  Model Comparison and Justification", 100, 85, 70, 85),
    ("4.4  Model Evaluation Methods", 100, 90, 85, 85),
    ("4.5  First Model Implementation", 85, 60, 25, 20),
    ("4.6  Baseline Reproduction", 80, 55, 10, 20),
    ("5  Prototype and System Implementation", 60, 25, 5, 5),
    ("6  Benchmarking, Evaluation, and Failure Study", 55, 30, 15, 10),
    ("7  Reproducibility", 100, 90, 85, 60),
    ("8  298B Plan", 55, 25, 10, 5),
    ("References", 100, 90, 95, 95),
]

GAP_EXPLANATION = [
    "Rows 3.1 to 3.6, Data Engineering. Complete is 90 to 95% and Document is 35 to 50% "
    "on every row, a gap of 45 to 60 points. The engineering has run ahead of the writing, "
    "and the reason is scheduling rather than neglect. The four-stage pipeline "
    "(scripts/run_pipeline.py, src/lrcs/) is merged, has been run end to end on the real "
    "HinGE corpus in 11.96 seconds, and its outputs are committed: "
    "reports/data_statistics.json, data/processed/manifests/hinge_split_manifest.json, "
    "four EDA figures under reports/figures/, two run records under runs/, and a "
    "demonstration notebook. The test suite covering it reports 38 passing tests.",

    "What does not exist is the Section 3 prose. Sections 3.1 to 3.6 belong to Workbook 2, "
    "due 11 November, and that writing is filed as Linear 298-57 with a 6 November date and "
    "an owner. Writing it now would put Workbook 2 content into a progress report. The "
    "numbers those sections will carry are already measured and committed, so this is a "
    "documentation lag against a known date rather than unfinished work:",
]

GAP_BULLETS = [
    "1,976 source rows yielding 4,799 human references, measured off the file against "
    "4,803 reported in the source paper; both figures are recorded and the four-reference "
    "difference is open rather than hidden",
    "six cleaning filters removing 125 records, each removal charged to the filter that "
    "rejected it, leaving 4,674",
    "1,938 unique sources grouped into 1,937 near-duplicate clusters, with splits of "
    "3,738 / 468 / 468 committed under SHA-256 hashes",
    "zero exact and zero near-duplicate overlaps at Jaccard 0.7 or above across every "
    "split pair, enforced by a leakage gate that halts the run rather than warning",
    "CMI 25.3, Switch-Point Fraction 0.240, M-index 0.693, and 86.1% of sentences "
    "code-mixed at 68.2% tagger coverage",
    "tokenizer fertility rising from 1.024 on English to 1.501 on Hinglish, vocabulary "
    "coverage falling from 98.5% to 52.6%, and a spelling-variant burden of 1.832 against "
    "a floor of 1.0",
]

GAP_CLOSING = [
    "No other row differs by more than 40 points. Row 2.3 runs the other way, Document 90% "
    "against Complete 60%, because the resource plan is fully written while the GPU "
    "allocation it depends on is still unconfirmed. That is a 30-point difference and is "
    "carried in Part D as a blocker rather than as a documentation gap.",

    "Three rows are deliberately low and would be easy to overstate. Row 4.5 is at 25% "
    "because, although both model scripts are merged and were executed on a GPU on "
    "22 October, those runs are a single-seed smoke test on synthetic data with a 0.5B "
    "stand-in model and docs/COMPUTE_BUDGET.md states in terms that none of it is a "
    "reportable result. Row 4.6 is at 10% because the published baseline has no code "
    "release and the reproduction has not been run. Row 5 is at 5% because nothing is "
    "deployed. Every percentage above was checked against an artifact on the main branch; "
    "where the repository and the Linear board disagreed, the repository was taken as "
    "authoritative and eight issues were reset accordingly under 298-45.",
]

# ---------------------------------------------------------------------- Part B
MEETINGS = [
    {
        "when": "6:00 pm to 8:30 pm on 10/08/2026",
        "where": "On campus / Team Meeting 1, graded checkpoint session",
        "who": "Savalia, Shevkar, Singh, Thomas Lnu, Waghmare (all five); "
               "the instructor and the ISA",
        "rows": [
            ("1.4",
             ["Resolved from Progress Report 1: the technology survey now resolves every "
              "model identifier against its official Hugging Face model card and gives "
              "the command to repeat the check, closing the earlier issue of a draft "
              "naming a configuration that does not exist"],
             ["Instructor and ISA: review the work presented, do more research, find more "
              "research papers, and implement accordingly"],
             ["Review sections 1.4 and 1.5 against recent code-switching MT and "
              "evaluation work; add the papers that change a design decision and "
              "implement what they change in the pipeline, harness or models "
              "(Jenil with all members)"]),
            ("1.5",
             ["Technology and literature surveys merged with comparison tables"],
             ["Literature base too narrow for the design decisions it supports"],
             ["Extend 1.5 with recent code-switching work and carry the findings into the "
              "code, not only the survey"]),
            ("3.x",
             ["Presented the four-stage pipeline live from a fresh clone: ingest, clean, "
              "split with leakage gate, statistics",
              "Demonstrated the leakage gate halting on an injected test source",
              "Resolved from Progress Report 1: HinGE's released splits are not mutually "
              "exclusive, so splits were re-derived from 1,938 unique sources with 0 "
              "exact and 0 near-duplicate overlaps, committed under SHA-256 hashes",
              "Resolved from Progress Report 1: the 4,803 reference count is now measured "
              "directly off the file at 4,799, with both figures reported"],
             ["The split step was not deterministic: the same seed produced different "
              "splits because cluster membership depended on set iteration order",
              "The run log marked clean checkouts as dirty, invalidating provenance "
              "records",
              "HinGE ships as a pickle, which the ingest stage does not accept and which "
              "is unsafe to load blindly"],
             ["Replace the cluster walk with a deterministic union-find and sort the LSH "
              "query results; fix delivered as a pull request against the author's own "
              "branch and reviewed there",
              "Count only tracked changes toward the dirty flag",
              "Convert the pickle to CSV in a separate, inspected step before ingest"]),
            ("3.4",
             ["Disjoint splits of 3,738 / 468 / 468 committed with manifests"],
             ["Gold evaluation set is empty: gold_set.csv holds a header row and 0 of 800 "
              "items, so the chrF++ success criterion cannot be evaluated"],
             ["Author the first 200 items, validate them and measure throughput; if the "
              "rate is too low, cut the target from 800 to 500 under the recorded rule "
              "(Jenil, 298-55, 5 November)"]),
            ("2.2",
             ["Workbook 1 sections 1.1 to 2.4 merged, one Linear issue per section"],
             ["Issues marked Done on the Linear board with no artifact on main",
              "No branch protection, and no merged pull request carries a review"],
             ["Reset each issue to its true state with a comment saying what is missing "
              "(Prakhar, 298-45, 22 October)",
              "Protection requiring one non-author approval, plus a reviewer rotation "
              "(Prakhar, 298-60, 26 October)"]),
            ("2.3",
             ["Resource budget and a reproducible Gantt and PERT schedule merged"],
             ["GPU allocation unconfirmed since the request went out on 26 September"],
             ["Obtain a written answer from the cluster, or fund and test the fallback "
              "(Prakhar, 298-51, 24 October)"]),
        ],
    },
    {
        "when": "7:00 pm to 9:15 pm on 10/22/2026",
        "where": "Online / Zoom",
        "who": "Savalia, Shevkar, Singh (joined briefly, unwell), Thomas Lnu, Waghmare",
        "rows": [
            ("4.5",
             ["Resolved from Team Meeting 1: both model arms were executed on a Tesla T4, "
              "proving the CUDA path including the 4-bit NF4 quantised branch that cannot "
              "be tested on the team's Apple Silicon machines",
              "QLoRA trainer merged with loss masked to completion tokens and eleven "
              "CPU-side tests, plus an --adapter flag so the fine-tuned arm is scored "
              "through the same script as the baseline",
              "Opened docs/COMPUTE_BUDGET.md with the first seven run records: 0.112 "
              "GPU-hours spent against a budget of 80 to 145"],
             ["The trainer requested bf16 unconditionally, but a T4 is Turing and has no "
              "bf16 silicon; the support check counts emulation, so thirty steps of a "
              "0.5B model took 301 seconds through a software path",
              "The pinned requirement resolved to transformers 5.x in Colab and broke the "
              "training arguments",
              "Gradient checkpointing severed the gradient graph on the non-quantised path",
              "A long run lost all output when the Colab session dropped"],
             ["Ask for native bf16 only and fall back to fp16 on pre-Ampere cards; record "
              "the precision in every run record so a regression is visible",
              "Pin transformers to 4.57.6 in the notebook and assert the major version "
              "before training",
              "Enable input gradients explicitly on that path",
              "Write checkpoints to a persistent directory and make the notebook resumable"]),
            ("2.2",
             ["Re-derived every Part A percentage against the main branch rather than "
              "against the board, and committed the result",
              "Audited the board: eight issues were Done with no artifact a reader can "
              "open, and all eight were reset with a comment naming what is missing"],
             ["Part A and Part C would have contradicted each other and the board",
              "The Linear assignee and the pull-request author disagree on two issues, so "
              "the board under-reports one member and over-reports another",
              "Prakhar was unwell and could not complete his two issues due today"],
             ["Treat an issue as incomplete unless a reader can open its artifact; the "
              "reset moved 33 story points of real unfinished work back into the cycle",
              "Report both the board assignee and the pull-request author in Part C, and "
              "say which is which",
              "Waghmare completes 298-45 and 298-48 on Singh's behalf, recorded as such "
              "in Part C rather than left to look like Singh's output"]),
            ("2.4",
             ["Reviewed the critical path to Team Meeting 2 on 12 November"],
             ["No commit reached main between 8 and 21 October; all merges this period "
              "fell on two days",
              "Team Meeting 2 requires a cloud pipeline, a live prototype, the baseline "
              "reproduced and a first model trained; none of the four exists today",
              "Only three days separate the last planned delivery from the checkpoint"],
             ["Every member pushes at least one commit against a Cycle 4 issue by "
              "26 October, then at least twice a week, with the commit log reviewed at "
              "each weekly meeting",
              "Rank every Cycle 4 issue by how directly it stands between the team and "
              "those four items, and schedule in that order",
              "Treat any slip of more than three days on a critical-path issue as a "
              "trigger to report the limitation at the checkpoint rather than discover it "
              "there"]),
            ("References",
             ["Workbook 1 references, submission checklist and self-assessment merged"],
             ["The harness normalisation covers 3 of the 72 groups in the committed "
              "spelling-variant lexicon, and two of its rules corrupt forms rather than "
              "normalising them",
              "No bootstrap resampling exists, although the requirements commit to it"],
             ["Drive normalisation from the lexicon and add 1,000-sample bootstrap "
              "confidence intervals, with a test that fails against the regex version "
              "(Thomas Lnu, 298-59, 2 November)"]),
        ],
    },
]

# ---------------------------------------------------------------------- Part C
PART_C = [
    ("Waghmare, Sarvesh", "5",
     "eval, writing",
     "298-30, 298-31, 298-36, 298-39, 298-46 — QLoRA trainer, Colab notebook and the "
     "first GPU run records: " + REPO + "/pull/25"),
    ("Singh, Prakhar Kumar", "4",
     "infra, writing",
     "298-37, 298-40, 298-45, 298-48 — demo runbook and two fresh-clone preflight "
     "records: " + REPO + "/pull/20"),
    ("Savalia, Jenil Sanjaybhai", "4",
     "writing",
     "298-32, 298-42, 298-43, 298-47 — minutes for both meetings in this window: "
     + REPO + "/pull/29"),
    ("Thomas Lnu, Shibin Biji", "4",
     "data, writing",
     "298-33, 298-41, 298-44, 298-49 — pipeline run on the real HinGE corpus and the "
     "demo notebook: " + REPO + "/pull/21"),
    ("Shevkar, Yash", "3",
     "data, research, writing",
     "298-34, 298-35, 298-38 — four-stage data pipeline in one command: "
     + REPO + "/pull/18"),
    ("Team total", "20", "data, eval, infra, research, writing",
     "23 pull requests merged, 0 reviewed, 19 self-merged"),
]

PART_C_NOTES = [
    "The window is 25 September to 22 October in Pacific time, which is how Linear anchors "
    "its cycles. Five pull requests merged on the evening of 24 September read as "
    "25 September in UTC; they belong to Progress Report 1 and are not counted again here.",

    "This table was counted after the 298-45 reset, so it counts work a reader can open. "
    "Eight issues had been marked Done with no artifact on main — 298-10, 298-15, "
    "298-16, 298-17, 298-21, 298-23, 298-24 and 298-25 — and each now carries a "
    "comment naming what is missing and the issue that tracks the remainder.",

    "Singh's four closed issues overstate his period and his two pull requests understate "
    "it. He was unwell on 22 October; 298-45 and 298-48 are assigned to him and closed "
    "under his name, but the work was done by Waghmare and merged as pull request 31. His "
    "own output this period is 298-37 and 298-40.",

    "The Linear assignee and the pull-request author disagree in both directions. 298-34 "
    "and 298-38 are Shevkar's on the board and landed as pull requests authored by "
    "Savalia, which is why Shevkar closed the fewest issues but the second-most story "
    "points — the data pipeline alone is an eight-point issue. Two of Thomas Lnu's "
    "branches were committed and merged under Waghmare's account.",

    "No model-labelled issue closed this period. Five of the six configured labels were "
    "exercised; the sixth is model, and both of its issues are blocked on the GPU "
    "allocation. The label gap and row 4.5 of Part A are the same fact.",

    "No pull request merged in this window carried a review, and 19 of the 23 were merged "
    "by their own author. Branch protection is not enabled on the default branch. This is "
    "the most serious process finding of the period and is the first item in Part D.",
]

# ---------------------------------------------------------------------- Part D
PART_D = [
    ("GPU allocation requested on 26 September is still unconfirmed",
     "Blocks the baseline, Model 1 and Model 2 — three of the four items Team "
     "Meeting 2 requires on 12 November. Rows 4.5 and 4.6 cannot move",
     "Singh",
     "Written answer from the cluster, or the fallback funded and one job proven on it, by "
     "24 October (298-51)"),
    ("No model trained or scored on the real corpus",
     "Row 4.5 is at 25%. The only numbers that exist are a single-seed synthetic smoke "
     "test on a 0.5B stand-in, so the central comparison of the project is unmeasured",
     "Waghmare",
     "Model 1 scored on three seeds by 3 November (298-53); Model 2 QLoRA on three seeds "
     "by 9 November (298-54)"),
    ("Published baseline has no code release and the reproduction has not been run",
     "The evaluation harness is unvalidated against any external number, so a "
     "plausible-looking score cannot be distinguished from a harness bug",
     "Thomas Lnu",
     "Rebuild the mBART recipe from the paper and pass the 0.01 ROUGE-L gate, or document "
     "the failure with evidence, by 7 November (298-52)"),
    ("Gold evaluation set is empty: 0 of 800 items",
     "The code-switching penalty is defined on this set, and the primary success criterion "
     "of chrF++ 3.0 points above zero-shot is stated on it",
     "Savalia",
     "First 200 items authored and validated, three columns each, by 5 November (298-55)"),
    ("Harness normalisation covers 3 of the lexicon's 72 groups and two rules corrupt "
     "forms; no bootstrap resampling exists",
     "Normalised chrF++ is not comparable with the committed lexicon, and no reported "
     "difference can be given a confidence interval",
     "Thomas Lnu",
     "Lexicon-driven normalisation and 1,000-sample bootstrap intervals by 2 November "
     "(298-59)"),
    ("Branch protection is not enabled: 0 of 23 merged pull requests carried a review and "
     "19 were self-merged",
     "No independent check on anything merged this period, including the non-determinism "
     "found by chance in the split step. The reproducibility claim in Section 7 is weaker "
     "than the code behind it",
     "Singh",
     "Protection requiring one non-author approval and a published reviewer rotation by "
     "26 October (298-60)"),
    ("Nothing is deployed, and Team Meeting 2 requires a live prototype",
     "Row 5 is at 5%. A demonstration cannot be assembled in the final week",
     "Singh",
     "Thin-slice prototype deployed to the cloud with the latency target measured, by "
     "9 November (298-56)"),
    ("Back-translation source has not been checked against the test sources",
     "HinGE's English comes from the IIT Bombay corpus, which is part of Samanantar. If "
     "the sets intersect, Model 4 is invalidated and the contamination is invisible in the "
     "scores",
     "Shevkar",
     "Contamination check run before any synthetic data is generated, by 9 November "
     "(298-58)"),
    ("Work arrives in bursts: all 23 merges this period fell on two days, with a "
     "fourteen-day gap between them",
     "Review is impossible at that cadence, and a late failure in the GPU runs leaves no "
     "recovery time before 11 November",
     "All five; Singh tracks",
     "Every member pushes at least one commit against a Cycle 4 issue by 26 October, then "
     "at least twice a week"),
    ("Model and infrastructure work is concentrated in two members",
     "Single point of failure on the training code and the deployment path; label balance "
     "on the board hides it because writing issues are spread evenly",
     "Singh",
     "Pair a second member onto 298-54 and 298-56, and rotate reviewers from 26 October"),
    ("Risk: the baseline may not reach 0.617 even if rebuilt correctly",
     "The published figure follows an automatic transliteration step and a dictionary step "
     "whose dictionary was never released; with automatic transliteration alone the paper "
     "reports 0.484",
     "Thomas Lnu",
     "Report against both rows and raise the tolerance question with the advisor rather "
     "than tuning toward the number, by 7 November"),
    ("Risk: free-tier GPU may be too slow for three seeds of a 7B model",
     "A reduced seed count would break the three-seed rule that every reported number "
     "depends on",
     "Waghmare",
     "The notebook already persists finished seeds; drop to a 4B-class backbone as the "
     "stated last resort, never below three seeds"),
]

OUTCOMES = [
    ("GPU access confirmed, or the fallback funded and proven by a completed run",
     "Singh", "298-51", "24 October",
     "a run record from the chosen GPU in runs/"),
    ("Branch protection enabled with one required non-author review, and the reviewer "
     "rotation published",
     "Singh", "298-60", "26 October",
     "no pull request merged without a review after this date"),
    ("Model 1 zero-shot scored on the real corpus at three seeds, 0-shot and 5-shot",
     "Waghmare", "298-53", "3 November",
     "three run records and a results row with mean and standard deviation"),
    ("First 200 items of the team-authored evaluation set written and validated",
     "Savalia", "298-55", "5 November",
     "validate_gold_set.py --expected-count 200 passes"),
    ("Published baseline reproduced within 0.01 ROUGE-L, or the failure documented",
     "Thomas Lnu", "298-52", "7 November",
     "scored outputs for both input conditions and a --check-baseline result"),
]


# ------------------------------------------------------------------- rendering
def build(out: Path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    for margin in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, margin, Inches(1))

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    def para(text="", size=None, bold=False, italic=False, align=None,
             before=None, after=None):
        p = doc.add_paragraph()
        if align is not None:
            p.alignment = align
        if before is not None:
            p.paragraph_format.space_before = Pt(before)
        if after is not None:
            p.paragraph_format.space_after = Pt(after)
        if text:
            run = p.add_run(text)
            run.font.name = FONT
            run.font.bold = bold
            run.font.italic = italic
            if size:
                run.font.size = Pt(size)
        return p

    def part_heading(text):
        return para(text, size=14, bold=True, before=18, after=8)

    def bullet(text, size=10.5):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(text)
        run.font.name, run.font.size = FONT, Pt(size)
        return p

    def borders(table):
        el = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = OxmlElement("w:" + edge)
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), "4")
            e.set(qn("w:space"), "0")
            e.set(qn("w:color"), "808080")
            el.append(e)
        table._tbl.tblPr.append(el)

    def shade(cell, fill="EFEFEF"):
        sh = OxmlElement("w:shd")
        sh.set(qn("w:val"), "clear")
        sh.set(qn("w:color"), "auto")
        sh.set(qn("w:fill"), fill)
        cell._tc.get_or_add_tcPr().append(sh)

    def write_cell(cell, lines, size=9.5, bold=False, bullets=False):
        cell.text = ""
        if isinstance(lines, str):
            lines = [lines]
        for i, line in enumerate(lines):
            p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(("• " if bullets else "") + line)
            run.font.name, run.font.size, run.font.bold = FONT, Pt(size), bold

    def table(rows, widths, size=9.5, numbered_cols=()):
        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        t.autofit = False
        borders(t)
        for ri, row in enumerate(rows):
            for ci, value in enumerate(row):
                cell = t.cell(ri, ci)
                write_cell(cell, value, size=size, bold=(ri == 0))
                if ri == 0:
                    shade(cell)
                elif ci in numbered_cols:
                    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for ci, w in enumerate(widths):
            for ri in range(len(rows)):
                t.cell(ri, ci).width = Inches(w)
        return t

    centre = WD_ALIGN_PARAGRAPH.CENTER

    # -------------------------------------------------------------- header
    para("Department of Applied Data Science", size=12, bold=True, align=centre, after=0)
    para("DATA 298A  MSDA Project I", size=12, bold=True, align=centre, after=0)
    para("Progress Report 2", size=16, bold=True, align=centre, before=6, after=6)
    para(TITLE, size=12, bold=True, align=centre, after=8)
    para("Team 2  ·  Section 11  ·  Topic 23", align=centre, after=0)
    para(MEMBERS, align=centre, after=0)
    para("Date of report: October 22, 2026", align=centre, after=0)
    para("Linear cycles covered: Cycles 2–3 (25 September – 22 October 2026)",
         align=centre, after=0)
    para("Repository: " + REPO, size=10, align=centre, after=0)
    para("Linear board: " + LINEAR, size=10, align=centre, after=0)

    # -------------------------------------------------------------- Part A
    part_heading("Part A  ·  Project Status")
    grid = [["Item", "Planning", "Investigation", "Complete", "Document"]]
    for row in PART_A:
        grid.append([row, "", "", "", ""] if isinstance(row, str)
                    else [row[0]] + [f"{v}%" for v in row[1:]])
    tA = table(grid, [3.0, 0.85, 1.05, 0.8, 0.8], numbered_cols=(1, 2, 3, 4))
    for ri, row in enumerate(PART_A, start=1):
        if isinstance(row, str):
            cells = tA.rows[ri].cells
            merged = cells[0]
            for cell in cells[1:]:
                merged = merged.merge(cell)
            write_cell(merged, row, bold=True)
            shade(merged, "F7F7F7")

    for text in GAP_EXPLANATION:
        para(text)
    for text in GAP_BULLETS:
        bullet(text)
    for text in GAP_CLOSING:
        para(text)

    # -------------------------------------------------------------- Part B
    doc.add_page_break()
    part_heading("Part B  ·  Minutes of Meetings")
    for meeting in MEETINGS:
        para("Time and date: " + meeting["when"], size=10.5, bold=True, after=0)
        para("Location / media: " + meeting["where"], size=10.5, after=0)
        para("Participants: " + meeting["who"], size=10.5, after=4)
        rows = [["Section", "Achievements", "Issues", "Recommended Solutions"]]
        t = table(rows + [[s, "", "", ""] for s, *_ in meeting["rows"]],
                  [0.6, 2.35, 1.75, 1.8])
        for ri, (_, ach, iss, sol) in enumerate(meeting["rows"], start=1):
            write_cell(t.cell(ri, 1), ach, bullets=True)
            write_cell(t.cell(ri, 2), [f"{i}. {x}" for i, x in enumerate(iss, 1)])
            write_cell(t.cell(ri, 3), [f"{i}. {x}" for i, x in enumerate(sol, 1)])
        para(after=10)

    # -------------------------------------------------------------- Part C
    doc.add_page_break()
    part_heading("Part C  ·  Work completed this period")
    para("Reconciled against the Linear board on 22 October 2026.")
    table([["Member", "Issues closed", "Labels worked", "Key artifact link"]]
          + [list(r) for r in PART_C],
          [1.35, 0.8, 1.15, 3.2], numbered_cols=(1,))
    for text in PART_C_NOTES:
        bullet(text, size=10)

    # -------------------------------------------------------------- Part D
    doc.add_page_break()
    part_heading("Part D  ·  Blockers, risks and next period")
    table([["Blocker or risk", "Impact", "Owner", "Next action and date"]]
          + [list(r) for r in PART_D],
          [1.9, 1.95, 0.75, 1.9])

    para("Five specific outcomes for the next period, each with an owner. Cycle 4 runs "
         "from 22 October to 9 November, ending three days before Team Meeting 2. Each "
         "outcome is checkable against an artifact rather than a statement.",
         before=12)
    for i, (outcome, owner, issue, due, done) in enumerate(OUTCOMES, start=1):
        bullet(f"{i}.  {outcome} — {owner}, {issue}, by {due}. "
               f"Done means: {done}.", size=10.5)

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" / "progress2" / "T2.A5.docx")
    build(ap.parse_args().out)
