"""The split TSVs are quote-free by construction; readers must honour that.

This is a regression test for a bug that real data found and synthetic data
could not. `lrcs.data.splits._split_tsv` joins fields with tabs and quotes
nothing, so a double quote inside a sentence is literal text. Reading such a
file with the csv module's defaults makes `"` open a quoted field, and every
following line is swallowed until the next quote.

Measured on the real HinGE splits before the fix: train parsed as 3,611 records
instead of 3,738 and test as 383 instead of 468, and some surviving records had
an empty `hinglish`, which then tripped the NOT NULL constraint on
`prepared_records` and aborted the warehouse load. The files and the manifest
hashes were correct throughout; only the readers were wrong.

58 of HinGE's 1,976 English sentences contain a double quote. The seeded
synthetic generator produces none, which is exactly why this survived until the
project moved onto real text.
"""

import csv
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs.data import splits  # noqa: E402
from lrcs.warehouse.load import _read_split_tsv  # noqa: E402

# Two records whose English carries an unbalanced double quote, as HinGE's does
# ("And the places of worship are for Allah (alone): So invoke not ...").
# The quote must be at the START of a field to trigger the csv module's quoted
# -field handling, which is exactly the shape real HinGE rows have: 57 fields
# across the train split begin with a double quote, e.g.
#   "And the places of worship are for Allah (alone): So invoke not any ...
RECORDS = [
    {"id": "a1", "group": "g1",
     "english": '"And the places of worship are for Allah (alone): So invoke not',
     "hindi": "वह आया", "hinglish": '"atah Allah ke sath kisi ko na pukaro'},
    {"id": "a2", "group": "g2",
     "english": '"(xviib) any compensation or other payment referred to in clause',
     "hindi": "उसने कहा", "hinglish": "koi bhi muavza ya anya bhugtan"},
    {"id": "a3", "group": "g3", "english": "No quotes at all",
     "hindi": "कोई नहीं", "hinglish": "koi nahi"},
]


class SplitTsvQuotingTest(unittest.TestCase):

    def setUp(self):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.path = Path(d.name) / "train.tsv"
        self.path.write_bytes(splits._split_tsv(RECORDS))

    def test_writer_emits_one_physical_line_per_record_plus_header(self):
        text = self.path.read_text(encoding="utf-8")
        self.assertEqual(len(text.rstrip("\n").split("\n")), len(RECORDS) + 1)

    def test_writer_does_not_escape_or_strip_the_quote(self):
        """The quote must survive as literal data, not become \\" or vanish."""
        self.assertIn('"And the places of worship', self.path.read_text(encoding="utf-8"))

    def test_the_default_csv_reader_loses_records(self):
        """Pinning the bug itself, so the fix cannot be quietly reverted."""
        with open(self.path, encoding="utf-8", newline="") as fh:
            naive = list(csv.DictReader(fh, delimiter="\t"))
        self.assertLess(len(naive), len(RECORDS),
                        "default quoting no longer merges rows; if the csv module "
                        "changed, revisit the reader contract rather than deleting "
                        "this test")

    def test_the_project_reader_recovers_every_record(self):
        rows = _read_split_tsv(self.path)
        self.assertEqual(len(rows), len(RECORDS))
        self.assertEqual([r["id"] for r in rows], ["a1", "a2", "a3"])

    def test_no_field_comes_back_empty(self):
        """The NOT NULL failure that surfaced this: a merged row lost hinglish."""
        for row in _read_split_tsv(self.path):
            for field in ("id", "english", "hinglish"):
                self.assertTrue(row[field].strip(),
                                "{} empty in {}".format(field, row))

    def test_round_trip_is_exact(self):
        rows = _read_split_tsv(self.path)
        for original, got in zip(RECORDS, rows):
            for field in ("id", "group", "english", "hindi", "hinglish"):
                self.assertEqual(got[field], original[field])


class RealSplitsTest(unittest.TestCase):
    """Runs only where the fetched corpus is present; skipped on a bare clone."""

    EXPECTED = {"train": 3738, "dev": 468, "test": 468}

    def setUp(self):
        self.base = REPO_ROOT / "data" / "processed" / "hinge"
        if not (self.base / "train.tsv").exists():
            self.skipTest("real splits absent; run scripts/fetch_data.py then "
                          "scripts/run_pipeline.py --input data/raw/hinge.csv")

    def test_record_counts_match_the_frozen_manifest(self):
        import json
        manifest = json.loads(
            (REPO_ROOT / "data" / "processed" / "manifests"
             / "hinge_split_manifest.json").read_text(encoding="utf-8"))
        for split, expected in self.EXPECTED.items():
            rows = _read_split_tsv(self.base / "{}.tsv".format(split))
            self.assertEqual(len(rows), expected, split)
            self.assertEqual(len(rows), manifest["splits"][split]["records"], split)

    def test_every_real_record_has_a_hinglish_reference(self):
        for split in self.EXPECTED:
            for row in _read_split_tsv(self.base / "{}.tsv".format(split)):
                self.assertTrue(row["hinglish"].strip(),
                                "empty hinglish in {}: {}".format(split, row["id"]))


if __name__ == "__main__":
    unittest.main()
