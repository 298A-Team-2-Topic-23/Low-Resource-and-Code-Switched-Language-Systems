"""Tests for evaluation/run_eval.py (298-59).

The normalisation tests are run against two implementations: the lexicon-driven
normaliser the harness now uses, and a verbatim copy of the regex rules it
replaced. Each contract is expected to hold for the first and to fail for the
second -- that is the proof the fix changed behaviour, not just code.
"""

import importlib.util
import sys
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
    # Correct words outside the lexicon, each damaged by the old n-at-word-end or
    # h-before-consonant rule (298-78). None has a long vowel, so the vowel-length
    # folding the new normaliser applies outside the lexicon leaves them intact.
    words = ["khyal", "sahna", "pahle", "bahna", "kahna", "rehna", "dhyan", "vyakhya"]
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


def test_out_of_lexicon_words_have_vowel_length_folded_and_nothing_else():
    # The variation human references show on words the lexicon does not list.
    assert ev.normalise("vikaas vibhaag poorv") == ev.normalise("vikas vibhag purv")
    assert ev.normalise("friend their") == "friend their"     # ie / ei are not length


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


# ------------------------------------------------------------------ the audit
def test_audit_reports_full_collapse_and_no_corruption():
    spec = importlib.util.spec_from_file_location(
        "audit_normalisation", ROOT / "scripts" / "audit_normalisation.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    a = audit.audit()
    assert a["groups"]["before"]["lexicon_groups"] == 3
    assert a["groups"]["after"]["lexicon_groups"] == a["groups"]["after"]["of_lexicon"] == 72
    after = a["occurrences_top15"]["after"]
    assert after["non_canonical_mapped_to_canonical"] == after["non_canonical"]
    assert all(v["after"] == w for w, v in a["corruption_probes"].items())
    assert all(v["before"] != w for w, v in a["corruption_probes"].items())


# ------------------------------------------------------ decision rule (298-79)
def test_decision_rule_is_registered_before_results():
    rule = ev.DECISION_RULE
    assert rule["registered"] == "2026-11-11"
    assert (rule["metric"], rule["null_floor"], rule["alpha"], rule["success_gain"]) == \
        ("chrf++", 1.0, 0.05, 3.0)


def test_null_threshold_comes_from_m1_seed_spread_with_a_floor():
    assert ev.null_threshold(None) == 1.0
    assert ev.null_threshold(0.3) == 1.0          # 2 x 0.3 is below the floor
    assert ev.null_threshold(0.8) == 1.6          # noisy M1 raises the bar


@pytest.mark.parametrize("diff, ci, p, expected", [
    (2.0, (0.5, 3.5), 0.01, "improvement"),
    (2.0, (-0.5, 3.5), 0.08, "null"),           # interval spans zero
    (0.6, (0.2, 1.0), 0.001, "null"),           # significant but below the threshold
    (-2.0, (-3.5, -0.5), 0.99, "worse"),
])
def test_verdict_on_known_numbers(diff, ci, p, expected):
    assert ev.verdict(diff, ci, p, threshold=1.0) == expected


def test_success_bar_needs_seed_error_bars():
    assert ev.meets_success_bar({"mean": 40, "std": None}, {"mean": 30, "std": None}) is None
    assert ev.meets_success_bar({"mean": 40, "std": 1}, {"mean": 30, "std": 1}) is True
    assert ev.meets_success_bar({"mean": 34, "std": 2}, {"mean": 30, "std": 2}) is False


def _write_system(tmp_path, name, lines_per_seed):
    files = []
    for seed, lines in enumerate(lines_per_seed):
        path = tmp_path / f"{name}.s{seed}.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        files.append(str(path))
    return name, files


LADDER_REFS = [f"main aaj {w} ke saath market ja raha hoon" for w in
               ("dost", "bhai", "papa", "mummy", "didi", "chacha", "nana", "dadi",
                "mama", "chachi", "bua", "mausi")] * 3


def test_identical_systems_are_never_called_different(tmp_path):
    hyps = [r.replace("raha", "rha") for r in LADDER_REFS]
    m1 = _write_system(tmp_path, "M1", [hyps] * 3)
    same = _write_system(tmp_path, "Same", [hyps] * 3)
    result = ev.compare_ladder([m1, same], LADDER_REFS, samples=200, seed=7)
    assert result["steps"][0]["verdict"] == "null"
    assert result["steps"][0]["diff"] == 0


def test_a_planted_difference_is_detected_and_deterministic(tmp_path):
    weak = [" ".join(r.split()[:3]) for r in LADDER_REFS]
    m1 = _write_system(tmp_path, "M1", [weak] * 3)
    m2 = _write_system(tmp_path, "M2", [LADDER_REFS] * 3)
    first = ev.compare_ladder([m1, m2], LADDER_REFS, samples=200, seed=7)
    again = ev.compare_ladder([m1, m2], LADDER_REFS, samples=200, seed=7)
    assert first["steps"][0]["verdict"] == "improvement"
    assert first["steps"] == again["steps"]          # a reported p-value reproduces exactly
    assert first["threshold_source"] == "M1 seed spread" or first["arms"][0]["std"] == 0


def test_compare_cli_prints_the_verdict(tmp_path):
    import subprocess
    ref = tmp_path / "ref.txt"
    ref.write_text("\n".join(LADDER_REFS) + "\n", encoding="utf-8")
    _write_system(tmp_path, "m1", [[" ".join(r.split()[:3]) for r in LADDER_REFS]] * 2)
    _write_system(tmp_path, "m2", [LADDER_REFS] * 2)
    out = subprocess.run([sys.executable, str(ROOT / "evaluation" / "run_eval.py"), "--ref", str(ref),
                          "--compare", f"M2={tmp_path}/m2.s*.txt", f"M1={tmp_path}/m1.s*.txt",
                          "--bootstrap", "200"], capture_output=True, text=True, check=True).stdout
    assert "| M2 vs M1 |" in out and "**improvement**" in out
    assert "decision rule registered 2026-11-11" in out
