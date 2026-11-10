"""Tests for evaluation/run_eval.py (298-59).

The normalisation tests are run against two implementations: the lexicon-driven
normaliser the harness now uses, and a verbatim copy of the regex rules it
replaced. Each contract is expected to hold for the first and to fail for the
second -- that is the proof the fix changed behaviour, not just code.
"""

import importlib.util
import re
import unicodedata
from pathlib import Path

import pytest

pytest.importorskip("sacrebleu")
import sacrebleu  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _load_harness():
    spec = importlib.util.spec_from_file_location("run_eval", ROOT / "evaluation" / "run_eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ev = _load_harness()

# The rules run_eval.py used before 298-59, copied unchanged.
_OLD_RULES = [
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


def old_normalise(text):
    t = unicodedata.normalize("NFC", text).lower()
    t = _OLD_PUNCT.sub(" ", t)
    for pat, rep in _OLD_RULES:
        t = pat.sub(rep, t)
    return t.strip()


# ------------------------------------------------------------- normalisation
def _collapses_every_group(norm):
    cov = ev.collapse_coverage(norm=norm)
    return cov["collapsed"] == cov["groups"]


def _catches_vowel_deletion(norm):
    pairs = [("nhi", "nahi"), ("kr", "kar"), ("gya", "gaya"), ("rha", "raha"), ("krna", "karna")]
    return all(norm(a) == norm(b) for a, b in pairs)


def _leaves_correct_words_alone(norm):
    # Correct words outside the lexicon, each damaged by an old rule.
    words = ["khyal", "sahna", "pahle", "bhool", "baat", "sooraj"]
    return all(norm(w) == w for w in words)


@pytest.mark.parametrize("contract", [_collapses_every_group, _catches_vowel_deletion,
                                      _leaves_correct_words_alone])
def test_lexicon_normaliser_meets_the_contract(contract):
    assert contract(ev.normalise)


@pytest.mark.parametrize("contract", [_collapses_every_group, _catches_vowel_deletion,
                                      _leaves_correct_words_alone])
def test_old_regex_normaliser_fails_the_same_contract(contract):
    assert not contract(old_normalise)


def test_old_regex_collapsed_three_groups_and_the_lexicon_collapses_all():
    groups = ev.collapse_coverage()["groups"]
    assert groups == 72
    assert ev.collapse_coverage(norm=old_normalise)["collapsed"] == 3
    assert ev.collapse_coverage()["collapsed"] == groups


def test_normalise_folds_case_punctuation_and_letter_runs_only():
    assert ev.normalise("Nahiiii!!  main  KR dunga.") == "nahi main kar dunga"
    assert ev.normalise("1000 rupay") == "1000 rupay"      # digit runs are not letter runs


# ---------------------------------------------------------- ROUGE-L and WER
def test_rouge_and_wer_see_spelling_differences():
    # The old tokeniser ran the spelling rules first, so nahin and nahi were
    # the same token and ROUGE-L / WER scored this pair as perfect.
    hyp, ref = ["wo nahin aaya"], ["wo nahi aaya"]
    assert ev.rouge_l(hyp, ref) < 1.0
    assert ev.wer(hyp, ref) == pytest.approx(1 / 3)


def test_rouge_and_wer_ignore_case_and_punctuation():
    assert ev.rouge_l(["Main ghar ja raha hoon."], ["main ghar ja raha hoon"]) == 1.0
    assert ev.wer(["Main ghar ja raha hoon."], ["main ghar ja raha hoon"]) == 0.0


# ----------------------------------------------------- additive statistics
HYPS = ["main aaj market ja raha hoon", "mujhe nhi pata", "kal milte hain", "report bhej do"]
REFS = ["main aaj market ja rha hoon", "mujhe nahi pata", "kal milenge", "please report bhej do"]


def test_summed_sentence_stats_reproduce_sacrebleu_corpus_scores():
    assert ev.chrf(HYPS, REFS) == pytest.approx(
        sacrebleu.corpus_chrf(HYPS, [REFS], word_order=2).score)
    assert ev.bleu(HYPS, REFS) == pytest.approx(sacrebleu.corpus_bleu(HYPS, [REFS]).score)


def test_normalised_chrf_forgives_lexicon_variants_only():
    assert ev.chrf(["mujhe nhi pata"], ["mujhe nahi pata"], normalised=True) == pytest.approx(100.0)
    assert ev.chrf(["mujhe nhi pata"], ["mujhe nahi pata"]) < 100.0


# -------------------------------------------------------------- bootstrap
def _stats(hyps, refs=REFS):
    return [ev.sentence_stats(hyps, refs)]


def test_bootstrap_ci_is_deterministic_and_brackets_the_score():
    stats = _stats(HYPS)
    lo, hi = ev.bootstrap_ci(stats, "chrf++", samples=200, seed=7)
    assert (lo, hi) == ev.bootstrap_ci(stats, "chrf++", samples=200, seed=7)
    assert lo <= ev.chrf(HYPS, REFS) <= hi


def test_paired_bootstrap_separates_a_better_system():
    good = _stats(REFS)                       # perfect output
    bad = _stats(["x y z"] * len(REFS))       # nothing right
    r = ev.paired_bootstrap(good, bad, "chrf++", samples=200, seed=7)
    assert r["diff"] > 0 and r["ci95"][0] > 0 and r["p"] < 0.05
    w = ev.paired_bootstrap(good, bad, "wer", samples=200, seed=7)
    assert w["diff"] < 0 and w["p"] < 0.05    # lower WER is better


def test_paired_bootstrap_of_a_system_against_itself_is_not_significant():
    stats = _stats(HYPS)
    r = ev.paired_bootstrap(stats, stats, "chrf++", samples=200, seed=7)
    assert r["diff"] == 0 and r["p"] == 1.0


def test_paired_bootstrap_refuses_different_item_counts():
    with pytest.raises(ValueError):
        ev.paired_bootstrap(_stats(HYPS), _stats(HYPS[:2], REFS[:2]), "chrf++", samples=10)
