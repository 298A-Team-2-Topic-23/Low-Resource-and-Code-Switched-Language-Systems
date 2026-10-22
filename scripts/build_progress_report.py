"""Assemble Progress Report 2 (T2.A5.docx) from the department template.

Usage:  python scripts/build_progress_report.py --template "Progress Report Template.docx"
                                                [--out reports/progress2/T2.A5.docx]

Parts A and B are written into the template's own tables, so its layout is kept. Part A's
percentages and gap explanation come from docs/progress2/part_a_status.md. Part B is taken
from the minutes in docs/minutes/. Part D is converted from docs/progress2/part_d_risks.md.
Part C (298-48) is inserted from docs/progress2/part_c_work.md if that file exists;
otherwise a highlighted placeholder marks where it goes.
"""
import argparse
import copy
import re
from pathlib import Path

import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = Path(__file__).resolve().parent.parent
PROGRESS = ROOT / "docs" / "progress2"

TEAM = "2 (Topic 23: Low-Resource and Code-Switched Language Systems)"
MEMBERS = ("Savalia, Jenil; Shevkar, Yash; Singh, Prakhar; Thomas Lnu, Shibin; "
           "Waghmare, Sarvesh")
REPORT_DATE = "October 22, 2026"
CYCLES = "Cycles 2 and 3, 25 September to 22 October 2026"

# Part A, keyed by the template's own row labels. Template rows 2.2-2.5 follow the
# department numbering; the values are taken from the matching workbook sections
# (2.2 Project Management Plan covers methodology and organisation, 2.3 resources,
# 2.4 schedule), as noted under the table.
STATUS = {
    "1.1": (100, 95, 95, 95), "1.2": (100, 95, 95, 95), "1.3": (100, 90, 85, 85),
    "1.4": (100, 95, 95, 95), "1.5": (100, 95, 95, 95),
    "2.1": (100, 90, 90, 85), "2.2": (100, 95, 90, 95), "2.3": (100, 95, 90, 95),
    "2.4": (100, 85, 60, 90), "2.5": (100, 90, 85, 90),
    "3.1": (100, 95, 95, 35), "3.2": (100, 95, 95, 40), "3.3": (100, 95, 95, 35),
    "3.4": (100, 95, 95, 40), "3.5": (100, 90, 90, 35), "3.6": (100, 95, 95, 50),
    "References": (100, 90, 95, 95),
}
EXTRA_STATUS = [  # rows beyond the template, inserted before References
    ("4.1 Model Proposals", (100, 90, 85, 90)),
    ("4.2 Model Supports", (90, 70, 55, 40)),
    ("4.3 Model Comparison and Justification", (100, 85, 70, 85)),
    ("4.4 Model Evaluation Methods", (100, 90, 85, 85)),
    ("4.5 First Model Implementation", (85, 60, 25, 20)),
    ("4.6 Baseline Reproduction", (80, 55, 10, 20)),
    ("5. Prototype and System Implementation", (60, 25, 5, 5)),
    ("6. Benchmarking, Evaluation, and Failure Study", (55, 30, 15, 10)),
    ("7. Reproducibility", (100, 90, 85, 60)),
    ("8. 298B Plan", (55, 25, 10, 5)),
]
STATUS_NOTE = (
    "Template rows 2.2 to 2.5 follow the department numbering. Their values come from "
    "the team's workbook sections: 2.2 Project Management Plan (2.2.1 to 2.2.8, which "
    "covers methodology and organisation) for rows 2.2 and 2.3, 2.3 Resources for row 2.4, "
    "and 2.4 Schedule for row 2.5. Rows 4 to 8 are added below the template's rows. All "
    "values were checked against main at commit b480fa6 (Part A, Linear 298-46, owner "
    "Sarvesh).")

