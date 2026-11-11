#!/usr/bin/env python3
"""
Before-and-after audit of the normalised-chrF++ metric.  [Linear 298-78]

PR #44 (298-59) replaced the harness's regex spelling rules with a lookup against
the spelling-variant lexicon. This script makes that change auditable, on three
levels, and writes the result to reports/normalisation_audit.{json,md}:

  1. Groups. How many of the 72 lexicon groups each normaliser collapses to one
     form, and how many of the 28 groups with two or more spellings attested in
     the real corpus.
  2. Token occurrences. On the real HinGE corpus, how many of the non-canonical
     spellings each normaliser maps to their group's canonical form. Measured on
     the 15 most frequent groups, whose per-form counts are committed in
     reports/data_statistics.json; they hold 73% of all lexicon occurrences.
  3. Scores on fixed, committed files. Raw, case-folded, and normalised chrF++
     under both normalisers on (a) evaluation/demo, the harness's own example
     outputs, and (b) the eight human references HinGE gives for one source
     sentence (reports/samples/hinge/transformed.md), each scored against every
     other: human-against-human, so any normalisation gain is spelling alone.

The old rules are reproduced verbatim below so the comparison runs against the
code that actually shipped, not a paraphrase of it.

  python scripts/audit_normalisation.py
"""

import importlib.util
import itertools
import json
import re
import statistics
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# evaluation/run_eval.py before 298-59 (commit 0ac53f8), unchanged.
OLD_RULES = [
    (re.compile(r"(.)\1{2,}"), r"\1"),
    (re.compile(r"aa+"), "a"),
    (re.compile(r"ee+"), "i"),
    (re.compile(r"ii+"), "i"),
    (re.compile(r"oo+"), "u"),
    (re.compile(r"uu+"), "u"),
    (re.compile(r"n\b"), ""),
    (re.compile(r"h(?=[bcdfgjklmnpqrstvwxyz])"), ""),
    (re.compile(r"\s+"), " "),
]
_OLD_PUNCT = re.compile(r"[^\w\sऀ-ॿ]", re.UNICODE)

# Words outside the lexicon that the old n-at-word-end and h-before-consonant rules damaged.
CORRUPTION_PROBES = ["khyal", "sahna", "pahle", "bahna", "kahna", "rehna", "dhyan", "vyakhya"]


def old_normalise(text):
    t = unicodedata.normalize("NFC", text).lower()
    t = _OLD_PUNCT.sub(" ", t)
    for pat, rep in OLD_RULES:
        t = pat.sub(rep, t)
    return t.strip()


