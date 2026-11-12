"""Tests for the AI-6 slice builder (298-75).

The behaviour worth testing hardest is the script guard. AI-6 names four slices
and the repository can only supply three, so the tempting way to "close" the
requirement is to drop a Romanised file in as `hi_deva` and report four rows.
That would measure the same script twice and the table would look complete, so
the builder refuses it and these tests pin that refusal down.
"""

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import make_slices  # noqa: E402

DEVANAGARI = [
    "मैं कल बाज़ार जा रहा हूँ",
    "वह स्कूल नहीं गया",
    "क्या तुम मेरी मदद कर सकते हो",
]


class BuildTest(unittest.TestCase):

    def setUp(self):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.out = Path(d.name)
        self.manifest = make_slices.build(self.out, n=50, seed=42)

    def test_three_slices_are_written(self):
        for name in ("en", "hi_roman", "hinglish"):
            self.assertTrue((self.out / "{}.txt".format(name)).exists(), name)

    def test_devanagari_slice_is_absent_not_empty(self):
        """An absent slice must not be written as an empty file."""
        self.assertFalse((self.out / "hi_deva.txt").exists())
        self.assertIn("hi_deva", self.manifest["absent"])

    def test_absence_names_a_reason_and_a_command(self):
        entry = self.manifest["absent"]["hi_deva"]
        self.assertIn("reason", entry)
        self.assertIn("fetch_data.py", entry["command_that_closes_it"])
        self.assertIn("HinGE", entry["supplied_by"])

    def test_ai6_status_is_definite(self):
        self.assertIn("not met", self.manifest["ai6_status"])
        self.assertIn("3 of 4", self.manifest["ai6_status"])

    def test_manifest_lists_all_four_required_slices(self):
        self.assertEqual(self.manifest["slices_required_by_ai6"],
                         ["en", "hi_deva", "hi_roman", "hinglish"])

    def test_manifest_is_written_and_valid_json(self):
        data = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data["present"]), {"en", "hi_roman", "hinglish"})

    def test_every_present_slice_records_a_sha256(self):
        for name, info in self.manifest["present"].items():
            self.assertEqual(len(info["sha256"]), 64, name)
            self.assertGreater(info["n_lines"], 0, name)

    def test_paths_are_repo_relative_or_absolute_tmp(self):
        """No machine-specific path inside the repo should leak into a manifest."""
        for info in self.manifest["present"].values():
            self.assertNotIn(str(REPO_ROOT), info["source"])


class DeterminismTest(unittest.TestCase):

    def _build(self, seed):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        out = Path(d.name)
        return make_slices.build(out, n=60, seed=seed)

    def test_same_seed_gives_identical_hashes(self):
        a, b = self._build(42), self._build(42)
        self.assertEqual({k: v["sha256"] for k, v in a["present"].items()},
                         {k: v["sha256"] for k, v in b["present"].items()})

    def test_different_seed_changes_the_synthetic_slices(self):
        a, b = self._build(42), self._build(7)
        self.assertNotEqual(a["present"]["en"]["sha256"],
                            b["present"]["en"]["sha256"])

    def test_the_fixture_slice_does_not_move_with_the_seed(self):
        """hi_roman comes from a committed file, so the seed must not touch it."""
        a, b = self._build(42), self._build(7)
        self.assertEqual(a["present"]["hi_roman"]["sha256"],
                         b["present"]["hi_roman"]["sha256"])


class ScriptGuardTest(unittest.TestCase):

    def test_roman_text_is_refused_as_devanagari(self):
        with self.assertRaises(make_slices.SliceError) as ctx:
            make_slices._check_script("hi_deva", ["main kal bazaar ja raha hoon"],
                                      "devanagari")
        self.assertIn("same script twice", str(ctx.exception))

    def test_devanagari_text_is_accepted_as_devanagari(self):
        frac = make_slices._check_script("hi_deva", DEVANAGARI, "devanagari")
        self.assertGreater(frac, make_slices.DEVA_MIN)

    def test_devanagari_text_is_refused_as_roman(self):
        with self.assertRaises(make_slices.SliceError):
            make_slices._check_script("hi_roman", DEVANAGARI, "roman")

    def test_roman_text_is_accepted_as_roman(self):
        frac = make_slices._check_script("en", ["the parcel is boring today"], "roman")
        self.assertLessEqual(frac, make_slices.ROMAN_MAX)

    def test_a_mixed_file_fails_both_checks(self):
        """The deliberate gap between the thresholds: half-and-half is refused
        either way rather than quietly accepted as whichever was asked for."""
        mixed = ["main kal bazaar ja raha hoon", "मैं कल बाज़ार जा रहा हूँ"]
        with self.assertRaises(make_slices.SliceError):
            make_slices._check_script("hi_deva", mixed, "devanagari")
        with self.assertRaises(make_slices.SliceError):
            make_slices._check_script("hi_roman", mixed, "roman")


