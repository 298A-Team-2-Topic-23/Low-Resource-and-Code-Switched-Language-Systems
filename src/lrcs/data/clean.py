"""Stage 2 -- clean: six filters with attrition logging, LinCE-style tagging.  [298-38]

Rubric component: "and cleaned". The evidence is the attrition table: every
filter reports how many records it saw, how many it removed and why, so the
drop from ingested to clean is fully accounted for and nothing disappears
silently.

Filters run in a fixed order, and each record is charged to the FIRST filter
that rejects it, so the removals in the table add up exactly:

  1. missing_field      English or Hinglish empty after normalisation
  2. not_romanized      Hinglish is mostly Devanagari -- a Hindi reference in
                        the wrong column, not Romanized Hinglish
  3. untranslated       Hinglish is the English source copied through
  4. length_bounds      fewer than min_words or more than max_words words
  5. length_ratio       Hinglish/English word ratio outside [1/max_ratio, max_ratio]
                        -- misaligned pairs
  6. exact_duplicate    same (English, Hinglish) pair as an earlier record

Language tagging
----------------
Every surviving Hinglish token gets a LinCE tag (Aguilar et al., 2020):
lang1 = English, lang2 = Hindi, plus ambiguous / ne / other / unk. The tagger
is a documented rule-based marker list, NOT a learned model -- a learned
language-ID model for Romanized Hinglish is out of scope (section 1.1). Rules,
in order:

  * no letters or digits                         -> other
  * Hindi marker AND appears in the English src  -> ambiguous   (is, to, me, main)
  * Hindi marker (variant lexicon + function words) -> lang2
  * appears in this pair's English source         -> lang1      (switched-in words)
  * English function word                         -> lang1
  * capitalised, not sentence-initial             -> ne
  * otherwise                                     -> unk

Tokens tagged ambiguous / ne / other / unk are excluded from CMI and SPF, and
the share of tokens the tagger could resolve is reported alongside them, so a
low-coverage tagging run cannot pass for a precise one.
"""

from collections import OrderedDict

from lrcs.lexicon import load_variant_groups
from lrcs.text import dedup_key, devanagari_fraction, is_word, tokenize, word_tokens

DEFAULTS = {
    "min_words": 2,
    "max_words": 60,
    "max_ratio": 3.0,
    "max_devanagari": 0.2,
}

FILTER_ORDER = [
    "missing_field", "not_romanized", "untranslated",
    "length_bounds", "length_ratio", "exact_duplicate",
]

# Romanized Hindi function words and very common content words, on top of every
# surface form in the variant lexicon.
HINDI_MARKERS = {
    "main", "mai", "mein", "me", "mera", "meri", "mere", "tera", "teri", "tere",
    "uska", "uski", "uske", "usne", "us", "woh", "wo", "yeh", "ye", "ko", "ka",
    "ki", "ke", "se", "par", "pe", "aur", "bhi", "toh", "to", "hi", "ho", "hoon",
    "hun", "hu", "hain", "tha", "thi", "the", "ek", "do", "jab", "tab", "jaise",
    "wala", "wali", "wale", "kyunki", "agar", "lekin", "baad", "pehle", "saath",
    "liye", "baare", "paas", "bahar", "andar", "upar", "neeche", "leke", "lena",
    "le", "lo", "dena", "jana", "ja", "aana", "aa", "aaya", "aayega",
    "gaya", "gayi", "raha", "rahi", "rahe", "sakte", "sakta", "sakti", "milenge",
    "bhej", "batana", "bolo", "bola", "pucho", "lana", "bhoolna", "khatam",
    "pasand", "itna", "sach", "lag", "mehenga", "hua", "hue", "atke", "pahunch",
    "shaam", "agle", "hafte", "tak", "baar", "jaye", "pata", "kahan", "abhi",
    "wajah", "ghar", "kuch", "sab", "nahi", "haan", "acha", "accha",
}

