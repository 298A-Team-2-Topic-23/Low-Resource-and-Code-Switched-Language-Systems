#!/usr/bin/env python3
"""
Check that every number in section 3.6 traces to the committed artifact it cites.  [298-86]

Section 3.6 says: "Every figure in this section is read from a committed artifact
... Nothing here is typed in by hand." This script tests that claim. Each entry
in CLAIMS names the text as it appears in the section, the artifact, and how to
read the value from it. A claim fails if the text is gone from the section (the
section changed and this list must follow) or if the artifact, rounded the way
the section rounds it, gives a different number.

    python scripts/audit_section_3_6.py
    python scripts/audit_section_3_6.py --out reports/audit/section_3_6_trace.json

Exit 0 if every claim traces, 1 if any does not. A failure is a finding to fix in
the section or the artifact, not in this list.
"""

import argparse
import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SECTION = REPO_ROOT / "docs" / "workbook2" / "section_3_6.md"

STATS = "reports/data_statistics.json"
FIG = "reports/workbook2_figures.json"
FERT = "reports/fertility.csv"


def _json(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _get(obj, path):
    for key in path.split("."):
        obj = obj[key]
    return obj


def _fert(root, slice_name, column):
    with open(str(root / FERT), encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["slice"] == slice_name:
                return float(row[column])
    raise KeyError("{}: no slice {}".format(FERT, slice_name))


def _tags_total(stats):
    return sum(stats["code_mixing"]["tag_counts"].values())


def _ratio(split, stats):
    return 100.0 * stats["splits"][split]["records"] / stats["attrition"]["kept"]


def _top(stats, group, field):
    for g in stats["spelling_variance"]["top_groups"]:
        if g["group"] == group:
            return g[field]
    raise KeyError(group)


# (text in section 3.6, artifact, reader(stats-or-artifact json) -> value, scale, decimals)
# scale converts a fraction to the percentage the section prints.
def S(path):
    return lambda a: _get(a, path)


CLAIMS = [
    ("1,976 file rows", STATS, S("provenance.rows_in_file"), 1, 0),
    ("**4,799** records", STATS, S("provenance.records"), 1, 0),
    ("| Pre-processed | **4,674**", STATS, S("attrition.kept"), 1, 0),
    ("125 records removed", STATS, S("attrition.removed_total"), 1, 0),
    ("**3,738 / 468 / 468**", STATS, lambda a: "{:,} / {} / {}".format(
        a["splits"]["train"]["records"], a["splits"]["dev"]["records"],
        a["splits"]["test"]["records"]), None, None),
    ("runs in 11.96 seconds", STATS, S("elapsed_seconds"), 1, 2),
    ("ingest 0.23 s", STATS, S("timings_seconds.ingest"), 1, 2),
    ("clean 0.54 s", STATS, S("timings_seconds.clean"), 1, 2),
    ("split\n9.16 s", STATS, S("timings_seconds.split"), 1, 2),
    ("figures 2.02 s", STATS, S("timings_seconds.eda"), 1, 2),
    ("English averages 15.24 words", STATS, S("lengths_words.english.mean"), 1, 2),
    ("Hinglish averages 15.87", STATS, S("lengths_words.hinglish.mean"), 1, 2),
    ("word ratio is 1.062", STATS, S("lengths_words.hinglish_to_english_ratio_mean"), 1, 3),
    ("6,780 types", STATS, S("vocabulary.english_types"), 1, 0),
    ("71,217 tokens", STATS, S("vocabulary.english_tokens"), 1, 0),
    ("**13,204 types", STATS, S("vocabulary.hinglish_types"), 1, 0),
    ("74,165 tokens**", STATS, S("vocabulary.hinglish_tokens"), 1, 0),
    ("type-token ratio of 0.178", STATS, S("vocabulary.hinglish_type_token_ratio"), 1, 3),
    ("Mean CMI is 25.34", STATS, S("code_mixing.cmi_mean_all"), 1, 2),
    ("29.42 across the\nmixed ones", STATS, S("code_mixing.cmi_mean_mixed_only"), 1, 2),
    ("86.1% of sentences are mixed", STATS, S("code_mixing.frac_sentences_mixed"), 100, 1),
    ("Switch-point fraction is 0.240", STATS, S("code_mixing.switch_point_fraction"), 1, 3),
    ("0.272 per sentence", STATS, S("code_mixing.spf_mean_per_sentence"), 1, 3),
    ("10,861 switch points", STATS, S("code_mixing.n_switch_points"), 1, 0),
    ("3.22 tokens", STATS, S("code_mixing.mean_span_length"), 1, 2),
    ("M-index is 0.693", STATS, S("code_mixing.m_index"), 1, 3),
    ("burstiness 0.056", STATS, S("code_mixing.burstiness"), 1, 3),
    ("covering **68.2%**", STATS, S("code_mixing.tagger_coverage"), 100, 1),
    ("**19,382 of", STATS, S("code_mixing.tag_counts.unk"), 1, 0),
    ("83,922** are `unk`", STATS, _tags_total, 1, 0),
    ("1,938 distinct sources", STATS, S("grouping.unique_sources"), 1, 0),
    ("a mean of 2.41 each", STATS, S("references_per_source.mean"), 1, 2),
    ("| Source sentences | 26 | 1,470 | 166 | 210 | 37 | 21 | 5 | 3 |", STATS,
     lambda a: "| Source sentences | " + " | ".join(
         "{:,}".format(a["references_per_source"]["distribution"][str(k)]) for k in range(1, 9))
     + " |", None, None),
    ("**76% of sources have exactly two references**", FIG, S("imbalance.modal_share"), 1, 0),
    ("a 14% tail", FIG, S("imbalance.four_or_more_share"), 1, 0),
    ("79.98 / 10.01 / 10.01", STATS, lambda a: "{:.2f} / {:.2f} / {:.2f}".format(
        _ratio("train", a), _ratio("dev", a), _ratio("test", a)), None, None),
    ("of 72 spelling-variant groups", STATS, S("spelling_variance.lexicon_groups"), 1, 0),
    ("68 are\nobserved", STATS, S("spelling_variance.groups_observed"), 1, 0),
    ("only **28 carry two or more", STATS, S("spelling_variance.groups_with_2plus_forms"), 1, 0),
    ("13% of their", STATS, S("spelling_variance.non_canonical_share_overall"), 100, 0),
    ("3,812 occurrences", STATS, S("spelling_variance.lexicon_token_occurrences"), 1, 0),
    ("burden metric of 1.832", FERT, lambda root: _fert(root, "en", "spelling_variant_burden"), 1, 3),
    ("Pearson **r = +0.29**", FIG, S("correlations.variants_vs_tokens.pearson"), 1, 2),
    ("Spearman **ρ = +0.32**", FIG, S("correlations.variants_vs_tokens.spearman"), 1, 2),
    ("Pearson **r = −0.15**", FIG, S("correlations.frequency_vs_non_canonical.pearson"), 1, 2),
    ("Spearman **ρ = −0.10**", FIG, S("correlations.frequency_vs_non_canonical.spearman"), 1, 2),
    ("`hai` occurs 934 times", STATS, lambda a: _top(a, "hai", "occurrences"), 1, 0),
    ("non-canonically 8.8%", STATS, lambda a: _top(a, "hai", "non_canonical_share"), 100, 1),
    ("reach 77% and 90%", STATS, lambda a: "{:.0f}% and {:.0f}%".format(
        100 * _top(a, "phir", "non_canonical_share"), 100 * _top(a, "kahan", "non_canonical_share")),
     None, None),
    ("fertility rising from 1.024 on English", FERT, lambda root: _fert(root, "en", "fertility"), 1, 3),
    ("to 1.501\non Hinglish", FERT, lambda root: _fert(root, "hinglish", "fertility"), 1, 3),
    ("coverage falls from 98.5%", FERT, lambda root: _fert(root, "en", "vocab_coverage"), 100, 1),
    ("to 52.6%", FERT, lambda root: _fert(root, "hinglish", "vocab_coverage"), 100, 1),
]


def _number_in(text):
    """The last number in the claim text, as printed (commas, sign, percent dropped)."""
    import re
    nums = re.findall(r"[−+-]?\d[\d,]*\.?\d*", text)
    return nums[-1].replace(",", "").replace("−", "-") if nums else None


def _format(value, scale, decimals):
    v = value * scale
    if decimals == 0:
        return str(int(round(v)))
    return "{:.{}f}".format(v, decimals)


def check(section_text, root, claims=CLAIMS):
    results = []
    cache = {}
    for text, artifact, read, scale, decimals in claims:
        entry = OrderedDict([("claim", text.replace("\n", " ")), ("artifact", artifact)])
        if text not in section_text:
            entry.update(status="text_missing",
                         note="not found in the section; the claim list is out of date")
            results.append(entry)
            continue
        path = root / artifact
        if not path.exists():
            entry.update(status="artifact_missing")
            results.append(entry)
            continue
        if artifact == FERT:
            value = read(root)
        else:
            if artifact not in cache:
                cache[artifact] = _json(root, artifact)
            value = read(cache[artifact])
        if scale is None:
            ok = str(value) in text
            entry.update(artifact_says=str(value), section_says=text.replace("\n", " "))
        else:
            want = _number_in(text)
            got = _format(value, scale, decimals)
            ok = want is not None and float(want) == float(got)
            entry.update(artifact_says=got, section_says=want)
        entry["status"] = "ok" if ok else "mismatch"
        results.append(entry)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--section", default=str(SECTION))
    ap.add_argument("--root", default=str(REPO_ROOT))
    ap.add_argument("--out", help="write the results as JSON")
    args = ap.parse_args(argv)
    results = check(Path(args.section).read_text(encoding="utf-8"), Path(args.root))
    bad = [r for r in results if r["status"] != "ok"]
    for r in bad:
        print("{:<13} {}  [{}]  section {!r}, artifact {!r}".format(
            r["status"].upper(), r["claim"][:60], r["artifact"],
            r.get("section_says"), r.get("artifact_says")))
    print("{} of {} claims trace to their artifact; {} do not".format(
        len(results) - len(bad), len(results), len(bad)))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        report = OrderedDict([("issue", "298-86"), ("section", "docs/workbook2/section_3_6.md"),
                              ("claims", len(results)), ("ok", len(results) - len(bad)),
                              ("failed", len(bad)), ("results", results)])
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
