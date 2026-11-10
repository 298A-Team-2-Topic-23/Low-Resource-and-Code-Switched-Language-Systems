import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

from human_eval.gold_agreement import (acceptability, decision, judgements, metadata, pool,
                                       renderings, sample, score)

FIELDS = ["item_id", "english_source", "devanagari_hindi", "romanized_hinglish",
          "needs_review", "notes"]


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class GoldAgreementTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.dir = Path(holder.name)
        self.gold = self.dir / "gold.csv"
        save(self.gold, [{"item_id": "G{:03d}".format(i), "english_source": "Sentence {}".format(i),
                          "devanagari_hindi": "वाक्य {}".format(i),
                          "romanized_hinglish": "GOLD vakya {}".format(i),
                          "needs_review": "no", "notes": ""} for i in range(1, 221)])
        self.out = self.dir / "iaa"

    def fill_renderings(self):
        for who in ("a", "b"):
            rows = read(self.out / "annotator_{}.csv".format(who))
            for i, row in enumerate(rows):
                if who == "a":
                    row["romanized_hinglish"] = "ye nahi hai " + row["english_source"]
                elif i % 2:
                    row["romanized_hinglish"] = "ye nhi hai " + row["english_source"]
                else:
                    row["romanized_hinglish"] = "Ye nahi hai, " + row["english_source"]
            save(self.out / "annotator_{}.csv".format(who), rows)

    def test_sample_is_random_within_the_first_200_and_hides_the_gold_column(self):
        meta = sample(self.gold, self.out)
        self.assertEqual(len(meta["item_ids"]), 100)
        self.assertTrue(all(int(i[1:]) <= 200 for i in meta["item_ids"]))
        self.assertEqual(meta, sample(self.gold, self.dir / "again"))
        sheet = (self.out / "annotator_a.csv").read_text(encoding="utf-8")
        self.assertNotIn("GOLD", sheet)
        self.assertNotIn("वाक्य", sheet)
        self.assertEqual([r["annotator"] for r in read(self.out / "annotators.csv")], ["A", "B"])

    def test_sample_refuses_fewer_than_200_rows(self):
        save(self.gold, read(self.gold)[:150])
        with self.assertRaises(SystemExit):
            sample(self.gold, self.out)

    def test_pool_hides_authorship_and_orders_each_judge_differently(self):
        sample(self.gold, self.out)
        self.fill_renderings()
        self.assertEqual(pool(self.out), 200)
        a, b = read(self.out / "judge_a.csv"), read(self.out / "judge_b.csv")
        self.assertNotIn("author", a[0])
        self.assertEqual({r["judgement_id"] for r in a}, {r["judgement_id"] for r in b})
        self.assertNotEqual([r["judgement_id"] for r in a], [r["judgement_id"] for r in b])
        authors = [r["author"] for r in read(self.out / "pool_key.csv")]
        self.assertEqual(authors.count("A"), 100)

    def test_blank_renderings_and_blank_judgements_are_refused(self):
        sample(self.gold, self.out)
        with self.assertRaises(SystemExit):
            renderings(self.out)
        self.fill_renderings()
        pool(self.out)
        with self.assertRaises(SystemExit):
            judgements(self.out)

    def test_acceptability_reports_alpha_with_raw_agreement_and_self_preference(self):
        key = {"J1": {"author": "A"}, "J2": {"author": "B"}, "J3": {"author": "A"},
               "J4": {"author": "B"}}
        by = {"A": {"J1": True, "J2": False, "J3": True, "J4": True},
              "B": {"J1": True, "J2": False, "J3": False, "J4": True}}
        result = acceptability(by, key)
        self.assertEqual(result["raw_agreement"], 0.75)
        self.assertIsNotNone(result["alpha_nominal"])
        self.assertEqual(result["self_preference"]["A"]["own_accepted"], 1.0)

    def test_uniform_judgements_leave_alpha_undefined_not_perfect(self):
        key = {"J1": {"author": "A"}, "J2": {"author": "B"}}
        result = acceptability({"A": {"J1": True, "J2": True}, "B": {"J1": True, "J2": True}}, key)
        self.assertIsNone(result["alpha_nominal"])
        self.assertIn("undefined", result["decision"])

    def test_decision_follows_the_guideline_thresholds(self):
        self.assertTrue(decision(0.7).startswith("usable"))
        self.assertTrue(decision(0.5).startswith("revise"))
        self.assertTrue(decision(0.2).startswith("retrain"))

    def test_metadata_requires_region_and_first_language(self):
        sample(self.gold, self.out)
        self.assertEqual(metadata(self.out)["missing_region_or_first_language"], ["A", "B"])

    @unittest.skipUnless(importlib.util.find_spec("sacrebleu"), "chrF++ needs sacrebleu")
    def test_score_end_to_end(self):
        sample(self.gold, self.out)
        self.fill_renderings()
        pool(self.out)
        for who in ("a", "b"):
            rows = read(self.out / "judge_{}.csv".format(who))
            for i, row in enumerate(rows):
                row["acceptable"] = "no" if (who == "b" and i % 10 == 0) else "yes"
            save(self.out / "judge_{}.csv".format(who), rows)
        result = score(self.out)
        ceiling = result["ceiling"]
        self.assertLess(ceiling["chrf++"]["mean"], ceiling["chrf++_norm"]["mean"])
        self.assertGreater(ceiling["normalisation_gap"], 0)
        low, high = ceiling["chrf++"]["ci95"]
        self.assertLessEqual(low, ceiling["chrf++"]["mean"])
        self.assertGreaterEqual(high, ceiling["chrf++"]["mean"])
        dis = result["disagreements"]
        self.assertEqual(dis["items_differing"], 50)
        self.assertEqual(dis["suggested_spelling"], 50)
        self.assertTrue((self.out / "results.json").exists())

        rows = read(self.out / "disagreements.csv")
        rows[0]["category"] = "spelling"
        save(self.out / "disagreements.csv", rows)
        self.assertEqual(score(self.out)["disagreements"]["counts"], {"spelling": 1})


if __name__ == "__main__":
    unittest.main()
