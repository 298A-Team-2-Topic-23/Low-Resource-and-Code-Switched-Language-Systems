"""Text helpers shared by every pipeline stage.

One normalisation and one tokeniser for the whole pipeline. If cleaning, split
grouping and EDA each tokenised their own way, the counts in the attrition table
and the statistics in data_statistics.json would stop describing the same text.
"""

import hashlib
import re
import unicodedata

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")
# Words (with an optional internal apostrophe: don't, it's) or single
# non-space symbols. Punctuation is kept as its own token so the tagger can mark
# it `other` instead of silently dropping it.
_TOKEN = re.compile(r"\w+(?:'\w+)?|[^\w\s]", re.UNICODE)
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def normalise(text):
    """NFC plus whitespace collapse. Applied once, at ingest, to every field."""
    if text is None:
        return ""
    return _WS.sub(" ", unicodedata.normalize("NFC", str(text))).strip()


def dedup_key(text):
    """Key used to decide that two sentences are the same sentence.

    Matches dedup_key() in the team's split script (298-11) on purpose: NFKC,
    lower-case, punctuation to space, whitespace collapsed. Case, punctuation
    and spacing variants of one sentence collapse to one key.
    """
    t = unicodedata.normalize("NFKC", text or "").lower()
    t = _PUNCT.sub(" ", t)
    return _WS.sub(" ", t).strip()


def tokenize(text):
    return _TOKEN.findall(text or "")


def is_word(token):
    return any(ch.isalnum() for ch in token)


def word_tokens(text):
    return [t for t in tokenize(text) if is_word(t)]


def devanagari_fraction(text):
    """Share of non-space characters that are Devanagari. Romanized Hinglish
    should be ~0; a Devanagari reference that leaked into the Hinglish column
    is ~1."""
    chars = [c for c in (text or "") if not c.isspace()]
    if not chars:
        return 0.0
    return sum(1 for c in chars if _DEVANAGARI.match(c)) / len(chars)


def record_id(english, hinglish):
    """Content hash, so an id means the same pair on every machine and every
    run. Built from the dedup keys, so a whitespace-only difference cannot mint
    a new id."""
    payload = "{}\t{}".format(dedup_key(english), dedup_key(hinglish))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()
