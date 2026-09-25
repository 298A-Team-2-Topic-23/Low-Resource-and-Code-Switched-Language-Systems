import csv
import tempfile
import unittest
from pathlib import Path

from data.goldtestset.validate_gold_set import validate


class GoldSetValidationTest(unittest.TestCase):
    def write_csv(self, rows):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        fields = ["item_id", "english_source", "devanagari_hindi",
                  "romanized_hinglish", "needs_review", "notes"]
        with handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return Path(handle.name)

    def test_valid_row(self):
        path = self.write_csv([{
            "item_id": "G001", "english_source": "Come here",
            "devanagari_hindi": "Yahan aao", "romanized_hinglish": "Yahan aa jao",
            "needs_review": "no", "notes": "",
        }])
        self.assertEqual(validate(path, expected_count=1), [])

    def test_flagged_row_requires_notes(self):
        path = self.write_csv([{
            "item_id": "G001", "english_source": "Come here",
            "devanagari_hindi": "Yahan aao", "romanized_hinglish": "Yahan aa jao",
            "needs_review": "yes", "notes": "",
        }])
        self.assertTrue(any("notes" in error for error in validate(path)))

    def test_empty_template_requires_explicit_opt_in(self):
        path = self.write_csv([])
        self.assertTrue(validate(path))
        self.assertEqual(validate(path, allow_empty=True), [])


if __name__ == "__main__":
    unittest.main()