"""`_corr` must agree with the stdlib, and must work where the stdlib function does not.

`statistics.correlation` arrived in Python 3.10. This project supports 3.9 --
requirements.txt pins matplotlib to 3.9.4 for that reason -- and `validate_raw.py`
is in the clone-and-run path, so calling a 3.10-only function there crashed
exactly the person trying to reproduce our results.
"""

import math
import random
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_raw import _corr  # noqa: E402


class CorrTest(unittest.TestCase):

    def test_perfect_positive(self):
        self.assertAlmostEqual(_corr([(1, 2), (2, 4), (3, 6)]), 1.0, places=12)

    def test_perfect_negative(self):
        self.assertAlmostEqual(_corr([(1, 6), (2, 4), (3, 2)]), -1.0, places=12)

    def test_too_few_pairs_is_none(self):
        self.assertIsNone(_corr([(1, 2), (2, 4)]))

    def test_constant_column_is_none_not_a_crash(self):
        """statistics.correlation raises StatisticsError here; we return None."""
        self.assertIsNone(_corr([(1, 5), (2, 5), (3, 5)]))

    @unittest.skipUnless(hasattr(statistics, "correlation"),
                         "statistics.correlation needs Python 3.10+")
    def test_matches_the_stdlib_on_random_data(self):
        rng = random.Random(42)
        for _ in range(50):
            pairs = [(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(30)]
            mine = _corr(pairs)
            theirs = statistics.correlation([a for a, _ in pairs], [b for _, b in pairs])
            self.assertTrue(math.isclose(mine, theirs, rel_tol=1e-12, abs_tol=1e-12),
                            "{} != {}".format(mine, theirs))


if __name__ == "__main__":
    unittest.main()
