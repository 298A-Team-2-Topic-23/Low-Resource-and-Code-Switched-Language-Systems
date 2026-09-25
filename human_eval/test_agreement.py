import unittest

from human_eval.agreement import krippendorff_alpha, pairwise_exact


class AgreementTest(unittest.TestCase):
    def test_perfect_ordinal_agreement(self):
        self.assertEqual(krippendorff_alpha([[4, 4, 4], [3, 3, 3]]), 1.0)

    def test_missing_rater_is_excluded_from_pair(self):
        rows = [
            {"a": "4", "b": "4", "c": ""},
            {"a": "3", "b": "2", "c": "3"},
        ]
        result = pairwise_exact(rows, ["a", "b", "c"])
        self.assertEqual(result[("a", "b")][1], 2)
        self.assertEqual(result[("a", "c")][1], 1)

    def test_nominal_agreement(self):
        self.assertEqual(krippendorff_alpha([["yes", "yes"], ["no", "yes"]], "nominal"), 0.0)


if __name__ == "__main__":
    unittest.main()