# Part B. One entry per meeting: header lines, then section -> (achievements, issues,
# recommended solutions). Every row restates docs/minutes/<date>.md.
MEETINGS = [
    {
        "time": "Team Meeting 1 (graded checkpoint) on 10/08/2026",
        "media": "Online/Zoom",
        "people": MEMBERS + "; instructor and ISA",
        "rows": {
            "1.4": (["Every model identifier verified against its official Hugging Face "
                     "model card on 8 Oct, with the command to repeat the check. Closes "
                     "the Progress Report 1 issue of a draft naming a configuration that "
                     "does not exist"],
                    ["Instructor and ISA: review the work presented, do more research, "
                     "find more research papers, and implement accordingly"],
                    ["Review 1.4 against recent code-switching MT work. Add the papers "
                     "that change a design decision and implement what they change "
                     "(Jenil, all members)"]),
            "1.5": ([],
                    ["Literature base too narrow for the design decisions it supports "
                     "(instructor and ISA feedback)"],
                    ["Extend 1.5 with recent code-switching MT and evaluation papers, and "
                     "carry the findings into the pipeline, harness and models"]),
            "2.2": ([],
                    ["Issues marked Done on Linear with no artifact on main",
                     "No branch protection; no merged PR has a recorded review"],
                    ["Reset each to its true state with a comment saying what is missing "
                     "(298-45, Prakhar)",
                     "Protection requiring one non-author approval, plus a reviewer "
                     "rotation (298-60, Prakhar)"]),
            "2.4": ([],
                    ["GPU allocation unconfirmed since 26 Sep"],
                    ["Written answer from the cluster, or fund the fallback (298-51, "
                     "Prakhar)"]),
            "3.1": (["Four-stage pipeline (ingest, clean, split with leakage gate, "
                     "statistics) merged and run live; fresh-clone preflight logs in "
                     "reports/rehearsals/2026-10-07/",
                     "Leakage gate demonstrated halting on an injected test source"],
                    [], []),
            "3.2": (["4,799 references measured directly off the file, against 4,803 "
                     "published; both reported in docs/datasheet.md. Closes the PR1 "
                     "issue of an uncorroborated count"],
                    ["Reconciliation of the four-reference difference still open"],
                    ["Recount from Table 1 of the source paper; report both until "
                     "settled (Yash)"]),
            "3.4": (["Splits re-derived from 1,938 unique sources: 0 exact and 0 "
                     "near-duplicate overlaps at Jaccard >= 0.7; 3,738 / 468 / 468 "
                     "committed with SHA-256 manifests. Closes the PR1 issue that HinGE's "
                     "released splits are not mutually exclusive"],
                    ["Gold test set holds 0 of 800 items, so the +3 chrF++ criterion "
                     "cannot be evaluated"],
                    ["Author and validate the first 200 items; cut 800 to 500 under the "
                     "recorded rule if throughput is too low (298-55, Jenil, 5 Nov)"]),
            "3.6": (["Corpus statistics committed (reports/data_statistics.json); "
                     "real-corpus run records dated 8 Oct under runs/"],
                    [], []),
        },
        "extra": {},
    },
    {
        "time": "Progress Report 2 working session on 10/22/2026",
        "media": "Online",
        "people": MEMBERS,
        "rows": {
            "2.1": (["Data management plan merged (PR #26, Yash), closing the overdue "
                     "298-35"], [], []),
            "2.2": (["Part A status (PR #24, Sarvesh) and Part D risks (PR #28, Shibin) "
                     "written from repository evidence"],
                    ["No commits between 9 and 21 October; Cycle 3 at 0 of 13 points "
                     "after ten days",
                     "8 Oct minutes written up 14 days late, against the 24-hour rule",
                     "Zero reviews on PRs #21 to #27; six self-merged",
                     "Eight issues Done on the board without artifacts"],
                    ["Every member commits against a cycle-4 issue by 26 Oct, then at "
                     "least twice a week; Prakhar checks the log weekly",
                     "Recorder commits minutes to docs/minutes/ the same day (Jenil)",
                     "Branch protection and reviewer rotation by 26 Oct (298-60)",
                     "Reset 298-10, -15, -16, -17, -21, -23, -24, -25 today (298-45)"]),
            "2.4": ([],
                    ["No GPU allocation: blocks the baseline, M1 and M2"],
                    ["Written answer, or the fallback funded and one job run on it, by "
                     "24 Oct (298-51, Prakhar)"]),
            "2.5": ([],
                    ["Team Meeting 2 on 12 Nov needs a cloud pipeline, a live prototype, "
                     "the baseline reproduced and a first model trained; none exists; "
                     "three days of slack"],
                    ["Cycle 4 plan: GPU 24 Oct (298-51), M1 scored 3 Nov (298-53), "
                     "baseline 7 Nov (298-52), M2 and prototype 9 Nov (298-54, 298-56)"]),
            "3.4": ([],
                    ["Gold set still 0 of 800"],
                    ["First 200 items authored and validated, plus the 50-item rater "
                     "pilot, by 5 Nov (298-55, Jenil)"]),
        },
        "extra": {
            "4.5": (["QLoRA trainer and Colab notebook for M1 and M2 merged (PRs #25, "
                     "#27, Sarvesh); first GPU smoke runs under runs/, on a free T4 and "
                     "synthetic data. Not reportable results (docs/COMPUTE_BUDGET.md)"],
                    ["No model trained or scored on the real corpus"],
                    ["M1 on three seeds by 3 Nov (298-53); M2 QLoRA on three seeds by "
                     "9 Nov (298-54)"]),
            "4.6": ([],
                    ["Baseline not reproduced; Gahoi et al. (2022) released no code"],
                    ["Rebuild the recipe and run both input conditions by 7 Nov "
                     "(298-52, Shibin)"]),
        },
    },
]


