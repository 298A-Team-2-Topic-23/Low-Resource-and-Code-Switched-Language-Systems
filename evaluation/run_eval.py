#!/usr/bin/env python3
"""
Evaluation harness for English -> Romanized Hinglish generation.
One command, all metrics, multi-seed aware.

Metrics
-------
  chrF++              primary metric (character n-grams + word bigrams)
  chrF++ (normalised) same, after collapsing Romanised spelling variants.
                      The raw-vs-normalised gap quantifies how much of the
                      "error" is orthographic noise rather than meaning.
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

  # append every run to one results file, then print the report table
  python run_eval.py ... --out results/results.jsonl
  python run_eval.py --report results/results.jsonl

Input format: one sentence per line, hypotheses and references aligned.
"""
import argparse
import json
import re
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

try:
    import sacrebleu
except ImportError:
    sys.exit("pip install sacrebleu")

# Published reference point: Gahoi et al. (2022), Table 2, MixMT Subtask-1.
PUBLISHED_BASELINE = {"rouge_l": 0.617, "wer": 0.633, "tolerance": 0.01}

# ---------------------------------------------------------------- normalisation
# Romanised Hindi has no standard orthography: nahi / nhi / nahii / nahin are
# one word. These rules collapse the common variants so we can measure how much
# of the score difference is spelling rather than meaning.
# NOTE: used for the normalised metric ONLY. Never normalise training data or
# the gold references themselves -- the variance is the phenomenon we study.
_NORM_RULES = [
    (re.compile(r"(.)\1{2,}"), r"\1"),       # bhaiiii -> bhai
    (re.compile(r"aa+"), "a"),
    (re.compile(r"ee+"), "i"),
    (re.compile(r"ii+"), "i"),
    (re.compile(r"oo+"), "u"),
    (re.compile(r"uu+"), "u"),
    (re.compile(r"n\b"), ""),                # nahin -> nahi
    (re.compile(r"h(?=[bcdfgjklmnpqrstvwxyz])"), ""),
    (re.compile(r"\s+"), " "),
]
_PUNCT = re.compile(r"[^\w\sऀ-ॿ]", re.UNICODE)


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFC", text).lower()
    t = _PUNCT.sub(" ", t)
    for pat, rep in _NORM_RULES:
        t = pat.sub(rep, t)
    return t.strip()


def tokenise(text: str):
    return normalise(text).split()


# ---------------------------------------------------------------------- metrics
def chrf(hyps, refs, normalised=False):
    """chrF++ : word_order=2 is what the ++ means."""
    if normalised:
        hyps = [normalise(h) for h in hyps]
        refs = [normalise(r) for r in refs]
    return sacrebleu.corpus_chrf(hyps, [refs], word_order=2).score


def bleu(hyps, refs):
    return sacrebleu.corpus_bleu(hyps, [refs]).score


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


def rouge_l(hyps, refs):
    """Corpus ROUGE-L F1, computed per sentence and averaged.

    Gahoi et al. report 0.617 on MixMT Subtask-1, so this is reported on the
    same 0-1 scale rather than 0-100.
    """
    scores = []
    for h, r in zip(hyps, refs):
        ht, rt = tokenise(h), tokenise(r)
        if not ht or not rt:
            scores.append(0.0)
            continue
        l = _lcs(ht, rt)
        if l == 0:
            scores.append(0.0)
            continue
        p, rec = l / len(ht), l / len(rt)
        scores.append(2 * p * rec / (p + rec))
    return sum(scores) / max(len(scores), 1)


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


def wer(hyps, refs):
    """Corpus Word Error Rate: total edits / total reference words. 0-1 scale."""
    edits = words = 0
    for h, r in zip(hyps, refs):
        ht, rt = tokenise(h), tokenise(r)
        edits += _edit_distance(ht, rt)
        words += len(rt)
    return edits / max(words, 1)


def score_all(hyps, refs):
    return {
        "chrf++": round(chrf(hyps, refs), 3),
        "chrf++_norm": round(chrf(hyps, refs, normalised=True), 3),
        "bleu": round(bleu(hyps, refs), 3),
        "rouge_l": round(rouge_l(hyps, refs), 4),
        "wer": round(wer(hyps, refs), 4),
    }


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
def print_report(path):
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        sys.exit("no results recorded yet")
    cols = ["chrf++", "chrf++_norm", "bleu", "rouge_l", "wer"]
    head = "| System | seeds | " + " | ".join(cols) + " | CS penalty |"
    print("\n" + head)
    print("|" + "---|" * (len(cols) + 3))
    for r in rows:
        cells = [fmt(r["metrics"][c]["mean"], r["metrics"][c]["std"]) for c in cols]
        pen = f"{r['cs_penalty']:.3f}" if r.get("cs_penalty") is not None else "—"
        print(f"| {r['system']} | {r['n_seeds']} | " + " | ".join(cells) + f" | {pen} |")
    print()


# ------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hyp", nargs="+", help="hypothesis file(s); one per seed")
    ap.add_argument("--ref", help="code-switched (Hinglish) reference file")
    ap.add_argument("--mono-hyp", nargs="+", help="monolingual Hindi hypothesis file(s)")
    ap.add_argument("--mono-ref", help="monolingual Hindi reference file")
    ap.add_argument("--system", default="unnamed", help="system name for the results table")
    ap.add_argument("--out", help="append the result as JSON to this file")
    ap.add_argument("--report", help="print the results table from this file and exit")
    ap.add_argument("--check-baseline", action="store_true",
                    help="compare ROUGE-L and WER against the published Gahoi et al. numbers")
    args = ap.parse_args()

    if args.report:
        print_report(args.report)
        return
    if not args.hyp or not args.ref:
        ap.error("--hyp and --ref are required")

    refs = read_lines(args.ref)
    per_seed = []
    for h in args.hyp:
        hyps = read_lines(h)
        check_aligned(hyps, refs, f"({h})")
        per_seed.append(score_all(hyps, refs))

    metrics = {}
    for k in per_seed[0]:
        mean, std = agg([s[k] for s in per_seed])
        metrics[k] = {"mean": mean, "std": std}

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

    print(f"\nsystem : {args.system}")
    print(f"seeds  : {len(per_seed)}")
    print(f"lines  : {len(refs)}")
    print("-" * 46)
    for k, v in metrics.items():
        print(f"  {k:<14} {fmt(v['mean'], v['std'])}")
    if cs_penalty is not None:
        print(f"  {'CS penalty':<14} {cs_penalty:.3f}   (monolingual chrF++ − code-switched chrF++)")
    gap = metrics["chrf++_norm"]["mean"] - metrics["chrf++"]["mean"]
    print(f"  {'norm gap':<14} {gap:+.3f}   (how much of the error is spelling, not meaning)")

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
            "hyp_files": args.hyp,
            "ref_file": args.ref,
        }
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"\nappended to {args.out}")


if __name__ == "__main__":
    main()
