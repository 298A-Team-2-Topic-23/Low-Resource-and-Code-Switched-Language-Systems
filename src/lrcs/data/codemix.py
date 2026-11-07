"""Synthetic code-mixing under the Equivalence Constraint.  [298-17]

Model 4 needs code-switched text that is not simply random word substitution.
The Equivalence Constraint (Poplack 1980; operationalised for generation by the
GCM toolkit, Rizvi et al. 2021) says a switch is licensed only where the surface
word orders of the two languages agree, so switching cannot break a constituent
whose order differs between them.

What this module implements
---------------------------
1. `align` -- IBM Model 1 by EM over the parallel corpus. No external aligner,
   no network, deterministic for a given corpus and iteration count.
2. `blocks` -- the alignment is cut into maximal monotonic blocks. A boundary
   between two blocks is a licensed switch point: no alignment link crosses it,
   so both languages order the material either side the same way. This is the
   Equivalence Constraint applied to alignment rather than to parse trees.
3. `generate` -- each block is realised in one language or the other, giving up
   to 2^n candidates per sentence, minus the all-English and all-Hindi ones
   which are not code-mixed.
4. `match_distribution` -- candidates are selected so the switch-point fraction
   of the emitted batch matches a target distribution, rather than sampling
   uniformly. Sampling randomly produces text with far more switching than
   people actually write, and a model trained on it learns the wrong
   distribution.

What it does NOT implement
--------------------------
* **Parse-based EC.** The real constraint is stated over constituent structure.
  Monotonic alignment blocks approximate it and will accept a few switches a
  parser would reject, and reject a few it would accept. Stated plainly because
  the difference matters if these outputs are ever reported as GCM output.
* **Transliteration.** Input must already be Romanised on both sides. Devanagari
  input is refused rather than silently mixed, because the target task is
  Romanised Hinglish and a mixed-script output would be neither. Lifting this
  needs Dakshina, which `docs/datasheet.md` lists and the repository does not
  have.
* **Validation.** Nothing here has been run on Samanantar or IIT Bombay, and no
  model has been trained on its output. It is a stood-up pipeline, not a
  validated data source.
"""

import math
import random
import re
from collections import OrderedDict, defaultdict

from lrcs.text import devanagari_fraction, word_tokens

EN, HI = "en", "hi"
NULL = "<null>"
DEFAULT_ITERATIONS = 12
MIN_ALIGNMENT_COVERAGE = 0.35


class CodeMixError(RuntimeError):
    pass


# ----------------------------------------------------------------- alignment
def align(pairs, iterations=DEFAULT_ITERATIONS):
    """IBM Model 1 by EM. Returns t(hindi word | english word) as a dict.

    Model 1 ignores word order, which is exactly right here: the ordering
    information we need comes back in `blocks`, from where the links land.
    Iteration order over dicts is made deterministic by sorting, so the same
    corpus gives the same table on any run.
    """
    source_vocab = sorted({w for _en, hi in pairs for w in hi})
    if not source_vocab:
        raise CodeMixError("no Hindi tokens in the corpus; nothing to align")

    uniform = 1.0 / len(source_vocab)
    t = defaultdict(lambda: uniform)
    for _ in range(iterations):
        counts = defaultdict(float)
        totals = defaultdict(float)
        for en, hi in pairs:
            english = [NULL] + list(en)
            for h in hi:
                denom = sum(t[(h, e)] for e in english)
                if denom <= 0:
                    continue
                for e in english:
                    delta = t[(h, e)] / denom
                    counts[(h, e)] += delta
                    totals[e] += delta
        if not totals:
            break
        t = defaultdict(lambda: 0.0)
        for (h, e), c in sorted(counts.items()):
            if totals[e] > 0:
                t[(h, e)] = c / totals[e]
    return t


def viterbi_links(en, hi, t):
    """Best English index for each Hindi token, or None for the null word."""
    links = []
    for j, h in enumerate(hi):
        best_i, best_p = None, t[(h, NULL)]
        for i, e in enumerate(en):
            p = t[(h, e)]
            if p > best_p:
                best_i, best_p = i, p
        links.append((best_i, j) if best_i is not None else (None, j))
    return links