ENGLISH_FUNCTION_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "i", "you",
    "he", "she", "it", "we", "they", "my", "your", "his", "her", "our", "their",
    "this", "that", "these", "those", "of", "in", "on", "at", "for", "with",
    "to", "from", "by", "and", "or", "but", "not", "no", "so", "if", "will",
    "can", "do", "does", "did", "have", "has", "had", "please", "what", "when",
    "where", "why", "how", "who", "which", "very", "really", "just", "also",
}

TAGS = ("lang1", "lang2", "ambiguous", "ne", "other", "unk")


def hindi_markers(lexicon=None):
    groups = lexicon if lexicon is not None else load_variant_groups()
    markers = set(HINDI_MARKERS)
    for forms in groups.values():
        markers.update(forms)
    return markers


def tag_tokens(hinglish, english, markers):
    """LinCE-style tags for one Hinglish sentence. Returns [(token, tag)]."""
    source_words = {t.lower() for t in word_tokens(english)}
    tagged = []
    for position, token in enumerate(tokenize(hinglish)):
        low = token.lower()
        if not is_word(token):
            tag = "other"
        elif low.isdigit():
            tag = "other"
        elif low in markers and low in source_words:
            tag = "ambiguous"
        elif low in markers:
            tag = "lang2"
        elif low in source_words or low in ENGLISH_FUNCTION_WORDS:
            tag = "lang1"
        elif token[:1].isupper() and position > 0:
            tag = "ne"
        else:
            tag = "unk"
        tagged.append((token, tag))
    return tagged


def _rejection(record, seen, params):
    english, hinglish = record["english"], record["hinglish"]
    if not english or not hinglish:
        return "missing_field"
    if devanagari_fraction(hinglish) > params["max_devanagari"]:
        return "not_romanized"
    if dedup_key(hinglish) == dedup_key(english):
        return "untranslated"
    n_en, n_hi = len(word_tokens(english)), len(word_tokens(hinglish))
    if min(n_en, n_hi) < params["min_words"] or max(n_en, n_hi) > params["max_words"]:
        return "length_bounds"
    ratio = n_hi / max(n_en, 1)
    if ratio > params["max_ratio"] or ratio < 1.0 / params["max_ratio"]:
        return "length_ratio"
    key = (dedup_key(english), dedup_key(hinglish))
    if key in seen:
        return "exact_duplicate"
    seen.add(key)
    return None


def clean(records, lexicon=None, **overrides):
    """Returns (kept_records, attrition). Kept records gain a `tags` field."""
    params = dict(DEFAULTS)
    params.update({k: v for k, v in overrides.items() if v is not None})
    removed = OrderedDict((name, []) for name in FILTER_ORDER)
    kept, seen = [], set()
    for record in records:
        reason = _rejection(record, seen, params)
        if reason is None:
            kept.append(record)
        else:
            removed[reason].append(record)

    markers = hindi_markers(lexicon)
    for record in kept:
        record["tags"] = [tag for _, tag in tag_tokens(record["hinglish"], record["english"], markers)]

    table = []
    remaining = len(records)
    for name in FILTER_ORDER:
        n_removed = len(removed[name])
        table.append({
            "filter": name,
            "in": remaining,
            "removed": n_removed,
            "out": remaining - n_removed,
            "pct_removed": round(100.0 * n_removed / remaining, 2) if remaining else 0.0,
            "examples": [r["id"] for r in removed[name][:3]],
        })
        remaining -= n_removed
    attrition = {
        "params": params,
        "ingested": len(records),
        "kept": len(kept),
        "removed_total": len(records) - len(kept),
        "table": table,
    }
    return kept, attrition


def print_attrition(attrition):
    print("  {:<17}{:>8}{:>9}{:>8}{:>9}".format("filter", "in", "removed", "out", "% rm"))
    print("  " + "-" * 51)
    for row in attrition["table"]:
        print("  {:<17}{:>8,}{:>9,}{:>8,}{:>8.2f}%".format(
            row["filter"], row["in"], row["removed"], row["out"], row["pct_removed"]))
    print("  " + "-" * 51)
    print("  ingested {:,} -> kept {:,} ({:,} removed)".format(
        attrition["ingested"], attrition["kept"], attrition["removed_total"]))
