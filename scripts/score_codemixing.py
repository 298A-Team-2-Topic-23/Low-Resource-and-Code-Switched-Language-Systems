#!/usr/bin/env python3
"""
Measure how much a system's output actually code-switches.

chrF++ cannot answer this question, and that matters more here than it looks.
English and Hinglish share most of their English words, so a system that copies
the English source through unchanged still earns substantial chrF++ against a
Hinglish reference. The first zero-shot run on Qwen2.5-7B did exactly that:

  source : install the standard and TSC pumps
  output : install the standard aur TSC pumps
  human  : "install the standard aur TSC pumps" -- but most outputs were
           verbatim English

So this reports, for every system and for the human references measured the
same way, the code-mixing statistics section 3.6 already uses on the corpus:
CMI, switch-point fraction, M-index, burstiness and the fraction of sentences
that are mixed at all. The reference row is the target; a system far below it
is not producing the task's output, whatever its chrF++ says.

The tagger is `lrcs.data.clean.tag_tokens`, the same LinCE-style tagger the
pipeline uses, so these figures are comparable with `reports/data_statistics.json`
rather than being a second, incompatible measurement.

Usage
-----
  python3 scripts/score_codemixing.py \\
      --sources data/sft/hinge/test_references.jsonl \\
      --hyp "M1 zero-shot=results/m1.test.txt" \\
      --hyp "M2 LoRA=results/m2.s42.test.txt"
"""

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs.analysis.codemixing import corpus_stats  # noqa: E402
from lrcs.data.clean import hindi_markers, tag_tokens  # noqa: E402
from lrcs.lexicon import DEFAULT_LEXICON, load_variant_groups  # noqa: E402

KEYS = ("n_sentences", "tagger_coverage", "cmi_mean_all", "cmi_mean_mixed_only",
        "frac_sentences_mixed", "switch_point_fraction", "m_index", "burstiness")


def measure(pairs, markers):
    """pairs: [(english_source, candidate_text)]"""
    tag_lists = [[t for _, t in tag_tokens(cand, src, markers)] for src, cand in pairs]
    return corpus_stats(tag_lists)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--sources", default=str(REPO_ROOT / "data" / "sft" / "hinge"
                                            / "test_references.jsonl"))
    p.add_argument("--hyp", action="append", default=[], metavar="NAME=PATH",
                   help="a system's hypotheses, one line per source (repeatable)")
    p.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    p.add_argument("--out", default=str(REPO_ROOT / "reports" / "codemixing_systems.json"))
    args = p.parse_args(argv)

    markers = hindi_markers(load_variant_groups(args.lexicon))

    sources, ref_sets = [], []
    with open(args.sources, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                obj = json.loads(line)
                sources.append(obj["english"])
                ref_sets.append(obj.get("references", []))

    rows = OrderedDict()

    # The human references, measured identically. Every reference counts, so a
    # source with five renderings contributes five observations of how people
    # actually mix -- this row is a target, not a system score.
    ref_pairs = [(src, r) for src, refs in zip(sources, ref_sets) for r in refs]
    rows["human references (target)"] = measure(ref_pairs, markers)

    # The English sources themselves: the floor. A system scoring here has
    # produced no code-switching at all.
    rows["English source (floor)"] = measure(list(zip(sources, sources)), markers)

    for spec in args.hyp:
        if "=" not in spec:
            raise SystemExit("--hyp takes NAME=PATH, got {!r}".format(spec))
        name, path = spec.split("=", 1)
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        if len(lines) != len(sources):
            raise SystemExit(
                "{}: {} hypothesis lines against {} sources. The harness is "
                "line-aligned; a mismatch means the wrong file or a newline in "
                "an output.".format(path, len(lines), len(sources)))
        rows[name.strip()] = measure(list(zip(sources, lines)), markers)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {k: {kk: v[kk] for kk in KEYS} for k, v in rows.items()},
        indent=2) + "\n", encoding="utf-8")

    width = max(len(k) for k in rows)
    print("\n{:<{w}} {:>6} {:>8} {:>8} {:>8} {:>8} {:>8}".format(
        "system", "n", "CMI", "CMI mix", "% mixed", "SPF", "M-index", w=width))
    print("-" * (width + 56))
    for name, s in rows.items():
        print("{:<{w}} {:>6,} {:>8.2f} {:>8.2f} {:>7.1%} {:>8.4f} {:>8.4f}".format(
            name, s["n_sentences"], s["cmi_mean_all"], s["cmi_mean_mixed_only"],
            s["frac_sentences_mixed"], s["switch_point_fraction"], s["m_index"],
            w=width))

    print("\nCMI is Das & Gambaeck's Code-Mixing Index; SPF is the switch-point "
          "fraction.\nThe floor row is the English source scored as if it were the "
          "output: a system\nnear it is not code-switching, however well it scores "
          "on chrF++.")
    print("\nwrote {}".format(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
