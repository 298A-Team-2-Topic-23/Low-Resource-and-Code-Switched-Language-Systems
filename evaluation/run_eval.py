#!/usr/bin/env python3
"""
Evaluation harness for English -> Romanized Hinglish generation.
One command, all metrics, multi-seed aware.

Metrics
-------
  chrF++              primary metric (character n-grams + word bigrams)
  chrF++ (normalised) same, after mapping every spelling variant in
                      analysis/spelling_variants.tsv to its group label. The
                      gap against case- and punctuation-folded chrF++ is the
                      spelling gap: how much of the "error" is orthographic
                      noise rather than meaning.
  BLEU                reported for comparability; unreliable here by design
  ROUGE-L             reported to compare against Gahoi et al. (2022), Table 2
  WER                 same reason

Usage
-----
  # single run
  python run_eval.py --hyp out/model1.txt --ref data/test.hinglish.txt \\
      --system "Model 1 zero-shot"

  # multi-seed: pass several hypothesis files, get mean +/- std
  python run_eval.py --hyp out/m2.s1.txt out/m2.s2.txt out/m2.s3.txt \\
      --ref data/test.hinglish.txt --system "Model 2 QLoRA"

  # code-switching penalty: score the same sources against a monolingual
  # reference as well, and report the gap
  python run_eval.py --hyp out/m2.hinglish.txt --ref data/test.hinglish.txt \\
      --mono-hyp out/m2.hindi.txt --mono-ref data/test.hindi.txt \\
      --system "Model 2 QLoRA"

  # baseline reproduction check against the published numbers
  python run_eval.py --hyp out/gahoi_repro.txt --ref data/mixmt.test.ref.txt \\
      --system "Gahoi et al. repro" --check-baseline

  # paired bootstrap significance against another system (same refs)
  python run_eval.py --hyp out/m2.s*.txt --ref data/test.hinglish.txt \\
      --system "Model 2 QLoRA" --vs-hyp out/m1.s*.txt --vs-system "Model 1"

  # the pre-registered decision: one rung against another, or the whole ladder
  python run_eval.py --ref data/test.hinglish.txt \\
      --compare "M2=out/m2.s*.txt" "M1=out/m1.s*.txt"
  python run_eval.py --ref data/test.hinglish.txt --ladder "M1=out/m1.s*.txt" \\
      "M2=out/m2.s*.txt" "ControlA=out/ca.s*.txt" "M3=out/m3.s*.txt"

  # append every run to one results file, then print the report table
  python run_eval.py ... --out results/results.jsonl
  python run_eval.py --report results/results.jsonl

Input format: one sentence per line, hypotheses and references aligned.

Every metric is reported as mean +/- std over seeds plus a 95% confidence
interval from a 1,000-sample bootstrap over test items (--bootstrap N; 0 turns
it off). ROUGE-L and WER are computed on case- and punctuation-folded tokens
with spelling left alone, so they see the same words the published baseline
was scored on.
"""
import argparse
import glob
import json
import random
import re
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    from sacrebleu.metrics import BLEU, CHRF
except ImportError:
    sys.exit("pip install sacrebleu")

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
from lrcs.lexicon import DEFAULT_LEXICON, form_index, load_variant_groups  # noqa: E402

# Published reference point: Gahoi et al. (2022), Table 2, MixMT Subtask-1.
PUBLISHED_BASELINE = {"rouge_l": 0.617, "wer": 0.633, "tolerance": 0.01}

# ---------------------------------------------------------------- normalisation
# Romanised Hindi has no standard orthography: nahi / nhi / nahin / nahii are one
# word. Normalisation maps every surface form in the team's spelling-variant
# lexicon (analysis/spelling_variants.tsv, loaded by lrcs.lexicon -- the same
# file the pipeline tags with and the fertility analysis measures) to its group
# label, so the normalised score forgives exactly the variation we have
# evidence for. A token outside the lexicon has its vowel length folded
# (aa -> a, ee/ii -> i, oo/uu -> u), the one variation human writers show on words
# the lexicon does not list (vikaas / vikas, vibhaag / vibhag); nothing else about
# it changes. Folding also merges the odd English pair (book, buk) -- a small
# over-credit, applied to hypothesis and reference alike.
#
# This replaced a set of regex rules (298-59, 298-78). They fully collapsed 3 of
# the 72 groups, missed vowel deletion (nhi, kr, gya), and corrupted correct
# words: n-at-word-end and h-before-consonant turned khyal into kyal, sahna into
# sana and dhyan into dya. Their vowel-length rules were the sound part and are
# kept, for out-of-lexicon tokens only. reports/normalisation_audit.md measures
# the change.
#
# NOTE: used for the normalised metric ONLY. Never normalise training data or
# the gold references themselves -- the variance is the phenomenon we study.
_PUNCT = re.compile(r"[^\w\sऀ-ॿ]", re.UNICODE)
_LETTER_RUN = re.compile(r"([^\W\d_])\1{2,}", re.UNICODE)   # bhaiiii -> bhai, not 1000 -> 10
_VOWEL_LENGTH = [(re.compile(r"aa+"), "a"), (re.compile(r"ee+|ii+"), "i"),
                 (re.compile(r"oo+|uu+"), "u")]


