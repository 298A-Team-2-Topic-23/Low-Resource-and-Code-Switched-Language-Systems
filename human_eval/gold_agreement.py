#!/usr/bin/env python3
"""
Inter-annotator agreement on the gold set.  [298-80, owner: Jenil]

Implements human_eval/iaa/PROTOCOL.md, which fixed the design before any item existed.

  sample   100 random items (seed 80) from the first 200 gold rows -> blank sheets for
           annotators A and B, and a metadata sheet with no names on it
  pool     both annotators' renderings, shuffled with authorship hidden -> one judging sheet
           per judge, and a sealed key
  score    acceptability alpha, self-preference, the human chrF++ ceiling (raw and normalised,
           both directions, bootstrap interval) and the disagreement sheet

Usage
-----
  python human_eval/gold_agreement.py sample --gold data/goldtestset/gold_set.csv
  python human_eval/gold_agreement.py pool
  python human_eval/gold_agreement.py score
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
for extra in (REPO_ROOT, REPO_ROOT / "evaluation", HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from agreement import krippendorff_alpha  # noqa: E402
from data.goldtestset.validate_gold_set import validate  # noqa: E402

DEFAULT_DIR = HERE / "iaa"
SEED = 80
N_ITEMS = 100
FROM_FIRST = 200
ANNOTATORS = ("a", "b")
RENDER_COLUMNS = ("item_id", "english_source", "romanized_hinglish", "needs_review", "notes")
JUDGE_COLUMNS = ("judgement_id", "english_source", "rendering", "acceptable", "notes")
META_COLUMNS = ("annotator", "region", "first_language", "other_languages")
CATEGORIES = ("spelling", "lexical", "switching", "error")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def sample(gold, out_dir, n=N_ITEMS, first=FROM_FIRST, seed=SEED):
    errors = validate(Path(gold))
    if errors:
        sys.exit("gold set does not validate:\n  " + "\n  ".join(errors))
    rows = read_csv(gold)
    if len(rows) < first:
        sys.exit("need the first {} gold rows, found {}".format(first, len(rows)))
    chosen = random.Random(seed).sample(rows[:first], n)
    chosen.sort(key=lambda r: r["item_id"])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blank = [{"item_id": r["item_id"], "english_source": r["english_source"],
              "romanized_hinglish": "", "needs_review": "", "notes": ""} for r in chosen]
    for who in ANNOTATORS:
        write_csv(out / "annotator_{}.csv".format(who), RENDER_COLUMNS, blank)
    write_csv(out / "annotators.csv", META_COLUMNS,
              [{"annotator": who.upper(), "region": "", "first_language": "",
                "other_languages": ""} for who in ANNOTATORS])
    meta = {"seed": seed, "items": n, "from_first": first, "gold": str(gold),
            "item_ids": [r["item_id"] for r in chosen]}
    (out / "sample.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def renderings(out):
    by = {}
    for who in ANNOTATORS:
        rows = read_csv(out / "annotator_{}.csv".format(who))
        empty = [r["item_id"] for r in rows if not r["romanized_hinglish"].strip()]
        if empty:
            sys.exit("annotator {} has {} blank renderings, first {}".format(
                who.upper(), len(empty), empty[0]))
        by[who] = OrderedDict((r["item_id"], r) for r in rows)
    if list(by["a"]) != list(by["b"]):
        sys.exit("annotator sheets cover different items")
    return by


def pool(out_dir, seed=SEED):
    out = Path(out_dir)
    by = renderings(out)
    units = [{"item_id": item, "author": who.upper(),
              "english_source": by[who][item]["english_source"],
              "rendering": by[who][item]["romanized_hinglish"].strip()}
             for item in by["a"] for who in ANNOTATORS]
    random.Random(seed).shuffle(units)
    for i, unit in enumerate(units, start=1):
        unit["judgement_id"] = "J{:03d}".format(i)
    write_csv(out / "pool_key.csv", ("judgement_id", "item_id", "author"),
              [{k: u[k] for k in ("judgement_id", "item_id", "author")} for u in units])
    # Each judge sees the same renderings in a different order, so order effects do not line up.
    for offset, who in enumerate(ANNOTATORS, start=1):
        order = list(units)
        random.Random(seed + offset).shuffle(order)
        write_csv(out / "judge_{}.csv".format(who), JUDGE_COLUMNS,
                  [{"judgement_id": u["judgement_id"], "english_source": u["english_source"],
                    "rendering": u["rendering"], "acceptable": "", "notes": ""} for u in order])
    return len(units)


def judgements(out):
    by = {}
    for path in sorted(out.glob("judge_*.csv")):
        who = path.stem.split("_", 1)[1].upper()
        rows = read_csv(path)
        bad = [r["judgement_id"] for r in rows
               if r["acceptable"].strip().lower() not in ("yes", "no")]
        if bad:
            sys.exit("judge {} has {} judgements that are not yes/no, first {}".format(
                who, len(bad), bad[0]))
        by[who] = {r["judgement_id"]: r["acceptable"].strip().lower() == "yes" for r in rows}
    if len(by) < 2:
        sys.exit("need at least two judging sheets")
    return by


def acceptability(by, key):
    ids = sorted(key)
    units = [[by[judge][j] for judge in by] for j in ids]
    agree = sum(len(set(u)) == 1 for u in units) / len(units)
    values = [v for u in units for v in u]
    single_value = len(set(values)) == 1
    alpha = None if single_value else round(krippendorff_alpha(units, scale="nominal"), 3)
    self_pref = {}
    for judge in by:
        own = [by[judge][j] for j in ids if key[j]["author"] == judge]
        other = [by[judge][j] for j in ids if key[j]["author"] != judge]
        if own and other:
            self_pref[judge] = {"own_accepted": round(sum(own) / len(own), 3),
                                "other_accepted": round(sum(other) / len(other), 3)}
    return {"judges": sorted(by), "renderings": len(units), "alpha_nominal": alpha,
            "raw_agreement": round(agree, 3),
            "accepted_share": round(sum(values) / len(values), 3),
            "decision": decision(alpha), "self_preference": self_pref}


def decision(alpha):
    if alpha is None:
        return "alpha undefined: every judgement was the same value; report raw agreement"
    if alpha >= 0.67:
        return "usable: continue the 800-item set under guidelines v2"
    if alpha >= 0.40:
        return "revise the guideline sections behind the commonest disagreement; re-judge 30 items"
    return "retrain on shared examples before any further authoring"


def ceiling(a_texts, b_texts, seed=SEED, samples=1000):
    import run_eval
    ab = run_eval.sentence_stats(a_texts, b_texts)
    ba = run_eval.sentence_stats(b_texts, a_texts)
    result = {}
    for metric in ("chrf++", "chrf++_norm"):
        a_on_b = run_eval.score_from_stats(metric, ab[metric])
        b_on_a = run_eval.score_from_stats(metric, ba[metric])
        low, high = run_eval.bootstrap_ci([ab, ba], metric, samples=samples, seed=seed)
        result[metric] = {"a_against_b": round(a_on_b, 3), "b_against_a": round(b_on_a, 3),
                          "mean": round((a_on_b + b_on_a) / 2, 3),
                          "ci95": [round(low, 3), round(high, 3)]}
    result["normalisation_gap"] = round(result["chrf++_norm"]["mean"]
                                        - result["chrf++"]["mean"], 3)
    return result


def disagreements(out, by):
    import run_eval
    path = out / "disagreements.csv"
    existing = {r["item_id"]: r for r in read_csv(path)} if path.exists() else {}
    rows = []
    for item, a in by["a"].items():
        ra, rb = a["romanized_hinglish"].strip(), by["b"][item]["romanized_hinglish"].strip()
        if run_eval.fold(ra) == run_eval.fold(rb):
            continue
        suggested = "spelling" if run_eval.normalise(ra) == run_eval.normalise(rb) else ""
        previous = existing.get(item, {})
        rows.append({"item_id": item, "english_source": a["english_source"], "rendering_a": ra,
                     "rendering_b": rb, "suggested": suggested,
                     "category": previous.get("category", ""), "notes": previous.get("notes", "")})
    write_csv(path, ("item_id", "english_source", "rendering_a", "rendering_b", "suggested",
                     "category", "notes"), rows)
    categories = [r["category"].strip().lower() for r in rows]
    unknown = sorted({c for c in categories if c and c not in CATEGORIES})
    return {"items_differing": len(rows), "items_identical": len(by["a"]) - len(rows),
            "suggested_spelling": sum(r["suggested"] == "spelling" for r in rows),
            "classified": sum(1 for c in categories if c in CATEGORIES),
            "counts": dict(Counter(c for c in categories if c in CATEGORIES)),
            "unknown_categories": unknown}


def metadata(out):
    rows = read_csv(out / "annotators.csv")
    missing = [r["annotator"] for r in rows
               if not (r["region"].strip() and r["first_language"].strip())]
    return {"annotators": rows, "missing_region_or_first_language": missing}


def score(out_dir, seed=SEED):
    out = Path(out_dir)
    by = renderings(out)
    key = {r["judgement_id"]: r for r in read_csv(out / "pool_key.csv")}
    items = list(by["a"])
    result = {
        "items": len(items),
        "acceptability": acceptability(judgements(out), key),
        "ceiling": ceiling([by["a"][i]["romanized_hinglish"].strip() for i in items],
                           [by["b"][i]["romanized_hinglish"].strip() for i in items], seed),
        "disagreements": disagreements(out, by),
        "metadata": metadata(out),
    }
    (out / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("sample", "pool", "score"):
        command = sub.add_parser(name)
        command.add_argument("--dir", default=str(DEFAULT_DIR))
        if name == "sample":
            command.add_argument("--gold", required=True)
    args = ap.parse_args(argv)

    if args.command == "sample":
        meta = sample(args.gold, args.dir)
        print("wrote sheets for {} items to {}".format(meta["items"], args.dir))
    elif args.command == "pool":
        print("wrote judging sheets for {} renderings".format(pool(args.dir)))
    else:
        result = score(args.dir)
        acc, ceil = result["acceptability"], result["ceiling"]
        print("alpha {} | raw agreement {} | accepted {} | {}".format(
            acc["alpha_nominal"], acc["raw_agreement"], acc["accepted_share"], acc["decision"]))
        print("human ceiling chrF++ {} (normalised {}, gap {})".format(
            ceil["chrf++"]["mean"], ceil["chrf++_norm"]["mean"], ceil["normalisation_gap"]))
        if result["metadata"]["missing_region_or_first_language"]:
            print("missing region or first language for:",
                  ", ".join(result["metadata"]["missing_region_or_first_language"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
