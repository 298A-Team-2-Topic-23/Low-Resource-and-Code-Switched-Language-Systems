import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts.error_analysis_sheet import (CODES, make_sheet, paired_difference, sample_sources,
                                          summarise)


def write(path, lines):
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class ErrorAnalysisSheetTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.dir = Path(holder.name)
        # 60 unique sources; every third one has a second reference record, as HinGE does.
        src, ref = [], []
        for i in range(60):
            for r in range(2 if i % 3 == 0 else 1):
                src.append("source sentence number {}".format(i))
                ref.append("reference {} nahi hai version {}".format(i, r))
        write(self.dir / "src.txt", src)
        write(self.dir / "ref.txt", ref)
        write(self.dir / "m2.txt", ["m2 nhi output {}".format(i) for i in range(len(src))])
        write(self.dir / "m3.txt", ["m3 nahi output {}".format(i) for i in range(len(src))])
        write(self.dir / "m4.txt", ["m4 output नहीं {}".format(i) for i in range(len(src))])
        self.systems = {"M2": self.dir / "m2.txt", "M3": self.dir / "m3.txt",
                        "M4": self.dir / "m4.txt"}
        self.run = self.dir / "run"
        self.meta = make_sheet(self.dir / "src.txt", self.dir / "ref.txt", self.systems, self.run)

    def test_sheet_is_blind_and_paired(self):
        sheet = read(self.run / "coding_sheet.csv")
        self.assertEqual(len(sheet), 150)
        self.assertNotIn("system", sheet[0])
        self.assertFalse(any("M2" in v or "M3" in v for row in sheet for v in row.values()))
        key = read(self.run / "key.csv")
        lines = {s: sorted(int(k["line"]) for k in key if k["system"] == s) for s in self.systems}
        self.assertEqual(lines["M2"], lines["M3"])
        self.assertEqual(lines["M3"], lines["M4"])
        self.assertEqual(len(set(lines["M2"])), 50)

    def test_sampling_is_by_unique_source_and_deterministic(self):
        src = (self.dir / "src.txt").read_text(encoding="utf-8").splitlines()
        chosen = sample_sources(src)
        self.assertEqual(len({src[i] for i in chosen}), 50)
        self.assertEqual(chosen, sample_sources(src))
        again = make_sheet(self.dir / "src.txt", self.dir / "ref.txt", self.systems,
                           self.dir / "run2")
        self.assertEqual((self.run / "coding_sheet.csv").read_bytes(),
                         (self.dir / "run2" / "coding_sheet.csv").read_bytes())
        self.assertEqual(again["sources_with_identical_outputs"], 0)

    def test_all_references_are_shown(self):
        sheet = read(self.run / "coding_sheet.csv")
        doubled = [r for r in sheet if r["english_source"].endswith(" 0")]
        self.assertTrue(all(r["references"].count(" || ") == 1 for r in doubled))

    def test_overlap_rows_are_a_subset(self):
        sheet = {r["row_id"]: r for r in read(self.run / "coding_sheet.csv")}
        overlap = read(self.run / "coding_sheet_overlap.csv")
        self.assertEqual(len(overlap), 30)
        self.assertTrue(all(sheet[r["row_id"]] == r for r in overlap))

    def test_automatic_indicators(self):
        key = {k["row_id"]: k["system"] for k in read(self.run / "key.csv")}
        auto = read(self.run / "auto.csv")
        script = {key[a["row_id"]] for a in auto if float(a["devanagari_share"]) > 0}
        self.assertEqual(script, {"M4"})
        m3 = [a for a in auto if key[a["row_id"]] == "M3"]
        self.assertTrue(all(a["canonical_tokens"] == a["lexicon_tokens"] for a in m3))

    def code(self, rule):
        key = {k["row_id"]: k["system"] for k in read(self.run / "key.csv")}
        for name in ("coding_sheet.csv", "coding_sheet_overlap.csv"):
            rows = read(self.run / name)
            for row in rows:
                row["codes"], row["acceptable"] = rule(key[row["row_id"]])
            save(self.run / name, rows)

    @unittest.skipUnless(importlib.util.find_spec("sacrebleu"), "sentence chrF++ needs sacrebleu")
    def test_summary_finds_a_spelling_concentrated_difference(self):
        self.code(lambda system: {"M2": ("SPELLING_VARIANT", "no"), "M3": ("OK", "yes"),
                                  "M4": ("SCRIPT, FLUENCY", "no")}[system])
        result = summarise(self.run)
        self.assertTrue(result["complete"], result.get("problems"))
        diff = result["differences"]["M2_minus_M3"]
        self.assertEqual(diff["spelling"]["difference"], 1.0)
        self.assertEqual(diff["adequacy"]["difference"], 0.0)
        self.assertEqual(result["rates"]["M4"]["script"], 1.0)
        self.assertEqual(result["automatic"]["M4"]["outputs_with_devanagari"], 50)
        self.assertEqual(result["agreement"]["spelling"]["raw_agreement"], 1.0)
        self.assertTrue(json.loads((self.run / "summary.json").read_text()))

    def test_incomplete_or_inconsistent_coding_is_refused(self):
        self.code(lambda system: ("OK", "yes"))
        result = summarise(self.run)
        self.assertFalse(result["complete"])
        self.assertTrue(all("SCRIPT disagrees" in p for p in result["problems"]))
        self.code(lambda system: ("OK, FLUENCY", "maybe"))
        problems = summarise(self.run)["problems"]
        self.assertTrue(any("OK must stand alone" in p for p in problems))
        self.assertTrue(any("acceptable must be yes or no" in p for p in problems))

    def test_codes_match_the_codebook(self):
        codebook = (Path(__file__).resolve().parent.parent / "analysis" / "error_analysis"
                    / "CODEBOOK.md").read_text(encoding="utf-8")
        for code in CODES:
            self.assertIn("`{}`".format(code), codebook)


class PairedDifferenceTest(unittest.TestCase):
    def test_interval_brackets_the_difference(self):
        result = paired_difference([1, 1, 0, 1, 0] * 10, [0, 1, 0, 0, 0] * 10)
        self.assertEqual(result["difference"], 0.4)
        low, high = result["ci95"]
        self.assertLessEqual(low, 0.4)
        self.assertGreaterEqual(high, 0.4)


if __name__ == "__main__":
    unittest.main()
