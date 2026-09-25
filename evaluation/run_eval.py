#!/usr/bin/env python3
"""One-command evaluation harness for Hindi / Hinglish generation.

Scores one or more hypothesis files (e.g. one per random seed) against a
reference file, line by line, and reports:

  * BLEU      (sacrebleu, corpus level)
  * chrF++    (sacrebleu, corpus level; more robust to spelling variation
               in romanized Hinglish)
  * CMI       Code-Mixing Index (Das & Gambäck, 2014), averaged per sentence,
               for both hypotheses and reference so the two can be compared

With several hypothesis files, it also reports mean and standard deviation
across seeds.

Usage:
    python evaluation/run_eval.py --ref ref.txt --hyp hyp.seed1 hyp.seed2 \
        [--lang hinglish|hindi] [--out results.json]
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

import sacrebleu

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
WORD = re.compile(r"[\wऀ-ॿ']+", re.UNICODE)

# Small high-frequency English lexicon used to tag romanized tokens.
# Latin-script tokens not in this list are treated as romanized Hindi.
# This is a heuristic; swap in a trained language-ID model for final numbers.
ENGLISH_WORDS = set("""
a about after all also am an and any are as at be because been but by can
could day did do does done for from get go going good got had has have he her
here him his how i if in is it its just know like make me more my no not now
of ok okay on one only or other our out people please really right said see
she so some sorry than thank thanks that the their them then there they think
this time to today too up us very want was we well what when where which who
why will with work would yes you your yeah movie phone office meeting college
friend friends party plan late sure actually problem class exam weekend
""".split())


def token_lang(tok):
    if DEVANAGARI.search(tok):
        return "hi"
    if tok.isdigit():
        return None  # language-independent
    return "en" if tok.lower() in ENGLISH_WORDS else "hi"


def cmi(sentence):
    """Code-Mixing Index: 100 * (1 - max_lang / (n - u)), 0 if no tagged tokens."""
    langs = [token_lang(t) for t in WORD.findall(sentence)]
    tagged = [l for l in langs if l is not None]
    if not tagged:
        return 0.0
    dominant = max(tagged.count("hi"), tagged.count("en"))
    return 100.0 * (1 - dominant / len(tagged))


def read_lines(path):
    return Path(path).read_text(encoding="utf-8").rstrip("\n").split("\n")


def score(refs, hyps, lang):
    # The default 13a tokenizer handles Devanagari punctuation poorly,
    # so Hindi uses sacrebleu's Unicode-aware "intl" tokenizer.
    tokenize = "intl" if lang == "hindi" else "13a"
    bleu = sacrebleu.corpus_bleu(hyps, [refs], tokenize=tokenize)
    chrf = sacrebleu.corpus_chrf(hyps, [refs], word_order=2)
    return {
        "bleu": round(bleu.score, 2),
        "chrf++": round(chrf.score, 2),
        "cmi_hyp": round(statistics.fmean(cmi(h) for h in hyps), 2),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ref", required=True, help="reference file, one sentence per line")
    p.add_argument("--hyp", required=True, nargs="+", help="hypothesis file(s), e.g. one per seed")
    p.add_argument("--lang", choices=["hinglish", "hindi"], default="hinglish")
    p.add_argument("--out", help="optional path to write results as JSON")
    args = p.parse_args(argv)

    refs = read_lines(args.ref)
    results = {"ref": args.ref, "lang": args.lang,
               "cmi_ref": round(statistics.fmean(cmi(r) for r in refs), 2),
               "runs": {}}

    for hyp_path in args.hyp:
        hyps = read_lines(hyp_path)
        if len(hyps) != len(refs):
            sys.exit(f"error: {hyp_path} has {len(hyps)} lines, reference has {len(refs)}")
        results["runs"][hyp_path] = score(refs, hyps, args.lang)

    if len(args.hyp) > 1:
        summary = {}
        for metric in ("bleu", "chrf++", "cmi_hyp"):
            vals = [r[metric] for r in results["runs"].values()]
            summary[metric] = {"mean": round(statistics.fmean(vals), 2),
                               "std": round(statistics.stdev(vals), 2)}
        results["summary"] = summary

    print(f"Reference: {args.ref}  ({len(refs)} lines, lang={args.lang}, CMI={results['cmi_ref']})")
    print(f"{'hypothesis':<40} {'BLEU':>7} {'chrF++':>7} {'CMI':>7}")
    for path, r in results["runs"].items():
        print(f"{path:<40} {r['bleu']:>7.2f} {r['chrf++']:>7.2f} {r['cmi_hyp']:>7.2f}")
    if "summary" in results:
        s = results["summary"]
        print(f"{'mean ± std':<40} " + " ".join(
            f"{s[m]['mean']:>5.2f}±{s[m]['std']:<4.2f}" for m in ("bleu", "chrf++", "cmi_hyp")))

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