class AddHiDevaTest(unittest.TestCase):
    """The path that closes AI-6 once the corpus exists. Exercised here because
    no team machine has the corpus, so this is the only place it runs."""

    def setUp(self):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.out = self.root / "slices"
        self.manifest = make_slices.build(self.out, n=40, seed=42)

    def _csv(self, text):
        path = self.root / "hinge.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_it_closes_ai6_with_a_devanagari_hindi_column(self):
        csv_path = self._csv("English,Hindi\n" + "".join(
            "en{},{}\n".format(i, line) for i, line in enumerate(DEVANAGARI)))
        manifest = make_slices.add_hi_deva(self.out, csv_path, self.manifest)
        self.assertIn("hi_deva", manifest["present"])
        self.assertEqual(manifest["absent"], {})
        self.assertIn("met", manifest["ai6_status"])
        self.assertTrue((self.out / "hi_deva.txt").exists())

    def test_a_romanised_hindi_column_is_refused(self):
        csv_path = self._csv("English,Hindi\nhello,main ghar ja raha hoon\n")
        with self.assertRaises(make_slices.SliceError):
            make_slices.add_hi_deva(self.out, csv_path, self.manifest)

    def test_a_missing_file_says_how_to_make_it(self):
        with self.assertRaises(make_slices.SliceError) as ctx:
            make_slices.add_hi_deva(self.out, self.root / "nope.csv", self.manifest)
        self.assertIn("convert_hinge_pkl", str(ctx.exception))

    def test_a_csv_without_a_hindi_column_is_refused(self):
        csv_path = self._csv("English,Hinglish\nhello,namaste yaar\n")
        with self.assertRaises(make_slices.SliceError) as ctx:
            make_slices.add_hi_deva(self.out, csv_path, self.manifest)
        self.assertIn("no 'Hindi' column", str(ctx.exception))

    def test_an_empty_hindi_column_is_refused(self):
        """The synthetic generator's hindi column is empty in all 1,200 rows, so
        pointing this at synthetic output must not produce a slice."""
        csv_path = self._csv("English,Hindi\nhello,\nworld,  \n")
        with self.assertRaises(make_slices.SliceError) as ctx:
            make_slices.add_hi_deva(self.out, csv_path, self.manifest)
        self.assertIn("empty", str(ctx.exception))


class FixtureReaderTest(unittest.TestCase):

    def test_it_reads_the_committed_fixture(self):
        lines = make_slices.fixture_romanised_hindi()
        self.assertGreaterEqual(len(lines), 25)
        self.assertTrue(all(line.strip() for line in lines))

    def test_the_header_row_is_not_data(self):
        self.assertNotIn("hindi_roman", make_slices.fixture_romanised_hindi())

    def test_comments_and_blanks_are_skipped(self):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "f.tsv"
        path.write_text("english\thindi_roman\n# note\n\nhello\tnamaste\n",
                        encoding="utf-8")
        self.assertEqual(make_slices.fixture_romanised_hindi(path), ["namaste"])

    def test_a_fixture_with_no_rows_raises(self):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "f.tsv"
        path.write_text("english\thindi_roman\n# only a comment\n", encoding="utf-8")
        with self.assertRaises(make_slices.SliceError):
            make_slices.fixture_romanised_hindi(path)


class SyntheticColumnsTest(unittest.TestCase):

    def test_the_hindi_column_is_empty_which_is_why_hi_deva_is_absent(self):
        """This is the fact the AI-6 verdict rests on, so it is pinned by a test
        rather than asserted in prose."""
        from lrcs.data.synthetic import generate
        rows = generate(200, 42)
        self.assertEqual(sum(1 for _en, hi, _hg in rows if (hi or "").strip()), 0)

    def test_english_and_hinglish_come_back_non_empty(self):
        english, hinglish = make_slices.synthetic_columns(100, 42)
        self.assertTrue(english)
        self.assertTrue(hinglish)
        self.assertTrue(all(line.strip() for line in english + hinglish))


if __name__ == "__main__":
    unittest.main()