def cell_texts(cell):
    return "".join(t.text for t in cell._tc.iter(qn("w:t"))).strip()


def set_labelled(paragraph, value):
    """Keep the first run (the bold label) and replace everything after it."""
    runs = paragraph.runs
    for r in runs[2:]:
        r._r.getparent().remove(r._r)
    if len(runs) > 1:
        runs[1].text = value
    else:
        paragraph.add_run(value)


def set_cell(cell, lines):
    """Fill a cell with one paragraph per line, cloned from its first paragraph."""
    paras = cell.paragraphs
    proto = copy.deepcopy(paras[0]._p)
    proto_rpr = None
    first_run = proto.find(qn("w:r"))
    if first_run is not None and first_run.find(qn("w:rPr")) is not None:
        proto_rpr = first_run.find(qn("w:rPr"))
    for child in list(proto):
        if child.tag != qn("w:pPr"):
            proto.remove(child)
    for p in paras:
        p._p.getparent().remove(p._p)
    for line in lines or [""]:
        p = copy.deepcopy(proto)
        r = OxmlElement("w:r")
        if proto_rpr is not None:
            r.append(copy.deepcopy(proto_rpr))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = line
        r.append(t)
        p.append(r)
        cell._tc.append(p)


def clone_row_before(table, template_row, anchor_row):
    new = copy.deepcopy(template_row._tr)
    anchor_row._tr.addprevious(new)
    return [c for c in table.rows if c._tr is new][0]


def fill_status(table):
    rows = list(table.rows)
    by_label = {}
    for row in rows[1:]:
        label = cell_texts(row.cells[0]).split()[0]  # template mixes spaces and NBSPs
        by_label.setdefault(label, row)
    for label, values in STATUS.items():
        row = by_label[label]
        for cell, v in zip(row.cells[1:], values):
            set_cell(cell, [f"{v}%"])
    proto, refs = by_label["3.6"], by_label["References"]
    for name, values in EXTRA_STATUS:
        row = clone_row_before(table, proto, refs)
        set_cell(row.cells[0], [name])
        for cell, v in zip(row.cells[1:], values):
            set_cell(cell, [f"{v}%"])


def fill_meeting(header_rows, body_rows, table, meeting):
    for row in header_rows:
        p = row.cells[0].paragraphs[0]
        text = cell_texts(row.cells[0])
        if text.startswith("Time and Date"):
            set_labelled(p, " " + meeting["time"])
        elif text.startswith("Location"):
            set_labelled(p, " " + meeting["media"])
        elif text.startswith("Participants"):
            set_labelled(p, " " + meeting["people"])
    section_rows = [r for r in body_rows if cell_texts(r.cells[0]) not in ("Section", "")]
    for row in section_rows:
        label = cell_texts(row.cells[0])
        ach, iss, sol = meeting["rows"].get(label, ([], [], []))
        set_cell(row.cells[1], ach)
        set_cell(row.cells[2], iss)
        set_cell(row.cells[3], sol)
    proto, ref = section_rows[-2], section_rows[-1]
    for label, (ach, iss, sol) in meeting["extra"].items():
        row = clone_row_before(table, proto, ref)
        set_cell(row.cells[0], [label])
        set_cell(row.cells[1], ach)
        set_cell(row.cells[2], iss)
        set_cell(row.cells[3], sol)


INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def add_inline(paragraph, text):
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**"):
            paragraph.add_run(piece[2:-2]).bold = True
        elif piece.startswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(9)
        elif piece.startswith("*"):
            paragraph.add_run(piece[1:-1]).italic = True
        else:
            paragraph.add_run(piece)


def bordered(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "000000")
        borders.append(e)
    tbl_pr.append(borders)


