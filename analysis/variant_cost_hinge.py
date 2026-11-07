#!/usr/bin/env python3
"""
What spelling variants cost on the real corpus, from committed artifacts only. [298-66]

spelling_variant_burden (analysis/tokenizer_fertility.py) is a property of the tokenizer and
the lexicon: every listed spelling counts once, however rarely anyone writes it. This script
asks the complementary question: weighting each spelling by how often HinGE writers actually
used it, how many tokens does one occurrence cost?

It joins two committed files and needs no corpus, no tokenizer and no GPU:

  reports/data_statistics.json     per-form counts for the top lexicon groups, real HinGE
  reports/fertility.variants.csv   tokens per surface form on Qwen/Qwen2.5-7B-Instruct

Only the groups kept in spelling_variance.top_groups can be weighted, so this is a measurement
over those groups, not over the whole lexicon. Re-running the pipeline with more groups retained
would widen it.

Usage:  python analysis/variant_cost_hinge.py [--out reports/variant_cost_hinge.json]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATS = REPO_ROOT / "reports" / "data_statistics.json"
VARIANTS = REPO_ROOT / "reports" / "fertility.variants.csv"
OUT = REPO_ROOT / "reports" / "variant_cost_hinge.json"


def read_costs(path):
    """Group means and per-form token counts from the tokenizer's variants CSV."""
    means, forms = {}, {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            means[row["group"]] = float(row["mean_tokens"])
            for item in row["detail"].split():
                form, tokens = item.rsplit(":", 1)
                forms[(row["group"], form)] = int(tokens)
    return means, forms


def measure(stats, means, forms):
    if stats.get("synthetic", True):
        sys.exit("refusing to report: data_statistics.json is not from the real corpus")

    occurrences = tokens = 0
    groups = []
    for group in stats["spelling_variance"]["top_groups"]:
        g_occ = g_tok = 0
        for form, count in group["forms"].items():
            if (group["group"], form) not in forms:
                sys.exit("no token cost for {} / {}".format(group["group"], form))
            g_occ += count
            g_tok += count * forms[(group["group"], form)]
        groups.append({
            "group": group["group"],
            "occurrences": g_occ,
            "tokens_per_occurrence": round(g_tok / g_occ, 4),
            "lexicon_mean_tokens": round(means[group["group"]], 4),
        })
        occurrences += g_occ
        tokens += g_tok

    return {
        "source": stats["source"],
        "synthetic": False,
        "tokenizer": "Qwen/Qwen2.5-7B-Instruct",
        "generated_from": {
            "statistics": "reports/data_statistics.json",
            "variants": "reports/fertility.variants.csv",
        },
        "groups_measured": len(groups),
        "lexicon_groups": stats["spelling_variance"]["lexicon_groups"],
        "occurrences": occurrences,
        "share_of_lexicon_occurrences": round(
            occurrences / stats["spelling_variance"]["lexicon_token_occurrences"], 4),
        "tokens_per_occurrence": round(tokens / occurrences, 4),
        "same_groups_lexicon_burden": round(
            sum(g["lexicon_mean_tokens"] for g in groups) / len(groups), 4),
        "whole_lexicon_burden": round(sum(means.values()) / len(means), 4),
        "whole_lexicon_mean_per_form": round(sum(forms.values()) / len(forms), 4),
        "groups": groups,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    means, forms = read_costs(VARIANTS)
    result = measure(json.loads(STATS.read_text(encoding="utf-8")), means, forms)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("{} tokens per occurrence over {} groups ({} occurrences); lexicon burden {}".format(
        result["tokens_per_occurrence"], result["groups_measured"], result["occurrences"],
        result["whole_lexicon_burden"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
