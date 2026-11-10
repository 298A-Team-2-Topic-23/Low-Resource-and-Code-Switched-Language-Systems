#!/usr/bin/env python3
"""
Devanagari-to-Roman post-processing for the reproduced baseline.  [Linear 298-52]

Gahoi et al. (2022), section 3.1.3: their mBART output "was in a mixed script
(Roman + Devanagari)", so every Devanagari word was transliterated to Roman
before scoring. Table 2 reports the effect of each step:

  Normal Output                                         ROUGE-L 0.39091  WER 0.81884
  With Automated Transliteration                        ROUGE-L 0.48376  WER 0.72561
  ... + Dictionary Based Transliteration                ROUGE-L 0.61667  WER 0.63342

The automatic step used "the transliteration function from indicate library".
The dictionary of "most common words and numbers" was never released, so the
third row cannot be rebuilt; this script reproduces the first two. The
reproduction is compared with the 0.48376 row, and the 0.61667 row is reported
as out of reach for a stated reason.

Backends
--------
  indicate   The paper's library. indicate 0.1.0 (22 August 2022) is the release
             current at submission time; it is a TensorFlow word-level model
             called as `indicate.hindi2english(word)`. Install it in its own
             environment if TensorFlow will not resolve alongside torch.
  sanscript  indic_transliteration's ITRANS scheme, lower-cased. Pure Python and
             always installable, but it is NOT the paper's tool: a run that uses
             it is a deviation and the run record says so.

Only tokens that contain Devanagari are touched. Roman tokens, numbers and
punctuation pass through unchanged, so a fully Roman output is a no-op.

Usage
-----
  python models/transliterate.py out/baseline/both.s13.raw.txt \\
      out/baseline/both.s13.auto.txt --backend indicate
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# A Devanagari run, so "star(स्तर)" transliterates the word and keeps the brackets.
_DEVANAGARI_RUN = re.compile(r"[ऀ-ॿ]+")
# Devanagari digits and the danda have fixed Roman equivalents; handled here so
# no backend has to get them right.
_FIXED = str.maketrans({"०": "0", "१": "1", "२": "2", "३": "3", "४": "4", "५": "5",
                        "६": "6", "७": "7", "८": "8", "९": "9", "।": ".", "॥": "."})


def has_devanagari(text):
    return bool(DEVANAGARI.search(text or ""))


def indicate_backend():
    try:
        from indicate import hindi2english
    except ImportError:
        sys.exit("the paper's backend needs indicate: pip install indicate==0.1.0 "
                 "(TensorFlow); or pass --backend sanscript and record the deviation")
    return lambda word: hindi2english(word).strip()


def sanscript_backend():
    try:
        from indic_transliteration import sanscript
    except ImportError:
        sys.exit("pip install indic-transliteration")
    # ITRANS is a scholarly scheme; three adjustments bring it to the way Hinglish
    # is typed, because without them nearly every word differs from a human
    # reference: long vowels (A, I, U) are doubled inside a word (baat, zameen)
    # and single at its end (pata, ji); the anusvara (M) and candrabindu (.N) are
    # written n, or m before p/b/m; and a word-final inherent vowel is silent
    # (kalyANa -> kalyan).
    def word_fn(word):
        roman = sanscript.transliterate(word, sanscript.DEVANAGARI, sanscript.ITRANS)
        roman = re.sub(r"M(?=[pbm])", "m", roman).replace("M", "n").replace(".N", "n")
        roman = re.sub(r"[AIU](?=[A-Za-z])",
                       lambda m: {"A": "aa", "I": "ee", "U": "oo"}[m.group(0)], roman)
        roman = re.sub(r"[^a-z]", "", roman.lower())
        if len(roman) > 2 and _ends_in_inherent_vowel(word):
            roman = roman[:-1]
        return roman
    return word_fn


_VIRAMA, _NUKTA = "्", "़"


def _ends_in_inherent_vowel(word):
    """True when the last Devanagari letter is a bare consonant (क-ह, with or
    without a nukta), so its vowel is the inherent a that Hindi does not voice."""
    last = word.rstrip(_NUKTA)[-1:]
    return bool(last) and "क" <= last <= "ह" and not word.endswith(_VIRAMA)


BACKENDS = {"indicate": indicate_backend, "sanscript": sanscript_backend}


def transliterate_line(line, word_fn, cache=None):
    """Romanise every Devanagari run in one line; everything else is untouched."""
    cache = {} if cache is None else cache
    line = line.translate(_FIXED)

    def _sub(match):
        run = match.group(0)
        if run not in cache:
            cache[run] = word_fn(run)
        return cache[run]

    return _DEVANAGARI_RUN.sub(_sub, line)


def script_stats(lines):
    with_dev = sum(1 for l in lines if has_devanagari(l))
    return {"lines": len(lines), "lines_with_devanagari": with_dev,
            "share": round(with_dev / max(len(lines), 1), 4)}


def transliterate_file(src, dst, backend):
    lines = Path(src).read_text(encoding="utf-8").splitlines()
    word_fn, cache = BACKENDS[backend](), {}
    out = [transliterate_line(l, word_fn, cache) for l in lines]
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text("\n".join(out) + "\n", encoding="utf-8")
    return {"backend": backend, "paper_backend": backend == "indicate",
            "before": script_stats(lines), "after": script_stats(out),
            "distinct_devanagari_words": len(cache)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src", help="raw model output, one sentence per line")
    ap.add_argument("dst", help="where the Romanised output is written")
    ap.add_argument("--backend", choices=sorted(BACKENDS), default="indicate")
    args = ap.parse_args(argv)
    info = transliterate_file(args.src, args.dst, args.backend)
    print(json.dumps(info, indent=2))
    if not info["paper_backend"]:
        print("note: sanscript is not the paper's transliterator; label this run a "
              "deviation from Gahoi et al. (2022), section 3.1.3", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
