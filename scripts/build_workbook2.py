"""Build T2.A6.docx (Workbook 2, Template 5) from the Markdown under docs/workbook2/.

Usage:  python scripts/build_workbook2.py [--out reports/workbook2/T2.A6.docx] [--final]

Section prose stays where its author committed it; this script only assembles. Sections 1 and 2
are not rewritten, so anything revised since Workbook 1 goes in the carry-forward table. Sections
4.5 and 4.6 stay bare headings, because they are written up with the final report.

A section that is not on main yet is not an error during drafting. It is rendered as a
highlighted [PENDING: ...] line, as is any [PENDING: ...] written in the Markdown itself, and the
first page says the file is a draft. --final exits 1 and writes nothing while any of that remains,
or while a section has no named author or a citation has no reference entry. So a draft cannot be
uploaded by accident.

It needs no .docx template file, so it runs from a clean clone. The page setup and table helpers
are shared with scripts/build_report.py.
"""
import argparse
import re
import sys
from pathlib import Path

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_report import (FONT, LINEAR, MEMBERS, REPO, ROOT, TITLE, borders,  # noqa: E402
                          new_document, shade, write_cell)

SOURCE_DIR = ROOT / "docs" / "workbook2"
DEFAULT_OUT = ROOT / "reports" / "workbook2" / "T2.A6.docx"
REPORT_DATE = "November 11, 2026"

# Template 5 order. Heading rows are strings; a tuple is (number, title, author, Linear issue).
SECTIONS = [
    "3  Data Engineering",
    ("3.1", "Data Process", "Shevkar", "298-57"),
    ("3.2", "Data Collection", "Shevkar", "298-57"),
    ("3.3", "Data Pre-processing", "Thomas Lnu", "298-63"),
    ("3.4", "Data Transformation", "Thomas Lnu", "298-63"),
    ("3.5", "Data Preparation", "Shevkar", "298-64"),
    ("3.6", "Data Statistics", "Waghmare", "298-65"),
    "4  Model Development",
    ("4.1", "Model Proposals", "Savalia", "298-66"),
    ("4.2", "Model Supports", "Singh", "298-67"),
    ("4.3", "Model Comparison and Justification", "Shevkar", "298-69"),
    ("4.4", "Model Evaluation Methods", "Thomas Lnu", "298-68"),
    ("4.5", "First Model Implementation", None, None),
    ("4.6", "Baseline Reproduction", None, None),
]
BARE = {"4.5", "4.6"}
BACK_MATTER = ("references.md", "submission_checklist.md", "self_assessment.md",
               "carry_forward.md")
# On disk here but deliberately not part of the document. The pipeline demo is rubric line 4.5,
# presented live on 12 November; it is not Template 5's section 4.5.
NOT_ASSEMBLED = {"ASSEMBLY.md", "section_4_5_pipeline_demo.md"}

INLINE = re.compile(r"(\[PENDING:[^\]]*\]|\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|\*[^*\s][^*]*\*)")
IMAGE = re.compile(r"^!\[(.*?)\]\((.+?)\)\s*$")
NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
AUTHOR_LINE = re.compile(r"(Written by|Author:|Authors:)")
CITATIONS = (
    re.compile(r"\b([A-Z][\w'-]+) et al\.,? \(?((?:19|20)\d{2})"),
    re.compile(r"\b([A-Z][\w'-]+) (?:&|and) [A-Z][\w'-]+(?: \(|, )((?:19|20)\d{2})"),
    re.compile(r"\(([A-Z][\w'-]+), ((?:19|20)\d{2})\)"),
)


def section_files(source_dir):
    """Map section numbers to files. section_3_1_3_2.md covers both 3.1 and 3.2."""
    found = {}
    for path in sorted(Path(source_dir).glob("section_*.md")):
        if path.name in NOT_ASSEMBLED:
            continue
        for major, minor in re.findall(r"(\d)_(\d)", path.stem):
            found[f"{major}.{minor}"] = path
    return found


def unrecognised_files(source_dir):
    known = set(BACK_MATTER) | NOT_ASSEMBLED | {p.name for p in section_files(source_dir).values()}
    return sorted(p.name for p in Path(source_dir).glob("*.md") if p.name not in known)


def find_citations(text):
    """Surname and year of every in-text citation, ignoring code spans."""
    text = re.sub(r"\s+", " ", re.sub(r"`[^`]*`", "", text))
    return {(m.group(1), m.group(2)) for pattern in CITATIONS for m in pattern.finditer(text)}


def missing_references(sources, references):
    """Citations with no reference entry starting with that surname and carrying that year."""
    entries = [e for e in references.split("\n\n") if e.strip()]
    missing = set()
    for text in sources:
        for surname, year in find_citations(text):
            if not any(e.lstrip().startswith(surname) and f"({year})" in e for e in entries):
                missing.add(f"{surname} ({year})")
    return sorted(missing)


