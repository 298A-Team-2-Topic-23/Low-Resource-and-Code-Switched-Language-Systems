"""Code-mixing statistics over LinCE-tagged sentences.  [298-38]

Same definitions as analysis/tokenizer_fertility.py --cmi-only (298-13/298-22),
re-stated over LinCE tags so the pipeline does not import a script. Only lang1
(English) and lang2 (Hindi) count as language tokens; ambiguous, ne, other and
unk are language-independent for every metric here, as in Das and Gambäck.

  CMI         100 * (1 - dominant-language share). 0 monolingual, 50 even mix.
  SPF         switch points / (language tokens - 1). The measured SPF is what
              governs synthetic-data sampling for M4.
  M-index     Barnett et al.; 0 monolingual, 1 perfectly balanced.
  burstiness  Goh and Barabasi over monolingual run lengths; +1 bursty,
              -1 regular alternation.
"""

import statistics
from collections import Counter

LANG_TAGS = ("lang1", "lang2")


def language_tags(tags):
    return [t for t in tags if t in LANG_TAGS]


def cmi(tags):
    langs = language_tags(tags)
    if not langs:
        return 0.0
    return 100.0 * (1.0 - max(Counter(langs).values()) / len(langs))


def switch_points(tags):
    langs = language_tags(tags)
    return sum(1 for a, b in zip(langs, langs[1:]) if a != b), len(langs)


def spf(tags):
    """Per-sentence switch-point fraction; None when there is no adjacent pair."""
    switches, n = switch_points(tags)
    return switches / (n - 1) if n > 1 else None


def m_index(tags):
    langs = language_tags(tags)
    counts = Counter(langs)
    if len(counts) < 2:
        return 0.0
    total = len(langs)
    sum_p2 = sum((c / total) ** 2 for c in counts.values())
    return (1.0 - sum_p2) / ((len(counts) - 1) * sum_p2)


def monolingual_spans(tags):
    spans, run, prev = [], 0, None
    for tag in language_tags(tags):
        if tag == prev:
            run += 1
        else:
            if run:
                spans.append(run)
            run, prev = 1, tag
    if run:
        spans.append(run)
    return spans


def burstiness(spans):
    if len(spans) < 2:
        return None
    mean = statistics.mean(spans)
    sd = statistics.pstdev(spans)
    return None if sd + mean == 0 else (sd - mean) / (sd + mean)


def corpus_stats(tag_lists):
    """Aggregate statistics over a list of per-sentence tag lists."""
    per_cmi = [cmi(tags) for tags in tag_lists]
    per_spf = [v for v in (spf(tags) for tags in tag_lists) if v is not None]
    total_switches = total_pairs = 0
    all_tags, all_spans = [], []
    for tags in tag_lists:
        sw, n = switch_points(tags)
        total_switches += sw
        total_pairs += max(n - 1, 0)
        all_tags.extend(tags)
        all_spans.extend(monolingual_spans(tags))
    tag_counts = Counter(all_tags)
    word_tags = sum(c for t, c in tag_counts.items() if t != "other")
    mixed = [c for c in per_cmi if c > 0]
    n = len(tag_lists)
    return {
        "n_sentences": n,
        "tag_counts": dict(sorted(tag_counts.items())),
        "tagger_coverage": (
            (tag_counts["lang1"] + tag_counts["lang2"]) / word_tags if word_tags else 0.0
        ),
        "cmi_mean_all": statistics.mean(per_cmi) if per_cmi else 0.0,
        "cmi_mean_mixed_only": statistics.mean(mixed) if mixed else 0.0,
        "frac_sentences_mixed": len(mixed) / n if n else 0.0,
        "switch_point_fraction": total_switches / total_pairs if total_pairs else 0.0,
        "spf_mean_per_sentence": statistics.mean(per_spf) if per_spf else 0.0,
        "n_switch_points": total_switches,
        "m_index": m_index(all_tags),
        "burstiness": burstiness(all_spans),
        "mean_span_length": statistics.mean(all_spans) if all_spans else 0.0,
        "per_sentence_cmi": per_cmi,
        "per_sentence_spf": per_spf,
    }
