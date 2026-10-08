"""Regression tests for split derivation (298-11).

The determinism test is the important one. Clustering previously depended on the
order MinHashLSH returned neighbours in, which varies with PYTHONHASHSEED between
processes, so the same corpus and the same --seed produced different splits on
every run -- and the committed manifest's hashes could not be regenerated on any
machine. Running clustering repeatedly inside one process would not have caught
that, so the test shells out to separate interpreters with hash randomisation
left on, which is the condition that actually failed.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "make_splits.py"

try:
    import datasketch  # noqa: F401
    HAVE_DATASKETCH = True
except ImportError:
    HAVE_DATASKETCH = False


def write_corpus(path, sentences, refs_per_source=3):
    rows = []
    for i, sentence in enumerate(sentences):
        for j in range(refs_per_source):
            rows.append("\t".join([sentence, "hi {}".format(i), "ref {}".format(j)]))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def run_splits(tmp, corpus, outdir):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(corpus),
         "--outdir", str(tmp / outdir), "--manifest-dir", str(tmp / outdir / "m"),
         "--seed", "42"],
        capture_output=True, text=True,
    )


# Lexically varied: no shared template, so char-4-gram similarity between any
# two of these stays well below the clustering threshold. Deliberately not built
# from a slot grammar -- a templated corpus trips the degeneracy guard, which is
# what the second test covers.
DIVERSE = [
    "the harbour froze over before anyone noticed",
    "she repainted the kitchen a deep olive green",
    "lightning knocked out power across three districts",
    "my grandfather collected stamps from portugal",
    "the bakery on wilson street closes at noon",
    "nobody claimed the umbrella left by the door",
    "we hiked until the trail disappeared entirely",
    "his violin needed restringing after the recital",
    "forty penguins waddled past the research hut",
    "the contract expired while she was travelling",
    "rain flooded the basement and ruined the carpets",
    "a stray cat adopted the entire fire station",
    "they cancelled the ferry because of high winds",
    "the museum acquired a rare bronze figurine",
    "corn prices collapsed after the second harvest",
    "her thesis defence was moved to september",
    "an old oak fell across the railway line",
    "the pharmacy ran out of antihistamines",
    "tourists crowded the lighthouse all summer",
    "he forgot his passport at the hotel desk",
    "the orchestra rehearsed until well past midnight",
    "snow buried the greenhouse under a metre of drift",
    "our landlord replaced every window last spring",
    "the printer jammed halfway through the report",
    "she inherited a vineyard she had never visited",
    "wolves returned to the valley after decades",
    "the committee rejected all four proposals",
    "a power surge destroyed the laboratory freezer",
    "fishermen reported unusually warm water offshore",
    "the bridge reopened six months behind schedule",
    "someone planted sunflowers along the motorway",
    "his appeal was heard by a different judge",
    "the festival moved indoors because of hail",
    "archaeologists uncovered a roman drainage system",
    "her bicycle was stolen outside the library",
    "the volcano has been dormant for two centuries",
    "we adopted a greyhound from the racing track",
    "the newspaper folded after ninety years",
    "bees swarmed the orchard in early april",
    "a courier delivered the wrong package twice",
]

# Deliberate near-duplicate families of three or more. Pairs are not enough:
# with only two members there is a single candidate union and the result is
# stable by accident. Clusters of three or more are where the order LSH returns
# neighbours in decides which unions happen first, which is the bug this test
# exists to catch.
DIVERSE += [
    "the harbour froze over before anybody noticed",
    "the harbour froze over before any one noticed",
    "the harbour had frozen over before anyone noticed",

    "she repainted the kitchen a deep olive colour",
    "she repainted the kitchen in deep olive green",
    "she had repainted the kitchen a deep olive green",

    "we hiked until the trail disappeared completely",
    "we hiked until the trail had disappeared entirely",
    "we kept hiking until the trail disappeared entirely",

    "her bicycle was stolen outside the library again",
    "her bicycle got stolen outside the library",
    "his bicycle was stolen outside the library",
]

# Differs only by a number, so every sentence is a near-duplicate of its
# neighbours and transitive chaining merges the whole corpus into one cluster.
TEMPLATED = [
    "the quick meeting number {} was moved to friday afternoon".format(i)
    for i in range(120)
]


@unittest.skipUnless(HAVE_DATASKETCH, "datasketch not installed")
class MakeSplitsTest(unittest.TestCase):

    def test_same_seed_reproduces_byte_identical_splits(self):
        """The manifest claims anyone can regenerate byte-identical splits."""
        with TemporaryDirectory() as td:
            tmp = Path(td)
            corpus = tmp / "corpus.tsv"
            write_corpus(corpus, DIVERSE)

            digests = []
            for run in range(3):
                result = run_splits(tmp, corpus, "run{}".format(run))
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads(
                    (tmp / "run{}".format(run) / "m" / "hinge_split_manifest.json")
                    .read_text(encoding="utf-8")
                )
                digests.append(
                    tuple(manifest["splits"][s]["sha256"] for s in ("train", "dev", "test"))
                )

            self.assertEqual(
                len(set(digests)), 1,
                "same input and seed produced different splits across runs: {}".format(digests),
            )

    def test_degenerate_clustering_aborts_without_writing(self):
        """Chaining can collapse a templated corpus into one cluster. That leaves
        train and dev empty while disjointness still passes, so it has to fail
        loudly rather than write a manifest nobody can trust."""
        with TemporaryDirectory() as td:
            tmp = Path(td)
            corpus = tmp / "templated.tsv"
            write_corpus(corpus, TEMPLATED)

            result = run_splits(tmp, corpus, "out")
            self.assertNotEqual(result.returncode, 0,
                                "degenerate split was accepted:\n" + result.stdout)
            self.assertFalse(
                (tmp / "out" / "m" / "hinge_split_manifest.json").exists(),
                "a manifest was written for a degenerate split",
            )


if __name__ == "__main__":
    unittest.main()