class Renderer:
    def __init__(self, doc):
        self.doc = doc
        self.problems = []
        for level, size in ((1, 14), (2, 12.5), (3, 11.5), (4, 11)):
            style = doc.styles[f"Heading {level}"]
            style.font.name, style.font.size = FONT, Pt(size)
            style.font.bold, style.font.color.rgb = True, RGBColor(0, 0, 0)
            fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
            for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                fonts.set(qn(attr), FONT)
            for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                fonts.attrib.pop(qn(attr), None)

    def runs(self, paragraph, text, size=None, bold=False):
        for piece in INLINE.split(text):
            if not piece:
                continue
            if piece.startswith("[PENDING:"):
                run = paragraph.add_run(piece)
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                self.problems.append(piece)
            elif piece.startswith("**"):
                run = paragraph.add_run(piece[2:-2])
                run.font.bold = True
            elif piece.startswith("`"):
                run = paragraph.add_run(piece[1:-1])
                run.font.name = "Courier New"
                run.font.size = Pt((size or 11) - 1.5)
                run.font.bold = bold or None
                continue
            elif piece.startswith("["):
                run = paragraph.add_run(piece[1:piece.index("]")])
            elif piece.startswith("*"):
                run = paragraph.add_run(piece[1:-1])
                run.font.italic = True
            else:
                run = paragraph.add_run(piece)
            run.font.name = FONT
            if bold:
                run.font.bold = True
            if size:
                run.font.size = Pt(size)

    def paragraph(self, text, align=None, size=None, bold=False, after=None):
        p = self.doc.add_paragraph()
        if align is not None:
            p.alignment = align
        if after is not None:
            p.paragraph_format.space_after = Pt(after)
        self.runs(p, text, size=size, bold=bold)
        return p

    def table(self, rows):
        columns = max(len(r) for r in rows)
        rows = [r + [""] * (columns - len(r)) for r in rows]
        t = self.doc.add_table(rows=len(rows), cols=columns)
        t.alignment = WD_TABLE_ALIGNMENT.LEFT
        t.autofit = False
        borders(t)
        # Share the 6.5 in page by content length, with a floor so short columns stay legible.
        lengths = [max(min(len(r[c]), 60) for r in rows) + 4 for c in range(columns)]
        widths = [max(0.55, 6.5 * n / sum(lengths)) for n in lengths]
        widths = [w * 6.5 / sum(widths) for w in widths]
        for ri, row in enumerate(rows):
            for ci, value in enumerate(row):
                cell = t.cell(ri, ci)
                cell.width = Inches(widths[ci])
                write_cell(cell, "", size=9)
                self.runs(cell.paragraphs[0], value, size=9, bold=ri == 0)
                if ri == 0:
                    shade(cell)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def markdown(self, text, base_dir, heading_offset=1):
        """Render the subset of Markdown the sections use."""
        lines = text.splitlines()
        i, buffer = 0, []

        def flush():
            if buffer:
                self.paragraph(" ".join(buffer))
                buffer.clear()

        while i < len(lines):
            line = lines[i].rstrip()
            stripped = line.strip()
            image = IMAGE.match(stripped)
            numbered = NUMBERED.match(stripped)
            if stripped in ("", "---"):
                flush()
            elif stripped.startswith("#"):
                flush()
                level = len(stripped) - len(stripped.lstrip("#"))
                self.doc.add_heading(stripped.lstrip("# ").strip(),
                                     min(level + heading_offset, 4))
            elif stripped.startswith("```"):
                flush()
                language = stripped[3:].strip()
                block = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    block.append(lines[i])
                    i += 1
                if language == "mermaid":
                    self.paragraph("[PENDING: mermaid diagram cannot render in Word; commit it "
                                   "as a generated figure]")
                else:
                    p = self.doc.add_paragraph()
                    p.paragraph_format.left_indent = Inches(0.25)
                    run = p.add_run("\n".join(block))
                    run.font.name, run.font.size = "Courier New", Pt(9)
            elif stripped.startswith("|"):
                flush()
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    if not all(set(c) <= set("-: ") and c for c in cells):
                        rows.append(cells)
                    i += 1
                i -= 1
                self.table(rows)
            elif image:
                flush()
                path = (Path(base_dir) / image.group(2)).resolve()
                if path.exists():
                    self.doc.add_picture(str(path), width=Inches(6.0))
                else:
                    self.paragraph(f"[PENDING: missing figure {image.group(2)}]")
            elif stripped.startswith(("- ", "* ")) or numbered:
                flush()
                item = [numbered.group(2) if numbered else stripped[2:]]
                while (i + 1 < len(lines) and lines[i + 1].startswith("  ")
                       and lines[i + 1].strip()):
                    i += 1
                    item.append(lines[i].strip())
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.3)
                p.paragraph_format.first_line_indent = Inches(-0.2)
                p.paragraph_format.space_after = Pt(3)
                marker = f"{numbered.group(1)}. " if numbered else "•  "
                self.runs(p, marker + " ".join(item))
            elif stripped.startswith(">"):
                flush()
                quoted = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    quoted.append(lines[i].strip().lstrip("> ").strip())
                    i += 1
                i -= 1
                p = self.paragraph(" ".join(quoted))
                p.paragraph_format.left_indent = Inches(0.25)
            else:
                buffer.append(stripped)
            i += 1
        flush()


