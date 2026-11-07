import re
import tempfile
import unittest
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")

from scripts.build_workbook2 import (BACK_MATTER, SOURCE_DIR, build,  # noqa: E402
                                     find_citations, main, missing_references, section_files,
                                     unrecognised_files)

SECTION = "# {n} Title\n\nWritten by Someone.\n\nBody with **bold** text.\n"


def text_of(path):
    document = docx.Document(path)
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        parts += [cell.text for row in table.rows for cell in row.cells]
    return "\n".join(parts)


def headings_of(path):
    return [p.text for p in docx.Document(path).paragraphs if p.style.name.startswith("Heading")]


class WorkbookBuildTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.dir = Path(holder.name)
        self.src = self.dir / "src"
        self.src.mkdir()
        self.out = self.dir / "T2.A6.docx"

    def write_complete(self):
        for n in ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "4.1", "4.2", "4.3", "4.4"):
            name = "section_" + n.replace(".", "_") + ".md"
            (self.src / name).write_text(SECTION.format(n=n), encoding="utf-8")
        for name in BACK_MATTER:
            (self.src / name).write_text("# " + name + "\n\nDone.\n", encoding="utf-8")

    def test_complete_sources_pass_final(self):
        self.write_complete()
        self.assertEqual(build(self.src, self.out, final=True), [])
        self.assertTrue(self.out.exists())
        self.assertNotIn("PENDING", text_of(self.out))

    def test_final_refuses_and_writes_nothing_when_a_section_is_missing(self):
        self.write_complete()
        (self.src / "section_3_1.md").unlink()
        problems = build(self.src, self.out, final=True)
        self.assertTrue(any("section 3.1" in p for p in problems))
        self.assertFalse(self.out.exists())

    def test_draft_marks_itself_and_the_missing_section(self):
        self.write_complete()
        (self.src / "section_4_2.md").unlink()
        build(self.src, self.out)
        text = text_of(self.out)
        self.assertIn("DRAFT, NOT FOR SUBMISSION", text)
        self.assertIn("section 4.2 is not on main", text)
        self.assertIn("Singh", text)

    def test_pending_written_in_markdown_blocks_final(self):
        self.write_complete()
        (self.src / "carry_forward.md").write_text(
            "# Carry\n\n| A | B |\n|---|---|\n| x | [PENDING: decide] |\n", encoding="utf-8")
        self.assertEqual(build(self.src, self.out, final=True), ["[PENDING: decide]"])

    def test_sections_keep_template_order_and_4_5_4_6_stay_bare(self):
        self.write_complete()
        (self.src / "section_4_5_pipeline_demo.md").write_text(
            "# 4.5 Demo\n\nAuthor: Y\n\nDEMO BODY\n", encoding="utf-8")
        build(self.src, self.out)
        heads = headings_of(self.out)
        numbers = [h.split()[0] for h in heads if re.match(r"\d\.\d", h)]
        self.assertEqual(numbers, ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6",
                                   "4.1", "4.2", "4.3", "4.4", "4.5", "4.6"])
        self.assertNotIn("DEMO BODY", text_of(self.out))

    def test_one_file_can_cover_two_sections(self):
        self.write_complete()
        (self.src / "section_3_1.md").unlink()
        (self.src / "section_3_2.md").unlink()
        (self.src / "section_3_1_3_2.md").write_text(
            "# 3.1 One\n\nWritten by X.\n\n# 3.2 Two\n\nONLY ONCE\n", encoding="utf-8")
        self.assertEqual(build(self.src, self.out, final=True), [])
        self.assertEqual(text_of(self.out).count("ONLY ONCE"), 1)

    def test_section_without_an_author_blocks_final(self):
        self.write_complete()
        (self.src / "section_3_3.md").write_text("# 3.3 T\n\nNo name.\n", encoding="utf-8")
        problems = build(self.src, self.out, final=True)
        self.assertEqual(problems, ["section_3_3.md does not name who wrote it"])

    def test_mermaid_blocks_final(self):
        self.write_complete()
        (self.src / "section_3_1.md").write_text(
            "# 3.1 T\n\nWritten by X.\n\n```mermaid\nflowchart TB\n```\n", encoding="utf-8")
        self.assertTrue(any("mermaid" in p for p in build(self.src, self.out, final=True)))

    def test_inline_markup_tables_and_lists_render(self):
        self.write_complete()
        (self.src / "section_4_1.md").write_text(
            "# 4.1 T\n\nWritten by X.\n\nSee `code` and **bold** and [a link](http://x.y).\n\n"
            "| H1 | H2 |\n|---|---|\n| a | **b** |\n\n- one\n  continued\n\n1. first\n",
            encoding="utf-8")
        build(self.src, self.out)
        text = text_of(self.out)
        self.assertIn("See code and bold and a link.", text)
        self.assertNotIn("**", text)
        self.assertIn("one continued", text)
        self.assertIn("1. first", text)

    def test_missing_figure_is_flagged(self):
        self.write_complete()
        (self.src / "section_3_6.md").write_text(
            "# 3.6 T\n\nWritten by X.\n\n![fig](nope.png)\n", encoding="utf-8")
        self.assertTrue(any("nope.png" in p for p in build(self.src, self.out, final=True)))

    def test_citation_without_a_reference_blocks_final(self):
        self.write_complete()
        (self.src / "section_4_1.md").write_text(
            "# 4.1 T\n\nWritten by X.\n\nAs (Nobody et al., 2020) said.\n", encoding="utf-8")
        problems = build(self.src, self.out, final=True)
        self.assertEqual(problems, ["cited but not in references.md: Nobody (2020)"])

    def test_main_returns_nonzero_when_final_refuses(self):
        self.assertEqual(main(["--source", str(self.src), "--out", str(self.out), "--final"]), 1)
        self.assertFalse(self.out.exists())


