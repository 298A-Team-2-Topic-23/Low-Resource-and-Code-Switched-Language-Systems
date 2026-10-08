"""Synthetic English -> Romanized Hinglish corpus for offline runs.  [298-38]

Exists so the whole pipeline can be demonstrated with no network and no raw
data on the machine. It is NOT training data and none of its numbers describe
HinGE. Every figure and statistics file produced from it says "synthetic".

What it plants, on purpose, so every stage has something real to do:
  * orthographic variance  -- Hindi words re-spelled from the variant lexicon
                              (nahi/nhi/nahin), the effect the project studies
  * multiple references    -- 2-3 Hinglish references for some sources, as in
                              HinGE, which must all land in one split
  * near-duplicate sources -- case/punctuation variants and one-word edits,
                              which the split stage must group
  * one row type per cleaning filter: empty target, Devanagari target,
    untranslated copy, over-long row, length-ratio outlier, exact duplicate

Deterministic: same n and seed -> byte-identical file.
"""

import csv
import random

from lrcs.lexicon import load_variant_groups

# (English template, Hinglish template). English content words are reused in the
# Hinglish side, which is what makes the output code-switched rather than Hindi.
TEMPLATES = [
    ("I am going to the {place} {time_en}.", "main {time_hi} {place} ja raha hoon."),
    ("Please send me the {noun} {time_en}.", "please mujhe {noun} {time_hi} bhej do."),
    ("I did not like the {noun} at the {place}.", "mujhe {place} wala {noun} bilkul pasand nahi aaya."),
    ("Why is the {noun} so {adj} {time_en}?", "{time_hi} {noun} itna {adj} kyun hai?"),
    ("We will meet at the {place} {time_en}.", "hum {time_hi} {place} pe milenge."),
    ("Can you check the {noun} once {time_en}?", "kya tum {time_hi} ek baar {noun} check kar sakte ho?"),
    ("My {noun} is not working {time_en}.", "mera {noun} {time_hi} kaam nahi kar raha hai."),
    ("The {noun} at the {place} was really {adj}.", "{place} ka {noun} sach mein bahut {adj} tha."),
    ("Do not forget to bring the {noun} {time_en}.", "{time_hi} {noun} lana mat bhoolna."),
    ("I have to finish the {noun} {time_en}.", "mujhe {time_hi} {noun} khatam karna hai."),
    ("She is waiting outside the {place} with the {noun}.", "woh {noun} leke {place} ke bahar wait kar rahi hai."),
    ("What happened to the {adj} {noun}?", "us {adj} {noun} ko kya hua?"),
    ("Tell me when the {noun} is ready {time_en}.", "jab {noun} ready ho jaye toh {time_hi} mujhe batana."),
    ("I don't know where the {place} is, ask about the {noun}.", "mujhe nahi pata {place} kahan hai, {noun} ke baare mein pucho."),
    ("This {noun} is very {adj}, buy it {time_en}.", "yeh {noun} bahut {adj} hai, {time_hi} le lo."),
    ("He said the {noun} will come {time_en}.", "usne bola {noun} {time_hi} aayega."),
    ("We are stuck near the {place} {time_en}.", "hum {time_hi} {place} ke paas atke hue hain."),
    ("Is the {adj} {noun} still available at the {place}?", "kya {place} pe {adj} {noun} abhi bhi available hai?"),
    ("Call me after you reach the {place} {time_en}.", "{time_hi} {place} pahunch ke mujhe call karna."),
    ("The {noun} looks {adj} but it is expensive.", "{noun} {adj} lag raha hai par mehenga hai."),
]

NOUNS = [
    "laptop", "phone", "report", "ticket", "order", "package", "charger",
    "presentation", "assignment", "bill", "cake", "movie", "song", "jacket",
    "book", "form", "invoice", "parcel", "file", "camera", "bike", "watch",
    "recipe", "menu", "schedule", "contract", "resume", "poster", "playlist",
    "notebook", "bag", "shoes", "headphones", "keyboard", "receipt",
    "document", "video", "game", "printer", "sofa",
]
PLACES = [
    "office", "station", "airport", "mall", "hospital", "college", "library",
    "gym", "market", "hotel", "restaurant", "bank", "metro", "temple",
    "canteen", "cafe", "theatre", "hostel", "parking", "clinic",
]
ADJECTIVES = [
    "expensive", "cheap", "slow", "boring", "amazing", "simple", "confusing",
    "heavy", "late", "small", "beautiful", "spicy", "noisy", "cold", "crowded",
]
TIMES = [
    ("today", "aaj"), ("tomorrow", "kal"), ("tonight", "aaj raat"),
    ("right now", "abhi"), ("this evening", "aaj shaam"),
    ("in the morning", "subah"), ("next week", "agle hafte"),
    ("on Monday", "Monday ko"), ("after lunch", "lunch ke baad"),
    ("by evening", "shaam tak"),
]
DEVANAGARI = [
    "मैं कल बाज़ार जाऊँगा।", "यह बहुत अच्छा है।", "मुझे नहीं पता।",
    "तुम कहाँ हो?", "आज बहुत गर्मी है।",
]