def markdown_blocks(doc, text, skip_title=True):
    """Convert the subset of Markdown used in docs/progress2 into document elements."""
    out = []
    lines = text.splitlines()
    i = 0
    para = []

    def flush():
        if para:
            p = doc.add_paragraph()
            add_inline(p, " ".join(para))
            out.append(p._p)
            para.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("# ") and skip_title:
            flush()
        elif line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            out.append(doc.add_paragraph(line.lstrip("# "), style=f"Heading {min(level, 3)}")._p)
        elif line.startswith("```"):
            flush()
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                p = doc.add_paragraph()
                run = p.add_run(lines[i])
                run.font.name = "Courier New"
                run.font.size = Pt(8)
                out.append(p._p)
                i += 1
        elif line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cells):
                    rows.append(cells)
                i += 1
            i -= 1
            table = doc.add_table(rows=len(rows), cols=len(rows[0]))
            bordered(table)
            for r, cells in enumerate(rows):
                for c, value in enumerate(cells):
                    p = table.cell(r, c).paragraphs[0]
                    add_inline(p, f"**{value}**" if r == 0 and value else value)
                    for run in p.runs:
                        run.font.size = Pt(8)
            out.append(table._tbl)
        elif line.startswith("- "):
            flush()
            item = [line[2:]]
            while i + 1 < len(lines) and lines[i + 1].startswith("  ") and lines[i + 1].strip():
                i += 1
                item.append(lines[i].strip())
            p = doc.add_paragraph(style="List Paragraph")
            add_inline(p, "• " + " ".join(item))
            out.append(p._p)
        elif line.strip() in ("", "---"):
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return out


def insert_after(anchor, elements):
    for el in elements:
        anchor.addnext(el)
        anchor = el
    return anchor


def heading(doc, text):
    return doc.add_paragraph(text, style="Heading 1")._p


def highlighted(doc, text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return p._p


def build(template, out):
    doc = docx.Document(template)
    body = doc.element.body

    title = list(body.iterchildren())[4]
    for t in title.iter(qn("w:t")):
        t.text = t.text.replace(" 1 (or 2)", " 2")

    cover, status, m1_head, m1_body, m2 = doc.tables[:5]
    set_labelled(cover.rows[0].cells[0].paragraphs[0], ": " + TEAM)
    set_labelled(cover.rows[1].cells[0].paragraphs[0], MEMBERS)
    set_labelled(cover.rows[2].cells[0].paragraphs[0], REPORT_DATE)
    cycles = copy.deepcopy(cover.rows[2]._tr)
    cover.rows[2]._tr.addnext(cycles)
    p = cover.rows[3].cells[0].paragraphs[0]
    p.runs[0].text = "Cycles covered: "
    set_labelled(p, CYCLES)

    fill_status(status)
    part_a = (PROGRESS / "part_a_status.md").read_text()
    explanation = part_a[part_a.index("## Explanation for the large gaps"):]
    explanation = explanation.replace("Row 2.3 runs the other way",
                                      "Row 2.4 (template numbering; workbook 2.3) runs "
                                      "the other way")
    note = doc.add_paragraph()
    add_inline(note, STATUS_NOTE)
    insert_after(status._tbl, [note._p] + markdown_blocks(doc, explanation))

    fill_meeting(m1_head.rows, m1_body.rows, m1_body, MEETINGS[0])
    fill_meeting(m2.rows[:3], m2.rows[3:], m2, MEETINGS[1])

    placeholder = [p for p in doc.paragraphs if "More minutes of meetings" in p.text][0]
    tail = [heading(doc, "Part C   Work Completed")]
    part_c = PROGRESS / "part_c_work.md"
    if part_c.exists():
        tail += markdown_blocks(doc, part_c.read_text())
    else:
        tail.append(highlighted(doc, "PART C PENDING: Linear 298-48 (Prakhar). Insert the "
                                     "per-member work-completed table here, reconciled to "
                                     "the board after the 298-45 reset."))
    tail.append(heading(doc, "Part D   Blockers, Risks and Next Period"))
    tail += markdown_blocks(doc, (PROGRESS / "part_d_risks.md").read_text())
    insert_after(placeholder._p, tail)
    placeholder._p.getparent().remove(placeholder._p)

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    print(f"wrote {out}  (Part C {'included' if part_c.exists() else 'PENDING'})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "progress2" / "T2.A5.docx")
    args = ap.parse_args()
    build(args.template, args.out)