def cover(r, files, draft_note):
    centre = WD_ALIGN_PARAGRAPH.CENTER
    if draft_note:
        r.paragraph(draft_note, align=centre)
    r.paragraph("Department of Applied Data Science", centre, 12, True, 0)
    r.paragraph("DATA 298A  MSDA Project I", centre, 12, True, 0)
    r.paragraph("Workbook 2", centre, 16, True, 6)
    r.paragraph(TITLE, centre, 12, True, 8)
    r.paragraph("Team 2  ·  Section 11  ·  Topic 23", centre, after=0)
    r.paragraph(MEMBERS, centre, after=0)
    r.paragraph("Date of submission: " + REPORT_DATE, centre, after=0)
    r.paragraph("Repository: " + REPO, centre, 10, after=0)
    r.paragraph("Linear board: " + LINEAR, centre, 10, after=8)
    rows = [["Section", "Written by", "Linear"]]
    for entry in SECTIONS:
        if isinstance(entry, tuple) and entry[0] not in BARE:
            state = "" if entry[0] in files else " (not yet on main)"
            rows.append([f"{entry[0]} {entry[1]}", entry[2] + state, entry[3]])
    rows.append(["References, checklist, self-assessment, carry-forward", "Savalia", "298-71"])
    r.table(rows)
    r.doc.add_page_break()


def body(r, source_dir, files):
    done = set()
    for entry in SECTIONS:
        if isinstance(entry, str):
            r.doc.add_heading(entry, 1)
            continue
        number, title, author, issue = entry
        if number in BARE:
            r.doc.add_heading(f"{number}  {title}", 2)
            continue
        path = files.get(number)
        if path is None:
            r.doc.add_heading(f"{number}  {title}", 2)
            r.paragraph(f"[PENDING: section {number} is not on main. "
                        f"Owner {author}, Linear {issue}.]")
        elif path not in done:
            text = path.read_text(encoding="utf-8")
            if not AUTHOR_LINE.search(text):
                r.problems.append(f"{path.name} does not name who wrote it")
            r.markdown(text, path.parent)
            done.add(path)
    for name in BACK_MATTER:
        path = Path(source_dir) / name
        if path.exists():
            r.markdown(path.read_text(encoding="utf-8"), path.parent, heading_offset=0)
        else:
            r.doc.add_heading(name.replace("_", " ").removesuffix(".md").capitalize(), 1)
            r.paragraph(f"[PENDING: docs/workbook2/{name} is not on main]")


def build(source_dir=SOURCE_DIR, out=DEFAULT_OUT, final=False):
    """Assemble the workbook and return the list of open problems."""
    source_dir = Path(source_dir)
    files = section_files(source_dir)
    # A first pass counts what is open, so the cover of the real pass can say so.
    probe = Renderer(new_document())
    body(probe, source_dir, files)

    references = source_dir / "references.md"
    if references.exists():
        sources = [p.read_text(encoding="utf-8") for p in set(files.values())]
        for missing in missing_references(sources, references.read_text(encoding="utf-8")):
            probe.problems.append(f"cited but not in references.md: {missing}")
    problems = list(probe.problems)

    if final and problems:
        return problems

    r = Renderer(new_document())
    note = ""
    if problems:
        note = f"[PENDING: DRAFT, NOT FOR SUBMISSION. {len(problems)} open items; see below.]"
    cover(r, files, note)
    body(r, source_dir, files)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    r.doc.save(out)
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--source", type=Path, default=SOURCE_DIR)
    ap.add_argument("--final", action="store_true",
                    help="refuse to write the file while anything is still open")
    args = ap.parse_args(argv)

    problems = build(args.source, args.out, args.final)
    for name in unrecognised_files(args.source):
        print(f"warning: docs/workbook2/{name} is not assembled; name it section_N_M.md or add "
              "it to NOT_ASSEMBLED", file=sys.stderr)
    for problem in problems:
        print("open:", problem)
    if args.final and problems:
        print(f"refusing to write {args.out}: {len(problems)} open items", file=sys.stderr)
        return 1
    print(f"wrote {args.out} ({len(problems)} open items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
