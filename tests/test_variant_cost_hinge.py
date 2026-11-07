import json
import unittest
from pathlib import Path

from analysis.variant_cost_hinge import OUT, STATS, VARIANTS, measure, read_costs


class VariantCostTest(unittest.TestCase):
    def setUp(self):
        self.stats = json.loads(Path(STATS).read_text(encoding="utf-8"))
        self.means, self.forms = read_costs(VARIANTS)

    def test_committed_output_matches_committed_inputs(self):
        committed = json.loads(Path(OUT).read_text(encoding="utf-8"))
        self.assertEqual(measure(self.stats, self.means, self.forms), committed)

    def test_burden_is_the_mean_of_group_means(self):
        result = measure(self.stats, self.means, self.forms)
        self.assertEqual(result["whole_lexicon_burden"], 1.8322)
        self.assertEqual(result["whole_lexicon_mean_per_form"], 1.8634)

    def test_weighting_is_by_occurrence(self):
        stats = {
            "source": "t", "synthetic": False,
            "spelling_variance": {
                "lexicon_groups": 1, "lexicon_token_occurrences": 4,
                "top_groups": [{"group": "g", "forms": {"a": 3, "b": 1}}],
            },
        }
        result = measure(stats, {"g": 1.5}, {("g", "a"): 1, ("g", "b"): 2})
        self.assertEqual(result["tokens_per_occurrence"], 1.25)

    def test_refuses_synthetic_statistics(self):
        with self.assertRaises(SystemExit):
            measure(dict(self.stats, synthetic=True), self.means, self.forms)


if __name__ == "__main__":
    unittest.main()