class CitationTest(unittest.TestCase):
    def test_forms_are_found(self):
        found = find_citations("Gahoi et al. (2022) and (Poplack, 1980) and Das & Gambäck (2014) "
                               "and `Ignored et al. (1999)` in October and November 2026, as Hu et\n al. (2022) said.")
        self.assertEqual(found, {("Gahoi", "2022"), ("Poplack", "1980"), ("Das", "2014"), ("Hu", "2022")})

    def test_year_must_match(self):
        refs = "Gahoi, A. (2022). Title.\n\nPoplack, S. (1980). Title.\n"
        self.assertEqual(missing_references(["Gahoi et al. (2021)"], refs), ["Gahoi (2021)"])
        self.assertEqual(missing_references(["(Poplack, 1980)"], refs), [])


class CommittedSourcesTest(unittest.TestCase):
    def test_reference_list_never_uses_et_al(self):
        text = (SOURCE_DIR / "references.md").read_text(encoding="utf-8")
        self.assertNotIn("et al", text)

    def test_reference_list_is_alphabetical(self):
        text = (SOURCE_DIR / "references.md").read_text(encoding="utf-8")
        entries = [e for e in text.split("\n\n")[1:] if not e.startswith("[PENDING")]
        names = [e.split(",")[0].split(".")[0].casefold() for e in entries]
        self.assertEqual(names, sorted(names))

    def test_every_committed_file_has_a_role(self):
        self.assertEqual(unrecognised_files(SOURCE_DIR), [])

    def test_demo_is_not_mistaken_for_section_4_5(self):
        self.assertNotIn("4.5", section_files(SOURCE_DIR))

    def test_committed_sources_build_as_a_draft(self):
        with tempfile.TemporaryDirectory() as holder:
            out = Path(holder) / "draft.docx"
            problems = build(SOURCE_DIR, out)
            self.assertTrue(out.exists())
        # The checklist's five template rows stay open until someone has Template 5 to hand.
        self.assertGreaterEqual(sum("Template 5" in p for p in problems), 5)


if __name__ == "__main__":
    unittest.main()
