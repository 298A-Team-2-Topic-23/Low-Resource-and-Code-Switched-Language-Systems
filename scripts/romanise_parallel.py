#!/usr/bin/env python3
"""
Romanise the Hindi side of the parallel slice, and measure how well it does.  [298-76]

Two modes.

  # 1. the accuracy spot-check, against human Romanisations Dakshina holds out
  python scripts/romanise_parallel.py --spot-check

  # 2. Romanise the contamination-checked slice from scripts/prepare_parallel_corpus.py
  python scripts/romanise_parallel.py \\
      --input data/interim/samanantar/hi_slice.tsv \\
      --output data/interim/samanantar/hi_slice.roman.tsv

The spot-check draws 100 sentences, seeded, from Dakshina's held-out test set
(`hi.romanized.rejoined.test.{native,roman}.txt`). These are Wikipedia
sentences that a person Romanised by hand and that the lexicon was not built
from. It scores the romaniser against that person's spelling, word by word and
by character error rate. Matching one annotator's spelling is a strict
standard: `nahi` against a reference `nahin` counts as wrong, although both
are right. That strictness is reported, not hidden, because it is exactly the
variance the project studies. A second check scores the rule-based fallback
alone on 100 held-out lexicon words it has never seen, against every spelling
annotators gave for that word.

Outputs:
  reports/codemix/transliteration_spotcheck.json   committed: metrics, line ids, 5 examples
  data/interim/.../hi_slice.roman.tsv              gitignored: english, hindi (Romanised)
  reports/codemix/romanisation_stats.json          committed: lexicon vs rule shares, script check
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative  # noqa: E402
from lrcs.data.transliterate import Romaniser, levenshtein, load_lexicon, rule_romanise  # noqa: E402
from lrcs.text import devanagari_fraction, sha256_file, word_tokens  # noqa: E402

DAKSHINA_HI = REPO_ROOT / "data" / "raw" / "dakshina" / "dakshina_dataset_v1.0" / "hi"
LEXICON = DAKSHINA_HI / "lexicons" / "hi.translit.sampled.train.tsv"
HELD_OUT_LEXICON = DAKSHINA_HI / "lexicons" / "hi.translit.sampled.test.tsv"
TEST_NATIVE = DAKSHINA_HI / "romanized" / "hi.romanized.rejoined.test.native.txt"
TEST_ROMAN = DAKSHINA_HI / "romanized" / "hi.romanized.rejoined.test.roman.txt"
REPORT_DIR = REPO_ROOT / "reports" / "codemix"
GENERATOR_LIMIT = 0.05   # codemix.read_parallel refuses a Hindi side above this


def need(path):
    if not Path(path).exists():
        sys.exit("{}: not found. Dakshina is not in the repository; download "
                 "dakshina_dataset_v1.0.tar from "
                 "https://github.com/google-research-datasets/dakshina and extract hi/ under "
                 "data/raw/dakshina/ (docs/datasheet.md)".format(repo_relative(Path(path))))


def spot_check(n, seed):
    for p in (LEXICON, HELD_OUT_LEXICON, TEST_NATIVE, TEST_ROMAN):
        need(p)
    lexicon = load_lexicon(LEXICON)
    native = TEST_NATIVE.read_text(encoding="utf-8").splitlines()
    roman = TEST_ROMAN.read_text(encoding="utf-8").splitlines()
    if len(native) != len(roman):
        raise SystemExit("Dakshina test files are misaligned")
    lines = sorted(random.Random(seed).sample(range(len(native)), n))
    romaniser = Romaniser(lexicon)

    words_aligned = words_correct = sentences_aligned = 0
    char_edits = char_total = 0
    lexicon_correct = lexicon_total = rule_correct = rule_total = 0
    examples = []
    for line in lines:
        hyp = romaniser.sentence(native[line])
        ref = roman[line]
        h_words = [w.lower() for w in word_tokens(hyp)]
        r_words = [w.lower() for w in word_tokens(ref)]
        n_words = [w for w in word_tokens(native[line])]
        h_join, r_join = " ".join(h_words), " ".join(r_words)
        char_edits += levenshtein(h_join, r_join)
        char_total += len(r_join)
        if len(h_words) == len(r_words):
            sentences_aligned += 1
            for hw, rw, nw in zip(h_words, r_words, n_words):
                words_aligned += 1
                ok = hw == rw
                words_correct += ok
                if nw in lexicon:
                    lexicon_total += 1
                    lexicon_correct += ok
                elif devanagari_fraction(nw) > 0:
                    rule_total += 1
                    rule_correct += ok
        if len(examples) < 5:
            examples.append(OrderedDict([("line", line + 1), ("ours", hyp), ("annotator", ref)]))

    # The fallback alone, on words it has never seen, against every attested spelling.
    held = {}
    for row in HELD_OUT_LEXICON.read_text(encoding="utf-8").splitlines():
        parts = row.split("\t")
        if len(parts) >= 2 and parts[0] not in lexicon:
            held.setdefault(parts[0], set()).add(parts[1].lower())
    words = sorted(random.Random(seed).sample(sorted(held), min(n, len(held))))
    rule_any = sum(1 for w in words if rule_romanise(w) in held[w])
    rule_cer_edits = sum(min(levenshtein(rule_romanise(w), s) for s in held[w]) for w in words)
    rule_cer_chars = sum(len(min(held[w], key=lambda s: levenshtein(rule_romanise(w), s)))
                         for w in words)

    report = OrderedDict([
        ("issue", "298-76"),
        ("generated_by", "scripts/romanise_parallel.py --spot-check"),
        ("seed", seed),
        ("lexicon", OrderedDict([("file", repo_relative(LEXICON)),
                                 ("sha256", sha256_file(LEXICON)),
                                 ("native_words", len(lexicon))])),
        ("sentence_check", OrderedDict([
            ("source", "Dakshina hi.romanized.rejoined.test, held out from the lexicon"),
            ("sentences", n),
            ("line_numbers", [x + 1 for x in lines]),
            ("character_error_rate", round(char_edits / char_total, 4) if char_total else None),
            ("sentences_with_equal_word_counts", sentences_aligned),
            ("words_scored", words_aligned),
            ("word_exact_match", round(words_correct / words_aligned, 4) if words_aligned else None),
            ("word_exact_match_lexicon_path", round(lexicon_correct / lexicon_total, 4) if lexicon_total else None),
            ("words_on_lexicon_path", lexicon_total),
            ("word_exact_match_rule_path", round(rule_correct / rule_total, 4) if rule_total else None),
            ("words_on_rule_path", rule_total),
            ("romaniser_paths", romaniser.summary()),
        ])),
        ("rule_fallback_check", OrderedDict([
            ("source", "Dakshina hi.translit.sampled.test, words absent from the train lexicon"),
            ("words", len(words)),
            ("matches_any_attested_spelling", round(rule_any / len(words), 4) if words else None),
            ("character_error_rate_to_nearest_attested", round(rule_cer_edits / rule_cer_chars, 4)
             if rule_cer_chars else None),
        ])),
        ("examples", examples),
        ("examples_licence", "Dakshina, CC BY-SA 4.0, Roark et al. (2020); quoted for evaluation"),
    ])
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "transliteration_spotcheck.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    s, r = report["sentence_check"], report["rule_fallback_check"]
    print("sentences {}  CER {:.1%}  word exact match {:.1%} over {} words "
          "(lexicon path {:.1%}, rule path {:.1%})".format(
              s["sentences"], s["character_error_rate"], s["word_exact_match"], s["words_scored"],
              s["word_exact_match_lexicon_path"], s["word_exact_match_rule_path"] or 0.0))
    print("rule fallback alone, {} unseen words: {:.1%} match an attested spelling, CER {:.1%}".format(
        r["words"], r["matches_any_attested_spelling"], r["character_error_rate_to_nearest_attested"]))
    print("-> {}".format(repo_relative(out)))
    return report


def romanise_file(src, dst):
    need(LEXICON)
    src, dst = Path(src), Path(dst)
    if not src.exists():
        sys.exit("{}: not found; run scripts/prepare_parallel_corpus.py first".format(repo_relative(src)))
    romaniser = Romaniser(load_lexicon(LEXICON))
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    rows_in = rows_out = 0
    over_limit = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(str(src), encoding="utf-8", newline="") as fin, \
            open(str(dst), "w", encoding="utf-8", newline="") as fout:
        reader = csv.DictReader(fin, delimiter="\t", quoting=csv.QUOTE_NONE)
        fout.write("english\thindi\n")
        for row in reader:
            rows_in += 1
            roman = romaniser.sentence(row["hindi"])
            if devanagari_fraction(roman) > GENERATOR_LIMIT:
                over_limit += 1
            fout.write("{}\t{}\n".format(row["english"], roman))
            rows_out += 1
    stats = OrderedDict([
        ("issue", "298-76"),
        ("generated_by", "scripts/romanise_parallel.py"),
        ("input", OrderedDict([("path", repo_relative(src)), ("sha256", sha256_file(src)),
                               ("rows", rows_in)])),
        ("output", OrderedDict([("path", repo_relative(dst)), ("sha256", sha256_file(dst)),
                                ("rows", rows_out), ("committed", False)])),
        ("lexicon", OrderedDict([("file", repo_relative(LEXICON)), ("sha256", sha256_file(LEXICON))])),
        ("paths", romaniser.summary()),
        ("rows_still_above_generator_devanagari_limit", over_limit),
    ])
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "romanisation_stats.json"
    out.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    p = stats["paths"]
    print("{} rows Romanised; {} Devanagari words, {:.1%} from the lexicon, {} by rule; "
          "{} rows still above the generator's Devanagari limit".format(
              rows_out, p["devanagari_words"], p["lexicon_share"], p["from_rules"], over_limit))
    print("-> {} (gitignored)\n-> {}".format(repo_relative(dst), repo_relative(out)))
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spot-check", action="store_true")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--input", default=str(REPO_ROOT / "data" / "interim" / "samanantar" / "hi_slice.tsv"))
    ap.add_argument("--output",
                    default=str(REPO_ROOT / "data" / "interim" / "samanantar" / "hi_slice.roman.tsv"))
    args = ap.parse_args(argv)
    if args.spot_check:
        spot_check(args.n, args.seed)
    else:
        romanise_file(args.input, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