def coverage(links):
    if not links:
        return 0.0
    return sum(1 for i, _ in links if i is not None) / len(links)


# -------------------------------------------------------------------- blocks
def blocks(en, hi, links):
    """Cut the sentence into maximal monotonic blocks.

    A block is a run of Hindi positions whose English links never go backwards.
    A boundary between two blocks is therefore order-preserving in both
    languages, which is the Equivalence Constraint condition this module
    enforces.

    Index spans are de-duplicated. Model 1 is many-to-one: several Hindi tokens
    routinely link to the same English token (`nahi kiya` -> `did`), and keeping
    one entry per link emits that English word once per link, so a realisation
    came out as "did did did".

    Returns a list of (en_span, hi_span) index pairs covering the sentence.
    """
    out, cur_hi, cur_en = [], [], []
    last_i = -1
    for i, j in links:
        if i is None:                      # unaligned: stays with the block
            cur_hi.append(j)
            continue
        if i < last_i:                     # crossing link -> close the block
            out.append((sorted(set(cur_en)), sorted(set(cur_hi))))
            cur_hi, cur_en = [], []
        cur_hi.append(j)
        cur_en.append(i)
        last_i = i
    if cur_hi or cur_en:
        out.append((sorted(set(cur_en)), sorted(set(cur_hi))))

    # English tokens no block claimed are attached to the nearest block, so the
    # English side of a realisation is still a complete sentence.
    claimed = {i for en_span, _ in out for i in en_span}
    for i in range(len(en)):
        if i in claimed or not out:
            continue
        nearest = min(range(len(out)),
                      key=lambda b: min((abs(i - x) for x in out[b][0]),
                                        default=len(en)))
        out[nearest][0].append(i)
        out[nearest][0].sort()
    return [(e, h) for e, h in out if e or h]


# ---------------------------------------------------------------- generation
def realise(en, hi, spans, choice):
    """Build one code-mixed sentence. `choice[k]` is EN or HI for block k."""
    tokens = []
    for (en_span, hi_span), lang in zip(spans, choice):
        source, span = (en, en_span) if lang == EN else (hi, hi_span)
        tokens.extend(source[i] for i in span)
    return tokens


def switch_points(choice):
    return sum(1 for a, b in zip(choice, choice[1:]) if a != b)


def switch_point_fraction(choice, n_tokens):
    """Switch points per token boundary -- the same definition the corpus
    statistics use, so a generated batch is comparable with the measured one."""
    if n_tokens < 2:
        return 0.0
    return switch_points(choice) / (n_tokens - 1)


def candidates(en, hi, spans, max_blocks=12):
    """Every EC-licensed realisation that is actually mixed.

    All-English and all-Hindi are dropped: they are the inputs, not
    code-mixing. Sentences with more than `max_blocks` blocks are skipped
    rather than enumerated, because 2^n grows faster than the value of the
    extra variety.
    """
    n = len(spans)
    if n < 2 or n > max_blocks:
        return []
    out = []
    for mask in range(1, (1 << n) - 1):
        choice = [EN if (mask >> k) & 1 else HI for k in range(n)]
        tokens = realise(en, hi, spans, choice)
        if not tokens:
            continue
        out.append({
            "tokens": tokens,
            "text": " ".join(tokens),
            "choice": choice,
            "switch_points": switch_points(choice),
            "spf": switch_point_fraction(choice, len(tokens)),
        })
    return out


