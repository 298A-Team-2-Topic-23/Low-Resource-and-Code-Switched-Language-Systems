"""Tests for the Equivalence-Constraint code-mixing generator (298-17).

Three things are worth testing hardest, and all three were real bugs during
development rather than hypotheticals:

1. Index spans must be de-duplicated. Model 1 is many-to-one, so several Hindi
   tokens link to one English token and a realisation came out as "did did did".
2. Distribution matching must steer the whole batch. Matching per sentence
   cannot work, because a two-block sentence has exactly two realisations and
   no freedom of its own.
3. Devanagari input must be refused, not silently mixed. The target is
   Romanised Hinglish; mixed-script output would be neither, and the failure
   would only show up as bad model output much later.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs.data import codemix  # noqa: E402

FIXTURE = REPO_ROOT / "data" / "codemix" / "parallel_fixture.tsv"


def tiny_corpus():
    return [
        (["i", "am", "going", "home"], ["main", "ghar", "ja", "raha", "hoon"]),
        (["he", "is", "going", "home"], ["woh", "ghar", "ja", "raha", "hai"]),
        (["i", "am", "reading"], ["main", "padh", "raha", "hoon"]),
    ]


class ReadParallelTest(unittest.TestCase):

    def _write(self, text):
        d = TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "pairs.tsv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_pairs_and_skips_comments_and_header(self):
        path = self._write("english\thindi_roman\n# a note\nhello\tnamaste\n")
        self.assertEqual(codemix.read_parallel(path), [(["hello"], ["namaste"])])

    def test_devanagari_is_refused_with_a_reason(self):
        path = self._write("hello\tनमस्ते दोस्त\n")
        with self.assertRaises(codemix.CodeMixError) as ctx:
            codemix.read_parallel(path)
        self.assertIn("Dakshina", str(ctx.exception))

    def test_empty_file_raises(self):
        with self.assertRaises(codemix.CodeMixError):
            codemix.read_parallel(self._write("# only a comment\n"))

    def test_the_committed_fixture_parses(self):
        pairs = codemix.read_parallel(FIXTURE)
        self.assertGreaterEqual(len(pairs), 25)
        for english, hindi in pairs:
            self.assertTrue(english and hindi)


class AlignmentTest(unittest.TestCase):

    def test_em_is_deterministic(self):
        a = codemix.align(tiny_corpus(), iterations=5)
        b = codemix.align(tiny_corpus(), iterations=5)
        self.assertEqual({k: round(v, 10) for k, v in a.items() if v},
                         {k: round(v, 10) for k, v in b.items() if v})

    def test_em_learns_a_repeated_pair(self):
        """'ghar' appears only with 'home', so it should prefer it."""
        t = codemix.align(tiny_corpus(), iterations=20)
        scores = {e: t[("ghar", e)] for e in ("home", "going", "reading")}
        self.assertEqual(max(scores, key=scores.get), "home")

    def test_alignment_needs_hindi_tokens(self):
        with self.assertRaises(codemix.CodeMixError):
            codemix.align([(["hello"], [])])

    def test_coverage_counts_linked_tokens(self):
        self.assertEqual(codemix.coverage([(0, 0), (None, 1)]), 0.5)
        self.assertEqual(codemix.coverage([]), 0.0)


class BlocksTest(unittest.TestCase):

    def test_spans_are_deduplicated(self):
        """Many-to-one links must not repeat an English token in a block."""
        en = ["did", "finish"]
        hi = ["nahi", "kiya", "khatam"]
        links = [(0, 0), (0, 1), (1, 2)]
        spans = codemix.blocks(en, hi, links)
        for en_span, hi_span in spans:
            self.assertEqual(len(en_span), len(set(en_span)))
            self.assertEqual(len(hi_span), len(set(hi_span)))

    def test_a_crossing_link_opens_a_new_block(self):
        en, hi = ["a", "b"], ["B", "A"]
        spans = codemix.blocks(en, hi, [(1, 0), (0, 1)])
        self.assertGreaterEqual(len(spans), 2)

    def test_monotonic_alignment_stays_one_block(self):
        en, hi = ["a", "b"], ["A", "B"]
        self.assertEqual(len(codemix.blocks(en, hi, [(0, 0), (1, 1)])), 1)

    def test_every_english_token_is_claimed_by_some_block(self):
        en, hi = ["a", "b", "c"], ["A", "C"]
        spans = codemix.blocks(en, hi, [(0, 0), (2, 1)])
        claimed = {i for en_span, _ in spans for i in en_span}
        self.assertEqual(claimed, {0, 1, 2})


class GenerationTest(unittest.TestCase):

    def setUp(self):
        self.en = ["the", "boy", "is", "reading"]
        self.hi = ["ladka", "padh", "raha", "hai"]
        self.spans = [([0, 1], [0]), ([2, 3], [1, 2, 3])]

    def test_candidates_exclude_the_monolingual_realisations(self):
        texts = {c["text"] for c in codemix.candidates(self.en, self.hi, self.spans)}
        self.assertNotIn(" ".join(self.en), texts)
        self.assertNotIn(" ".join(self.hi), texts)

    def test_two_blocks_give_two_mixed_realisations(self):
        self.assertEqual(len(codemix.candidates(self.en, self.hi, self.spans)), 2)

    def test_a_single_block_cannot_be_mixed(self):
        self.assertEqual(codemix.candidates(self.en, self.hi, [([0, 1], [0])]), [])

    def test_block_explosion_is_refused(self):
        spans = [([i], [i]) for i in range(20)]
        self.assertEqual(codemix.candidates(list("x" * 20), list("y" * 20), spans), [])

    def test_switch_point_fraction_definition(self):
        self.assertEqual(codemix.switch_point_fraction(["en", "hi"], 5), 0.25)
        self.assertEqual(codemix.switch_point_fraction(["en"], 1), 0.0)


class MatchDistributionTest(unittest.TestCase):

    def pool(self, spfs):
        return [{"spf": s, "text": "t{}".format(i)} for i, s in enumerate(spfs)]

    def test_it_moves_the_mean_toward_the_target(self):
        pool = self.pool([0.1, 0.2, 0.25, 0.9, 1.0])
        chosen = codemix.match_distribution(pool, 0.24, 2, seed=42)
        mean = sum(c["spf"] for c in chosen) / len(chosen)
        self.assertLess(abs(mean - 0.24), 0.1)

    def test_running_batch_state_is_honoured(self):
        """A batch already above target should be pulled down, not ignored."""
        pool = self.pool([0.1, 0.9])
        chosen = codemix.match_distribution(pool, 0.3, 1, seed=1,
                                            running=(2.0, 2))
        self.assertEqual(chosen[0]["spf"], 0.1)

    def test_it_is_deterministic(self):
        pool = self.pool([0.1, 0.3, 0.5, 0.7])
        a = codemix.match_distribution(pool, 0.4, 3, seed=7)
        b = codemix.match_distribution(pool, 0.4, 3, seed=7)
        self.assertEqual([c["text"] for c in a], [c["text"] for c in b])

    def test_it_never_returns_more_than_asked(self):
        pool = self.pool([0.1, 0.2, 0.3])
        self.assertEqual(len(codemix.match_distribution(pool, 0.2, 2, seed=1)), 2)

    def test_empty_pool_is_safe(self):
        self.assertEqual(codemix.match_distribution([], 0.2, 3, seed=1), [])


class EndToEndTest(unittest.TestCase):

    def setUp(self):
        self.pairs = codemix.read_parallel(FIXTURE)
        self.rows, self.stats = codemix.generate(
            self.pairs, target_mean_spf=0.2398, per_sentence=1, seed=42)

    def test_it_produces_output(self):
        self.assertTrue(self.rows)
        self.assertEqual(self.stats["rows_out"], len(self.rows))

    def test_the_batch_hits_the_target(self):
        self.assertTrue(self.stats["spf_within_0.05_of_target"],
                        "mean SPF {} missed target {}".format(
                            self.stats["mean_spf"], self.stats["target_mean_spf"]))

    def test_no_output_repeats_a_token_run(self):
        """The 'did did did' regression."""
        for row in self.rows:
            tokens = row["codemixed"].split()
            for a, b, c in zip(tokens, tokens[1:], tokens[2:]):
                self.assertFalse(a == b == c,
                                 "repeated run in: {}".format(row["codemixed"]))

    def test_output_is_actually_mixed(self):
        for row in self.rows:
            self.assertNotEqual(row["codemixed"], row["english"])
            self.assertNotEqual(row["codemixed"], row["hindi"])

    def test_it_is_deterministic(self):
        rows, _stats = codemix.generate(
            self.pairs, target_mean_spf=0.2398, per_sentence=1, seed=42)
        self.assertEqual([r["codemixed"] for r in rows],
                         [r["codemixed"] for r in self.rows])

    def test_pool_utilisation_is_reported(self):
        self.assertIn("pool_utilisation", self.stats)
        self.assertLessEqual(self.stats["pool_utilisation"], 1.0)


if __name__ == "__main__":
    unittest.main()