def fold(text: str) -> str:
    """Case, punctuation and whitespace only. Spelling is untouched."""
    t = unicodedata.normalize("NFC", text).lower()
    return " ".join(_PUNCT.sub(" ", t).split())


def load_lexicon_index(path=DEFAULT_LEXICON):
    groups = load_variant_groups(path)
    return groups, form_index(groups)


_GROUPS, _INDEX = load_lexicon_index()


def fold_vowel_length(token: str) -> str:
    for pat, rep in _VOWEL_LENGTH:
        token = pat.sub(rep, token)
    return token


def _normalise_token(tok, index):
    if tok in index:
        return index[tok]
    short = fold_vowel_length(tok)
    return index.get(short, short)


def normalise(text: str, index=None) -> str:
    """fold(), then letter runs of three or more cut to one, then every lexicon
    form replaced by its group label; any other token has its vowel length folded."""
    index = _INDEX if index is None else index
    t = _LETTER_RUN.sub(r"\1", fold(text))
    return " ".join(_normalise_token(tok, index) for tok in t.split())


def collapse_coverage(groups=None, norm=None):
    """How many lexicon groups the normaliser maps to a single form.

    Reported before any normalised figure, so a near-inert normaliser cannot
    pass for a working one."""
    groups = _GROUPS if groups is None else groups
    norm = normalise if norm is None else norm
    collapsed = [g for g, forms in groups.items() if len({norm(f) for f in forms}) == 1]
    return {"collapsed": len(collapsed), "groups": len(groups)}


def tokenise(text: str):
    """Tokens for ROUGE-L and WER: folded, spelling left alone."""
    return fold(text).split()


# ---------------------------------------------------------------------- metrics
# Each metric is computed from per-sentence statistics that add up to the
# corpus score. Scoring a bootstrap sample is then a sum over resampled
# indices, not a fresh pass over the text, so 1,000 samples take seconds.
_CHRF = CHRF(word_order=2)          # word_order=2 is what the ++ means
_BLEU = BLEU()


def _sacre_stats(metric, hyps, refs):
    return [list(map(float, s)) for s in metric._extract_corpus_statistics(hyps, [refs])]


