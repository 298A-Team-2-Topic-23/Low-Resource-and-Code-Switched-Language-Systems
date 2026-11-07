"""Tests for the stage-sample emitter (298-62).

The thing worth testing hardest is determinism. These files are committed and
quoted by Workbook 2 sections 3.2 to 3.5, so a reviewer must be able to
regenerate them byte-for-byte. Sampling that depended on set or dict iteration
order would still look fine -- the tables would be populated and plausible --
and the drift would only show up as a mystifying diff in someone else's branch.
"""

import random
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
for entry in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    sys.path.insert(0, str(entry))

import emit_stage_samples as ess  # noqa: E402
from lrcs.data import clean as clean_stage  # noqa: E402

EXPECTED_FILES = ("index.md", "raw.md", "preprocessed.md", "transformed.md",
                  "prepared.md", "edge_cases.md")


def args_for(outdir, raw_dir, seed=42, n_synthetic=400, n_samples=5):
    return ess.parse_args([
        "--synthetic",
        "--n-synthetic", str(n_synthetic),
        "--seed", str(seed),
        "--n-samples", str(n_samples),
        "--out-dir", str(outdir),
        "--raw-dir", str(raw_dir),
    ])


def build_in(root, label, seed=42, n_synthetic=400, n_samples=5):
    """One run under `root`. Returns {filename: bytes}.

    The raw directory is shared between runs on purpose: the synthetic corpus is
    written there and its path is recorded in each file's provenance line, so
    giving each run its own raw directory would make the outputs differ on the
    path alone and the comparison would prove nothing.
    """
    outdir = ess.build(args_for(root / label, root / "raw", seed,
                                n_synthetic, n_samples))
    return {p.name: p.read_bytes() for p in sorted(outdir.glob("*.md"))}


def build_once(seed=42, n_synthetic=400, n_samples=5):
    with TemporaryDirectory() as tmp:
        return build_in(Path(tmp), "out", seed, n_synthetic, n_samples)


class DeterminismTest(unittest.TestCase):

    def test_same_seed_produces_byte_identical_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(build_in(root, "a", seed=42),
                             build_in(root, "b", seed=42))

    def test_a_different_seed_changes_the_sample(self):
        """Guards against a seed that is accepted and then ignored."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertNotEqual(build_in(root, "a", seed=42),
                                build_in(root, "b", seed=7))

    def test_every_stage_file_is_written(self):
        produced = build_once()
        for name in EXPECTED_FILES:
            self.assertIn(name, produced, "{} was not emitted".format(name))

    def test_pick_ignores_input_order(self):
        records = [{"id": "{:04d}".format(i)} for i in range(50)]
        expected = ess.pick(records, 5, seed=42)
        for shuffle_seed in (1, 2, 3):
            shuffled = list(records)
            random.Random(shuffle_seed).shuffle(shuffled)
            self.assertEqual(ess.pick(shuffled, 5, seed=42), expected)

    def test_pick_returns_everything_when_asked_for_more_than_exists(self):
        records = [{"id": "b"}, {"id": "a"}]
        self.assertEqual([r["id"] for r in ess.pick(records, 10, seed=42)],
                         ["a", "b"])


class PartitionTest(unittest.TestCase):
    """clean() is now a wrapper over partition(); they must not drift apart."""

    def _records(self):
        return [
            {"id": "1", "english": "hello there", "hindi": "", "hinglish": "namaste bhai",
             "row": 2, "ref": 0},
            {"id": "2", "english": "", "hindi": "", "hinglish": "orphan",
             "row": 3, "ref": 0},
            {"id": "3", "english": "copy this through", "hindi": "",
             "hinglish": "copy this through", "row": 4, "ref": 0},
        ]

    def test_partition_hands_back_the_rejected_records(self):
        kept, removed, attrition = clean_stage.partition(self._records())
        self.assertEqual([r["id"] for r in kept], ["1"])
        self.assertEqual([r["id"] for r in removed["missing_field"]], ["2"])
        self.assertEqual([r["id"] for r in removed["untranslated"]], ["3"])
        self.assertEqual(attrition["removed_total"], 2)

    def test_clean_still_returns_two_values_and_agrees_with_partition(self):
        kept_a, attrition_a = clean_stage.clean(self._records())
        kept_b, _removed, attrition_b = clean_stage.partition(self._records())
        self.assertEqual([r["id"] for r in kept_a], [r["id"] for r in kept_b])
        self.assertEqual(attrition_a["table"], attrition_b["table"])

    def test_every_filter_appears_even_with_nothing_to_remove(self):
        _kept, removed, _attrition = clean_stage.partition(self._records())
        self.assertEqual(list(removed), clean_stage.FILTER_ORDER)

    def test_removal_counts_sum_to_the_total(self):
        """Each record is charged to one filter only; 3.3 states this."""
        _kept, removed, attrition = clean_stage.partition(self._records())
        self.assertEqual(sum(len(v) for v in removed.values()),
                         attrition["removed_total"])


class CellTest(unittest.TestCase):

    def test_pipes_are_escaped_so_the_table_survives(self):
        self.assertEqual(ess.cell("a|b"), "a\\|b")

    def test_newlines_collapse_to_a_space(self):
        self.assertEqual(ess.cell("a\nb"), "a b")

    def test_long_cells_are_truncated(self):
        out = ess.cell("x" * (ess.CELL_LIMIT + 50))
        self.assertEqual(len(out), ess.CELL_LIMIT)
        self.assertTrue(out.endswith("..."))

    def test_integers_get_thousands_separators(self):
        self.assertEqual(ess.cell(4799), "4,799")

    def test_booleans_are_not_formatted_as_numbers(self):
        self.assertEqual(ess.cell(True), "True")

    def test_none_is_empty(self):
        self.assertEqual(ess.cell(None), "")


class ContentTest(unittest.TestCase):

    def setUp(self):
        self.files = build_once()

    def test_synthetic_output_warns_it_is_not_reportable(self):
        """A grader must not mistake a synthetic sample set for the corpus."""
        for name, payload in self.files.items():
            self.assertIn(b"Synthetic corpus", payload,
                          "{} does not carry the synthetic warning".format(name))

    def test_preprocessed_names_every_filter(self):
        payload = self.files["preprocessed.md"].decode("utf-8")
        for name in clean_stage.FILTER_ORDER:
            self.assertIn(name, payload)

    def test_prepared_covers_all_three_splits(self):
        payload = self.files["prepared.md"].decode("utf-8")
        for split in ("train", "dev", "test"):
            self.assertIn("## {} --".format(split), payload)

    def test_transformed_gives_a_reason_for_each_transformation(self):
        payload = self.files["transformed.md"].decode("utf-8")
        for name, _where, _why in ess.TRANSFORMATIONS:
            self.assertIn(name, payload)

    def test_files_are_utf8_so_devanagari_survives(self):
        for name, payload in self.files.items():
            payload.decode("utf-8")  # raises if the encoding was mishandled


if __name__ == "__main__":
    unittest.main()
