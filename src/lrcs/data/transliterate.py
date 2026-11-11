"""Devanagari-to-Roman transliteration for the code-mix generator.  [298-76]

`codemix.read_parallel` refuses Devanagari on purpose: the task output is
Romanised Hinglish, and mixing a Devanagari Hindi side with English would give
text that is neither. Samanantar's Hindi side is Devanagari, so this module is
a named step that runs **in front of** that refusal. The refusal itself is not
changed, and anything this step fails to Romanise is still caught by it.

How a word is Romanised, in order:

1. **Dakshina lexicon.** `hi.translit.sampled.train.tsv` (Roark et al., 2020)
   gives native words with the Latin spellings people actually typed and how
   many annotators typed each. The most attested spelling wins; ties break
   alphabetically, so the choice is deterministic.
2. **Rule-based fallback** for words the lexicon does not hold: a character map
   in the informal style Hinglish writers use (no diacritics, `aa`/`ee` only
   where length is usually written), plus schwa deletion -- the inherent `a`
   is dropped word-finally and in the VC_CV position (`samajhna`, not
   `samajhana`). Rules cannot know which spelling a writer would choose, so
   this is the weaker path and its share is reported.
3. Non-Devanagari tokens (digits, Latin, punctuation) pass through; Devanagari
   digits become ASCII and the danda becomes a full stop.

Romanisation is not deterministic in the world -- `nahi` and `nahin` are both
right -- so accuracy is measured against human Romanisations rather than
assumed (`scripts/romanise_parallel.py --spot-check`), and the error rate goes
in the datasheet.
"""

import re
from collections import Counter, OrderedDict

_DEVA_WORD = re.compile(r"[ऀ-ॣ०-ॿ]+")
_TOKEN = re.compile(r"[ऀ-ॣ०-ॿ]+|[।॥]|[^\sऀ-ॿ]+")

VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o", "ऍ": "e", "ॠ": "ri",
}
MATRAS = {
    "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e", "ॄ": "ri",
}
CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "ळ": "l", "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "d", "ढ़": "dh",
    "फ़": "f", "य़": "y",
}
NUKTA_FORMS = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "d", "ढ": "dh", "फ": "f", "य": "y"}
NUKTA, HALANT, ANUSVARA, CHANDRABINDU, VISARGA = "़", "्", "ं", "ँ", "ः"
DIGITS = {chr(0x0966 + i): str(i) for i in range(10)}
# In running Hinglish these are usually written short at the end of a word:
# "ladka", "ladki", "hindu", not "ladkaa", "ladkee", "hindoo".
FINAL_SHORTEN = {"aa": "a", "ee": "i", "oo": "u"}


def _units(word):
    """Parse one Devanagari word into units: [consonant, vowel, inherent, coda]."""
    units = []
    i = 0
    while i < len(word):
        ch = word[i]
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch in CONSONANTS:
            cons = CONSONANTS[ch]
            if nxt == NUKTA:
                cons = NUKTA_FORMS.get(ch, cons)
                i += 1
            units.append([cons, "a", True, ""])
        elif ch in VOWELS:
            units.append([None, VOWELS[ch], False, ""])
        elif ch in MATRAS and units and units[-1][0] is not None:
            units[-1][1], units[-1][2] = MATRAS[ch], False
        elif ch == HALANT and units:
            units[-1][1], units[-1][2] = "", False
        elif ch in (ANUSVARA, CHANDRABINDU) and units:
            units[-1][3] += "n"
        elif ch == VISARGA and units:
            units[-1][3] += "h"
        elif ch in DIGITS:
            units.append([DIGITS[ch], "", False, ""])
        # anything else (stray signs, rare letters) is dropped and counted by the caller
        i += 1
    return units


def rule_romanise(word):
    """Romanise one Devanagari word with rules alone."""
    units = _units(word)
    if not units:
        return ""
    # Schwa deletion: word-final inherent a ...
    if len(units) > 1 and units[-1][2] and not units[-1][3]:
        units[-1][1], units[-1][2] = "", False
    # ... and medial inherent a in VC_CV, right to left, never two in a row.
    for k in range(len(units) - 2, 0, -1):
        cur, prev, nxt = units[k], units[k - 1], units[k + 1]
        if (cur[2] and not cur[3] and prev[1] and nxt[0] is not None and nxt[1]
                and not (k + 1 < len(units) and units[k + 1][2] is False and units[k + 1][1] == "")):
            cur[1], cur[2] = "", False
    out = []
    for n, (cons, vowel, _inherent, coda) in enumerate(units):
        if n == len(units) - 1 and not coda:
            vowel = FINAL_SHORTEN.get(vowel, vowel)
        out.append((cons or "") + vowel + coda)
    return "".join(out)


def load_lexicon(path):
    """Dakshina lexicon TSV (native, latin, attestations) -> {native: latin}."""
    votes = {}
    with open(str(path), encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2 or not parts[0] or not parts[1]:
                continue
            count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            votes.setdefault(parts[0], Counter())[parts[1].lower()] += count
    return {native: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            for native, c in votes.items()}


class Romaniser:
    """Lexicon first, rules second. Counts which path each word took."""

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.counts = Counter()

    def word(self, token):
        if token in ("।", "॥"):
            self.counts["punctuation"] += 1
            return "."
        if not _DEVA_WORD.fullmatch(token):
            self.counts["passthrough"] += 1
            return token
        if token in self.lexicon:
            self.counts["lexicon"] += 1
            return self.lexicon[token]
        self.counts["rule"] += 1
        return rule_romanise(token)

    def sentence(self, text):
        tokens = _TOKEN.findall(text or "")
        out = [self.word(t) for t in tokens]
        joined = " ".join(t for t in out if t)
        # Re-attach punctuation the tokeniser split off: "ghar ." -> "ghar."
        return re.sub(r"\s+([.,!?;:)\]])", r"\1", joined)

    def summary(self):
        words = self.counts["lexicon"] + self.counts["rule"]
        return OrderedDict([
            ("devanagari_words", words),
            ("from_lexicon", self.counts["lexicon"]),
            ("from_rules", self.counts["rule"]),
            ("lexicon_share", round(self.counts["lexicon"] / words, 4) if words else 0.0),
            ("passthrough_tokens", self.counts["passthrough"]),
        ])


def levenshtein(a, b):
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]