# Probability of each row type. "base" is a new English source; the rest
# either add a reference to an existing source or plant one defect.
ROW_TYPES = [
    ("base", 0.70),
    ("extra_ref", 0.17),
    ("near_dup_source", 0.04),
    ("exact_dup", 0.03),
    ("empty_target", 0.015),
    ("devanagari_target", 0.01),
    ("untranslated", 0.015),
    ("overlong", 0.01),
    ("ratio_outlier", 0.01),
]

VARIANT_RATE = 0.35   # chance a lexicon word is re-spelled as a non-canonical variant


def _pick(rng, weighted):
    r = rng.random() * sum(w for _, w in weighted)
    for name, w in weighted:
        r -= w
        if r <= 0:
            return name
    return weighted[-1][0]


def _respell(text, rng, groups, index):
    out = []
    for word in text.split(" "):
        core = word.rstrip(".,?!")
        tail = word[len(core):]
        label = index.get(core.lower())
        if label is not None and rng.random() < VARIANT_RATE:
            core = rng.choice(groups[label][1:] or groups[label])
        out.append(core + tail)
    return " ".join(out)


def _base_pair(rng):
    en_t, hi_t = rng.choice(TEMPLATES)
    time_en, time_hi = rng.choice(TIMES)
    slots = {
        "noun": rng.choice(NOUNS), "place": rng.choice(PLACES),
        "adj": rng.choice(ADJECTIVES), "time_en": time_en, "time_hi": time_hi,
    }
    en = en_t.format(**slots)
    return en[0].upper() + en[1:], hi_t.format(**slots)


def generate(n, seed, lexicon=None):
    """Return n rows of (english, hindi, hinglish). Hindi is left empty: the
    synthetic corpus has no Devanagari reference column."""
    if n < 1:
        raise ValueError("n must be >= 1")
    rng = random.Random(seed)
    groups = lexicon if lexicon is not None else load_variant_groups()
    index = {}
    for label, forms in groups.items():
        for form in forms:
            index.setdefault(form, label)

    rows = []
    bases = []          # (english, canonical hinglish) of every base source
    seen_sources = set()
    while len(rows) < n:
        kind = _pick(rng, ROW_TYPES) if bases else "base"
        if kind == "base":
            en, hi = _base_pair(rng)
            if en in seen_sources:
                continue
            seen_sources.add(en)
            bases.append((en, hi))
            rows.append((en, "", _respell(hi, rng, groups, index)))
        elif kind == "extra_ref":
            en, hi = rng.choice(bases)
            rows.append((en, "", _respell(hi, rng, groups, index)))
        elif kind == "near_dup_source":
            en, hi = rng.choice(bases)
            if rng.random() < 0.5:
                en2 = en.upper().rstrip(".?") + "!"          # same dedup key
            else:
                en2 = "So " + en[0].lower() + en[1:]         # one-word edit
            rows.append((en2, "", _respell(hi, rng, groups, index)))
        elif kind == "exact_dup":
            rows.append(rng.choice(rows))
        elif kind == "empty_target":
            en, _ = rng.choice(bases)
            rows.append((en, "", ""))
        elif kind == "devanagari_target":
            en, _ = rng.choice(bases)
            rows.append((en, "", rng.choice(DEVANAGARI)))
        elif kind == "untranslated":
            en, _ = rng.choice(bases)
            rows.append((en, "", en))
        elif kind == "overlong":
            en, hi = rng.choice(bases)
            rows.append((" ".join([en] * 12), "", " ".join([hi] * 12)))
        elif kind == "ratio_outlier":
            # long English, truncated Hinglish: a misaligned pair
            en, hi = rng.choice(bases)
            extra = " ".join(rng.choice(bases)[0] for _ in range(3))
            words = hi.split(" ")
            rows.append((en + " " + extra, "", " ".join(words[: max(2, len(words) // 2)])))
    return rows


def write_tsv(rows, path):
    with open(str(path), "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["english", "hindi", "hinglish"])
        writer.writerows(rows)