def load_harness():
    spec = importlib.util.spec_from_file_location("run_eval", ROOT / "evaluation" / "run_eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def group_collapse(ev, groups, attested):
    out = {}
    for name, norm in (("before", old_normalise), ("after", ev.normalise)):
        collapsed = {g for g, forms in groups.items() if len({norm(f) for f in forms}) == 1}
        out[name] = {"lexicon_groups": len(collapsed), "of_lexicon": len(groups),
                     "attested_2plus": len(collapsed & attested), "of_attested_2plus": len(attested)}
    return out


def occurrence_collapse(ev, top_groups):
    out = {}
    for name, norm in (("before", old_normalise), ("after", ev.normalise)):
        total = non_canonical = mapped = 0
        for g in top_groups:
            canon = norm(g["group"])
            for form, n in g["forms"].items():
                total += n
                if form != g["group"]:
                    non_canonical += n
                    mapped += n if norm(form) == canon else 0
        out[name] = {"occurrences": total, "non_canonical": non_canonical,
                     "non_canonical_mapped_to_canonical": mapped,
                     "share_mapped": round(mapped / max(non_canonical, 1), 4)}
    return out


def score_pairs(ev, hyps, refs):
    norm_old = ev._sacre_stats(ev._CHRF, [old_normalise(h) for h in hyps],
                               [old_normalise(r) for r in refs])
    stats = ev.sentence_stats(hyps, refs)
    return {"chrf++": round(ev.score_from_stats("chrf++", stats["chrf++"]), 3),
            "chrf++_fold": round(ev.score_from_stats("chrf++", stats["chrf++_fold"]), 3),
            "chrf++_norm_before": round(ev.score_from_stats("chrf++", norm_old), 3),
            "chrf++_norm_after": round(ev.score_from_stats("chrf++", stats["chrf++_norm"]), 3)}


def row3_references(path):
    """The eight references of HinGE source row 3, from the committed sample."""
    refs, in_table = [], False
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("## Reference-list expansion"):
            in_table = True
        elif line.startswith("## ") and in_table:
            break
        elif in_table and line.startswith("| ") and not line.startswith("| id"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 4 and cells[1].isdigit():
                refs.append(cells[3])
    return refs


def audit():
    ev = load_harness()
    stats = json.loads((ROOT / "reports" / "data_statistics.json").read_text(encoding="utf-8"))
    sv = stats["spelling_variance"]
    attested = {g["group"] for g in sv["top_groups"] if g["distinct_forms"] >= 2}
    groups = ev._GROUPS

    demo = ROOT / "evaluation" / "demo"
    demo_refs = demo.joinpath("ref.hinglish.txt").read_text(encoding="utf-8").splitlines()
    demo_scores = {}
    for seed in (1, 2):
        hyps = demo.joinpath(f"hyp.seed{seed}.txt").read_text(encoding="utf-8").splitlines()
        demo_scores[f"seed{seed}"] = score_pairs(ev, hyps, demo_refs)

    refs8 = row3_references(ROOT / "reports" / "samples" / "hinge" / "transformed.md")
    pairs = list(itertools.permutations(refs8, 2))
    human = score_pairs(ev, [a for a, _ in pairs], [b for _, b in pairs])

    return {
        "lexicon": str(ev.DEFAULT_LEXICON.relative_to(ROOT)),
        "groups": group_collapse(ev, groups, attested),
        "groups_attested_2plus_in_hinge": sv["groups_with_2plus_forms"],
        "groups_attested_2plus_with_committed_counts": len(attested),
        "occurrences_top15": occurrence_collapse(ev, sv["top_groups"]),
        "occurrences_top15_share_of_all": round(
            sum(g["occurrences"] for g in sv["top_groups"]) / sv["lexicon_token_occurrences"], 4),
        "corruption_probes": {w: {"before": old_normalise(w), "after": ev.normalise(w)}
                              for w in CORRUPTION_PROBES},
        "scores": {"evaluation/demo": demo_scores,
                   "hinge_row3_reference_pairs": dict(human, pairs=len(pairs), references=len(refs8))},
    }


def to_markdown(a):
    g, o = a["groups"], a["occurrences_top15"]
    lines = [
        "# Normalised chrF++: before and after the lexicon lookup",
        "",
        "Generated by `scripts/audit_normalisation.py` (298-78). Do not edit by hand.",
        "",
        "*Before* is the regex normaliser `evaluation/run_eval.py` used until 298-59; *after* is",
        f"the lookup against `{a['lexicon']}` that replaced it.",
        "",
        "## Collapse",
        "",
        "| Measure | Before | After |",
        "|---|---|---|",
        f"| Lexicon groups collapsed to one form | {g['before']['lexicon_groups']} of {g['before']['of_lexicon']}"
        f" | {g['after']['lexicon_groups']} of {g['after']['of_lexicon']} |",
        f"| Of the groups with 2+ spellings in the top 15 real-corpus groups | "
        f"{g['before']['attested_2plus']} of {g['before']['of_attested_2plus']} | "
        f"{g['after']['attested_2plus']} of {g['after']['of_attested_2plus']} |",
        f"| Non-canonical occurrences mapped to canonical, top 15 groups | "
        f"{o['before']['non_canonical_mapped_to_canonical']} of {o['before']['non_canonical']} "
        f"({o['before']['share_mapped']:.1%}) | {o['after']['non_canonical_mapped_to_canonical']} of "
        f"{o['after']['non_canonical']} ({o['after']['share_mapped']:.1%}) |",
        "",
        f"The real corpus attests {a['groups_attested_2plus_in_hinge']} groups with two or more spellings. Per-form"
        f" counts are committed for the 15 most frequent groups, which hold"
        f" {a['occurrences_top15_share_of_all']:.0%} of all lexicon occurrences, so the occurrence row and the"
        " second group row are measured on those.",
        "",
        "## Corruption",
        "",
        "Correct words outside the lexicon, rewritten by the old n-at-word-end and h-before-consonant rules.",
        "",
        "| Word | Before | After |",
        "|---|---|---|",
    ]
    lines += [f"| `{w}` | `{v['before']}` | `{v['after']}` |" for w, v in a["corruption_probes"].items()]
    lines += ["", "## Scores on fixed, committed files", "",
              "| File | chrF++ | chrF++ folded | Normalised, before | Normalised, after |", "|---|---|---|---|---|"]
    for name, s in a["scores"]["evaluation/demo"].items():
        lines.append(f"| `evaluation/demo`, {name} | {s['chrf++']} | {s['chrf++_fold']} | "
                     f"{s['chrf++_norm_before']} | {s['chrf++_norm_after']} |")
    h = a["scores"]["hinge_row3_reference_pairs"]
    lines.append(f"| HinGE row 3: {h['references']} human references, {h['pairs']} ordered pairs | "
                 f"{h['chrf++']} | {h['chrf++_fold']} | {h['chrf++_norm_before']} | {h['chrf++_norm_after']} |")
    lines += ["", "The spelling gap the harness reports is *normalised after* minus *folded*.", ""]
    return "\n".join(lines)


def main():
    a = audit()
    out = ROOT / "reports"
    (out / "normalisation_audit.json").write_text(json.dumps(a, indent=2, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    md = to_markdown(a)
    (out / "normalisation_audit.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