def _lcs(a, b):
    """Length of the longest common subsequence. O(len(a) * len(b))."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b):
            cur.append(prev[j] + 1 if x == y else max(cur[j], prev[j + 1]))
        prev = cur
    return prev[-1]


def _rouge_l_sentence(h, r):
    ht, rt = tokenise(h), tokenise(r)
    if not ht or not rt:
        return 0.0
    l = _lcs(ht, rt)
    if l == 0:
        return 0.0
    p, rec = l / len(ht), l / len(rt)
    return 2 * p * rec / (p + rec)


def _edit_distance(a, b):
    if not a:
        return len(b)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def sentence_stats(hyps, refs):
    """metric -> one additive statistics vector per sentence."""
    norm_h, norm_r = [normalise(h) for h in hyps], [normalise(r) for r in refs]
    fold_h, fold_r = [fold(h) for h in hyps], [fold(r) for r in refs]
    return {
        "chrf++": _sacre_stats(_CHRF, hyps, refs),
        "chrf++_norm": _sacre_stats(_CHRF, norm_h, norm_r),
        "chrf++_fold": _sacre_stats(_CHRF, fold_h, fold_r),
        "bleu": _sacre_stats(_BLEU, hyps, refs),
        "rouge_l": [[_rouge_l_sentence(h, r), 1.0] for h, r in zip(hyps, refs)],
        "wer": [[float(_edit_distance(tokenise(h), tokenise(r))), float(len(tokenise(r)))]
                for h, r in zip(hyps, refs)],
    }


def score_from_stats(metric, stats):
    """Corpus score from summed per-sentence statistics."""
    total = [sum(col) for col in zip(*stats)] if stats else []
    if metric.startswith("chrf"):
        return _CHRF._compute_score_from_stats(total).score
    if metric == "bleu":
        return _BLEU._compute_score_from_stats(total).score
    if metric == "rouge_l":     # mean of sentence F1, on the 0-1 scale of Gahoi et al.
        return total[0] / max(total[1], 1)
    if metric == "wer":         # total edits / total reference words, 0-1
        return total[0] / max(total[1], 1)
    raise KeyError(metric)


ROUNDING = {"chrf++": 3, "chrf++_norm": 3, "chrf++_fold": 3, "bleu": 3, "rouge_l": 4, "wer": 4}


def score_all(hyps, refs, stats=None):
    stats = sentence_stats(hyps, refs) if stats is None else stats
    return {k: round(score_from_stats(k, v), ROUNDING[k]) for k, v in stats.items()}


def chrf(hyps, refs, normalised=False):
    if normalised:
        hyps, refs = [normalise(h) for h in hyps], [normalise(r) for r in refs]
    return score_from_stats("chrf++", _sacre_stats(_CHRF, hyps, refs))


def bleu(hyps, refs):
    return score_from_stats("bleu", _sacre_stats(_BLEU, hyps, refs))


def rouge_l(hyps, refs):
    """Corpus ROUGE-L F1, computed per sentence and averaged (0-1 scale)."""
    return score_from_stats("rouge_l", sentence_stats(hyps, refs)["rouge_l"])


def wer(hyps, refs):
    """Corpus Word Error Rate: total edits / total reference words. 0-1 scale."""
    return score_from_stats("wer", sentence_stats(hyps, refs)["wer"])


# -------------------------------------------------------------------- bootstrap
def _percentile(sorted_vals, q):
    """Linear-interpolated percentile of an already sorted list."""
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _resample_means(per_seed_stats, metric, samples, seed):
    """Seed-mean of the metric on each bootstrap sample. One set of resampled
    item indices is shared by every seed (and by both systems in a paired
    comparison), so the variation measured is over test items only."""
    n = len(per_seed_stats[0][metric])
    rng = random.Random(seed)
    out = []
    for _ in range(samples):
        idx = [rng.randrange(n) for _ in range(n)]
        vals = [score_from_stats(metric, [s[metric][i] for i in idx]) for s in per_seed_stats]
        out.append(statistics.mean(vals))
    return out


def bootstrap_ci(per_seed_stats, metric, samples=1000, seed=12345, level=0.95):
    """Percentile bootstrap CI for the seed-mean of one metric."""
    vals = sorted(_resample_means(per_seed_stats, metric, samples, seed))
    a = (1 - level) / 2
    return _percentile(vals, a), _percentile(vals, 1 - a)


def paired_bootstrap(stats_a, stats_b, metric, samples=1000, seed=12345, level=0.95):
    """System A minus system B on the same resampled items.

    Returns the observed difference, its CI, and the share of samples in which
    A does not beat B (a one-sided p-value; lower is better for WER, so the
    sign is flipped there)."""
    if len(stats_a[0][metric]) != len(stats_b[0][metric]):
        raise ValueError("paired bootstrap needs both systems scored on the same items")
    a = _resample_means(stats_a, metric, samples, seed)
    b = _resample_means(stats_b, metric, samples, seed)
    sign = -1 if metric == "wer" else 1
    diffs = sorted(x - y for x, y in zip(a, b))
    observed = (statistics.mean(score_from_stats(metric, s[metric]) for s in stats_a)
                - statistics.mean(score_from_stats(metric, s[metric]) for s in stats_b))
    p = sum(1 for d in diffs if sign * d <= 0) / samples
    lv = (1 - level) / 2
    return {"diff": observed, "ci95": (_percentile(diffs, lv), _percentile(diffs, 1 - lv)), "p": p}


# -------------------------------------------------------------- decision rule
# Pre-registered 11 November 2026 (298-79), before any real result existed:
# docs/workbook2/section_4_4.md, 4.4.6. Do not change it after results exist.
#
# A rung counts as an improvement over the rung below only if all three hold:
#   * its mean primary-metric gain is at least the null threshold,
#     max(1.0 chrF++, 2 x M1's seed standard deviation). 1.0 is AI-2's
#     null-result line from Workbook 1; the seed term stops a gain smaller than
#     run-to-run noise from counting, and comes from M1, never from the rung
#     being judged;
#   * the 95% paired-bootstrap interval of the gain excludes zero;
#   * the one-sided paired-bootstrap p-value is below 0.05.
# Worse is the mirror image. Anything else is a null result.
# AI-1's success bar is reported beside it: a gain of 3.0 or more with
# non-overlapping seed error bars (mean +/- std).
DECISION_RULE = {"registered": "2026-11-11", "metric": "chrf++", "null_floor": 1.0,
                 "seed_std_multiplier": 2.0, "alpha": 0.05, "success_gain": 3.0,
                 "bootstrap_samples": 1000, "bootstrap_seed": 12345}


def null_threshold(m1_seed_std=None, rule=DECISION_RULE):
    if not m1_seed_std:
        return rule["null_floor"]
    return max(rule["null_floor"], rule["seed_std_multiplier"] * m1_seed_std)


def verdict(diff, ci, p, threshold, rule=DECISION_RULE):
    """'improvement', 'worse' or 'null' for a gain of system A over system B."""
    if diff >= threshold and ci[0] > 0 and p < rule["alpha"]:
        return "improvement"
    if diff <= -threshold and ci[1] < 0 and (1 - p) < rule["alpha"]:
        return "worse"
    return "null"


def meets_success_bar(arm_a, arm_b, rule=DECISION_RULE):
    """AI-1: gain >= 3.0 and the seed error bars do not overlap. None when either
    arm has a single seed, because then there are no error bars to compare."""
    if arm_a["std"] is None or arm_b["std"] is None:
        return None
    gain = arm_a["mean"] - arm_b["mean"]
    return gain >= rule["success_gain"] and arm_a["mean"] - arm_a["std"] > arm_b["mean"] + arm_b["std"]


def parse_system(spec):
    """'Name=glob' or 'glob', or comma-separated files. Returns (name, files)."""
    name, _, pattern = spec.rpartition("=")
    files = []
    for part in pattern.split(","):
        found = sorted(glob.glob(part))
        files.extend(found or ([part] if Path(part).exists() else []))
    if not files:
        sys.exit(f"no hypothesis files match {pattern!r}")
    return (name or Path(files[0]).stem), files


def compare_ladder(systems, refs, samples=1000, seed=12345, rule=DECISION_RULE):
    """Judge each rung against the rung below it under the decision rule.

    systems: [(name, hyp_files)] in ladder order, lowest first. The null
    threshold uses the seed spread of the rung named M1 if there is one."""
    metric = rule["metric"]
    arms = []
    for name, files in systems:
        stats, scores = score_files(files, refs)
        mean, std = agg([s[metric] for s in scores])
        lo, hi = bootstrap_ci(stats, metric, samples, seed)
        arms.append({"name": name, "files": files, "seeds": len(files), "mean": mean, "std": std,
                     "ci95": [round(lo, 3), round(hi, 3)], "_stats": stats})
    m1 = next((a for a in arms if a["name"].upper() == "M1"), None)
    threshold = null_threshold(m1["std"] if m1 else None, rule)
    steps = []
    for lower, upper in zip(arms, arms[1:]):
        r = paired_bootstrap(upper["_stats"], lower["_stats"], metric, samples, seed)
        steps.append({"system": upper["name"], "vs": lower["name"], "diff": round(r["diff"], 3),
                      "ci95": [round(x, 3) for x in r["ci95"]], "p": round(r["p"], 4),
                      "verdict": verdict(r["diff"], r["ci95"], r["p"], threshold, rule),
                      "ai1_success": meets_success_bar(upper, lower, rule)})
    for a in arms:
        del a["_stats"]
    return {"rule": rule, "metric": metric, "null_threshold": round(threshold, 3),
            "threshold_source": "M1 seed spread" if m1 and m1["std"] else "floor (no multi-seed M1)",
            "arms": arms, "steps": steps}


_SUCCESS_LABEL = {True: "met", False: "not met", None: "n/a: needs 2+ seeds per arm"}


def print_ladder(result):
    r = result["rule"]
    print(f"\ndecision rule registered {r['registered']}: {r['metric']}, null threshold "
          f"{result['null_threshold']:.3f} ({result['threshold_source']}), alpha {r['alpha']}, "
          f"{r['bootstrap_samples']}-sample paired bootstrap")
    print("\n| System | seeds | mean ± std over seeds | 95% CI over test items |")
    print("|---|---|---|---|")
    for a in result["arms"]:
        print(f"| {a['name']} | {a['seeds']} | {fmt(a['mean'], a['std'])} | {fmt_ci(a['ci95'])} |")
    print("\n| Step | gain | 95% CI of gain | p | verdict | AI-1 success bar |")
    print("|---|---|---|---|---|---|")
    for s in result["steps"]:
        print(f"| {s['system']} vs {s['vs']} | {s['diff']:+.3f} | {fmt_ci(s['ci95'])} | {s['p']:.4f} "
              f"| **{s['verdict']}** | {_SUCCESS_LABEL[s['ai1_success']]} |")
    print()


# --------------------------------------------------------------------------- io
def read_lines(path):
    lines = [l.rstrip("\n") for l in Path(path).read_text(encoding="utf-8").splitlines()]
    if not lines:
        sys.exit(f"empty file: {path}")
    return lines


def check_aligned(hyps, refs, label=""):
    if len(hyps) != len(refs):
        sys.exit(f"line count mismatch {label}: {len(hyps)} hypotheses vs {len(refs)} references")


def agg(values):
    """mean +/- sample std. std is None for a single run."""
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else None
    return round(m, 3), (round(s, 3) if s is not None else None)


def fmt(mean, std):
    return f"{mean:.3f}" if std is None else f"{mean:.3f} ± {std:.3f}"


# ----------------------------------------------------------------------- report
def fmt_ci(ci):
    return "—" if not ci else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def print_report(path):
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        sys.exit("no results recorded yet")
    cols = ["chrf++", "chrf++_norm", "bleu", "rouge_l", "wer"]
    head = "| System | seeds | " + " | ".join(cols) + " | chrF++ 95% CI | CS penalty |"
    print("\n" + head)
    print("|" + "---|" * (len(cols) + 4))
    for r in rows:
        cells = [fmt(r["metrics"][c]["mean"], r["metrics"][c]["std"]) for c in cols]
        ci = fmt_ci(r["metrics"]["chrf++"].get("ci95"))
        pen = f"{r['cs_penalty']:.3f}" if r.get("cs_penalty") is not None else "—"
        print(f"| {r['system']} | {r['n_seeds']} | " + " | ".join(cells) + f" | {ci} | {pen} |")
    print()


def score_files(hyp_files, refs):
    """Per-seed sentence statistics and scores for a list of hypothesis files."""
    stats, scores = [], []
    for h in hyp_files:
        hyps = read_lines(h)
        check_aligned(hyps, refs, f"({h})")
        st = sentence_stats(hyps, refs)
        stats.append(st)
        scores.append(score_all(hyps, refs, st))
    return stats, scores


# ------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hyp", nargs="+", help="hypothesis file(s); one per seed")
    ap.add_argument("--ref", help="code-switched (Hinglish) reference file")
    ap.add_argument("--mono-hyp", nargs="+", help="monolingual Hindi hypothesis file(s)")
    ap.add_argument("--mono-ref", help="monolingual Hindi reference file")
    ap.add_argument("--system", default="unnamed", help="system name for the results table")
    ap.add_argument("--vs-hyp", nargs="+", help="another system's hypothesis file(s), same refs, "
                                               "for a paired bootstrap comparison")
    ap.add_argument("--vs-system", default="other system", help="name of the --vs-hyp system")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"),
                    help="judge system A against system B under the pre-registered decision "
                         "rule; each is 'Name=glob' (one file per seed)")
    ap.add_argument("--ladder", nargs="+", metavar="SYSTEM",
                    help="judge each rung against the one below, lowest first; 'Name=glob' each")
    ap.add_argument("--bootstrap", type=int, default=1000,
                    help="bootstrap samples for confidence intervals (0 turns them off)")
    ap.add_argument("--bootstrap-seed", type=int, default=12345)
    ap.add_argument("--out", help="append the result as JSON to this file")
    ap.add_argument("--report", help="print the results table from this file and exit")
    ap.add_argument("--check-baseline", action="store_true",
                    help="compare ROUGE-L and WER against the published Gahoi et al. numbers")
    args = ap.parse_args()

    if args.report:
        print_report(args.report)
        return
    if args.compare or args.ladder:
        if not args.ref:
            ap.error("--ref is required")
        refs = read_lines(args.ref)
        # A, B order on the command line reads as "A against B"; the ladder runs low to high.
        specs = list(reversed(args.compare)) if args.compare else args.ladder
        result = compare_ladder([parse_system(s) for s in specs], refs,
                                args.bootstrap or 1000, args.bootstrap_seed)
        print_ladder(result)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            rec = dict(result, timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       kind="comparison", ref_file=args.ref)
            with open(args.out, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
        return
    if not args.hyp or not args.ref:
        ap.error("--hyp and --ref are required")

    refs = read_lines(args.ref)
    stats, per_seed = score_files(args.hyp, refs)

    metrics = {}
    for k in per_seed[0]:
        mean, std = agg([s[k] for s in per_seed])
        metrics[k] = {"mean": mean, "std": std}
        if args.bootstrap:
            lo, hi = bootstrap_ci(stats, k, args.bootstrap, args.bootstrap_seed)
            metrics[k]["ci95"] = [round(lo, ROUNDING[k]), round(hi, ROUNDING[k])]

    # code-switching penalty: monolingual quality minus code-switched quality
    cs_penalty = None
    if args.mono_hyp and args.mono_ref:
        mono_refs = read_lines(args.mono_ref)
        mono = []
        for h in args.mono_hyp:
            mh = read_lines(h)
            check_aligned(mh, mono_refs, f"({h})")
            mono.append(chrf(mh, mono_refs))
        cs_penalty = round(statistics.mean(mono) - metrics["chrf++"]["mean"], 3)

    coverage = collapse_coverage()
    print(f"\nsystem : {args.system}")
    print(f"seeds  : {len(per_seed)}")
    print(f"lines  : {len(refs)}")
    print(f"lexicon: normalisation collapses {coverage['collapsed']} of {coverage['groups']} "
          f"variant groups ({DEFAULT_LEXICON.relative_to(REPO_ROOT)})")
    if args.bootstrap:
        print(f"CI     : 95%, {args.bootstrap}-sample bootstrap over test items")
    print("-" * 46)
    for k, v in metrics.items():
        ci = f"   95% CI {fmt_ci(v['ci95'])}" if "ci95" in v else ""
        print(f"  {k:<14} {fmt(v['mean'], v['std'])}{ci}")
    if cs_penalty is not None:
        print(f"  {'CS penalty':<14} {cs_penalty:.3f}   (monolingual chrF++ − code-switched chrF++)")
    gap = metrics["chrf++_norm"]["mean"] - metrics["chrf++_fold"]["mean"]
    print(f"  {'spelling gap':<14} {gap:+.3f}   (normalised minus case/punctuation-folded chrF++: "
          f"error that is spelling, not meaning)")

    comparison = None
    if args.vs_hyp:
        vs_stats, _ = score_files(args.vs_hyp, refs)
        samples = args.bootstrap or 1000
        print(f"\npaired bootstrap: {args.system} vs {args.vs_system}, {samples} samples")
        comparison = {"vs_system": args.vs_system, "vs_hyp_files": args.vs_hyp, "metrics": {}}
        for k in ("chrf++", "chrf++_norm", "bleu", "rouge_l", "wer"):
            r = paired_bootstrap(stats, vs_stats, k, samples, args.bootstrap_seed)
            comparison["metrics"][k] = {"diff": round(r["diff"], ROUNDING[k]),
                                        "ci95": [round(x, ROUNDING[k]) for x in r["ci95"]],
                                        "p": round(r["p"], 4)}
            print(f"  {k:<14} diff {r['diff']:+.3f}   95% CI {fmt_ci(r['ci95'])}   p {r['p']:.4f}")

    if args.check_baseline:
        b = PUBLISHED_BASELINE
        print("\nbaseline reproduction check — Gahoi et al. (2022), Table 2")
        ok = True
        for k in ("rouge_l", "wer"):
            got, want = metrics[k]["mean"], b[k]
            d = abs(got - want)
            hit = d <= b["tolerance"]
            ok &= hit
            print(f"  {k:<8} got {got:.4f}  published {want:.3f}  diff {d:.4f}  "
                  f"{'PASS' if hit else 'FAIL'} (tolerance {b['tolerance']})")
        print("  => harness validated" if ok else "  => outside tolerance; do not interpret model results yet")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "system": args.system,
            "n_seeds": len(per_seed),
            "n_lines": len(refs),
            "metrics": metrics,
            "per_seed": per_seed,
            "cs_penalty": cs_penalty,
            "normalisation_coverage": coverage,
            "bootstrap": {"samples": args.bootstrap, "seed": args.bootstrap_seed},
            "comparison": comparison,
            "hyp_files": args.hyp,
            "ref_file": args.ref,
        }
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"\nappended to {args.out}")


if __name__ == "__main__":
    main()