# ------------------------------------------------- distribution matching
def match_distribution(pool, target_mean_spf, n, seed, running=(0.0, 0)):
    """Pick `n` candidates whose mean SPF lands as close to the target as the
    pool allows.

    At each step take whichever remaining candidate moves the running mean
    closest to the target. That is O(n x pool) and, unlike accepting anything
    that does not make matters much worse, it cannot drift: an earlier version
    took the first candidate unconditionally and ended 0.07 above target.

    The pool is sorted before the seeded shuffle so dict and set order cannot
    reach the result, and the shuffle only breaks ties between candidates that
    are equally good.

    Sampling uniformly instead would emit far more switching than the measured
    corpus has -- HinGE's switch-point fraction is 0.2398.
    """
    if not pool or n <= 0:
        return []
    remaining = sorted(pool, key=lambda c: (c["spf"], c["text"]))
    random.Random(seed).shuffle(remaining)

    # `running` carries the batch so far. Steering the whole batch matters
    # because a sentence cut into two blocks has exactly two mixed
    # realisations, both with one switch point, so it has no freedom of its
    # own: only later sentences can pull the mean back.
    total, count = running
    chosen = []
    while remaining and len(chosen) < n:
        best = min(range(len(remaining)),
                   key=lambda i: abs((total + remaining[i]["spf"]) / (count + 1)
                                     - target_mean_spf))
        pick = remaining.pop(best)
        chosen.append(pick)
        total += pick["spf"]
        count += 1
    return chosen


# --------------------------------------------------------------- the pipeline
def read_parallel(path):
    """TSV with an english and a romanised-hindi column. Refuses Devanagari."""
    pairs = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            english, hindi = parts[0].strip(), parts[1].strip()
            if lineno == 1 and english.lower() in {"english", "en", "source"}:
                continue
            if not english or not hindi:
                continue
            if devanagari_fraction(hindi) > 0.05:
                raise CodeMixError(
                    "line {}: the Hindi side is in Devanagari. This generator "
                    "produces Romanised Hinglish and does not transliterate; "
                    "that needs Dakshina (docs/datasheet.md), which is not in "
                    "the repository. Supply Romanised Hindi.".format(lineno))
            pairs.append((word_tokens(english), word_tokens(hindi)))
    if not pairs:
        raise CodeMixError("{}: no usable parallel pairs".format(path))
    return pairs


def generate(pairs, target_mean_spf, per_sentence, seed,
             iterations=DEFAULT_ITERATIONS):
    """Run the whole thing. Returns (rows, stats)."""
    table = align(pairs, iterations=iterations)
    rows, skipped = [], OrderedDict(
        (k, 0) for k in ("low_coverage", "too_few_blocks", "no_candidates"))
    coverages = []
    running_total, running_count = 0.0, 0
    pool_size = 0

    for index, (en, hi) in enumerate(pairs):
        links = viterbi_links(en, hi, table)
        cov = coverage(links)
        coverages.append(cov)
        if cov < MIN_ALIGNMENT_COVERAGE:
            skipped["low_coverage"] += 1
            continue
        spans = blocks(en, hi, links)
        if len(spans) < 2:
            skipped["too_few_blocks"] += 1
            continue
        pool = candidates(en, hi, spans)
        if not pool:
            skipped["no_candidates"] += 1
            continue
        pool_size += len(pool)
        for pick in match_distribution(pool, target_mean_spf, per_sentence,
                                       seed + index,
                                       running=(running_total, running_count)):
            running_total += pick["spf"]
            running_count += 1
            rows.append({
                "source_index": index,
                "english": " ".join(en),
                "hindi": " ".join(hi),
                "codemixed": pick["text"],
                "blocks": len(spans),
                "switch_points": pick["switch_points"],
                "spf": round(pick["spf"], 4),
                "alignment_coverage": round(cov, 4),
            })

    spfs = [r["spf"] for r in rows]
    stats = OrderedDict([
        ("pairs_in", len(pairs)),
        ("rows_out", len(rows)),
        ("skipped", dict(skipped)),
        ("target_mean_spf", target_mean_spf),
        ("mean_spf", round(sum(spfs) / len(spfs), 4) if spfs else 0.0),
        ("mean_alignment_coverage",
         round(sum(coverages) / len(coverages), 4) if coverages else 0.0),
        ("em_iterations", iterations),
        ("candidate_pool", pool_size),
        # How much of the available variety the batch consumed. Distribution
        # matching can only steer what it can leave behind, so a high figure
        # explains a missed target better than the target itself does.
        ("pool_utilisation",
         round(len(rows) / pool_size, 3) if pool_size else 0.0),
    ])
    stats["spf_within_0.05_of_target"] = bool(
        spfs and abs(stats["mean_spf"] - target_mean_spf) <= 0.05)
    stats["pool_exhausted"] = stats["pool_utilisation"] > 0.5
    return rows, stats
