#!/usr/bin/env python3
"""
Tokenizer fertility and code-mixing statistics.  [Linear 298-13 and 298-22, owner: Sarvesh]

This is the CPU-only test of the project's central hypothesis. Quality loss on
Hinglish is usually blamed on missing data, and tokenizer inefficiency is usually
blamed on non-Latin script. Hinglish is already written in Roman script, so if
fertility is still high the cause has to be something else -- our claim is
orthographic variance. `nahi`, `nhi`, `nahii` and `nahin` are one word that the
tokenizer sees as four unrelated vocabulary entries.

`spelling_variant_burden` is the column that tests that claim directly. Everything
else in the fertility table is context for it.

Two modes.

Fertility, across four text slices and every candidate tokenizer
----------------------------------------------------------------
    python analysis/tokenizer_fertility.py \
        --corpus en=data/slices/en.txt \
        --corpus hi_deva=data/slices/hi_deva.txt \
        --corpus hi_roman=data/slices/hi_roman.txt \
        --corpus hinglish=data/slices/hinglish.txt \
        --tokenizer Qwen/Qwen3-8B \
        --tokenizer google/gemma-3-12b-it \
        --out results/fertility.csv

Writes results/fertility.csv (one row per tokenizer x slice) and
results/fertility.variants.csv (one row per tokenizer x variant group, which is
where the burden number is auditable group by group rather than as one mean).

Code-mixing statistics on a language-tagged corpus (298-22)
-----------------------------------------------------------
    python analysis/tokenizer_fertility.py --cmi-only --conll data/hinge_tagged.conll

Prints and optionally writes CMI, Switch-Point Fraction, M-index and burstiness.
The SPF number from this mode is what the GCM synthetic sampling in 298-17 has to
match -- sampling synthetic output randomly instead of SPF-matched gives an
unnatural switching distribution, which is worse than no synthetic data at all.

Self-test, no corpora and no network needed
-------------------------------------------
    python analysis/tokenizer_fertility.py --selftest

Expected fertility ranges. If yours are far outside these, suspect the slices
before you suspect the tokenizer:

    English            1.2 - 1.4
    Devanagari Hindi   2.5 - 4.0
    Romanized Hindi    1.8 - 2.5
    Romanized Hinglish similar to Romanized Hindi, possibly higher

If Romanized Hinglish fertility comes out low, that is a finding and not a
failure. Romanization is known to cut fertility two to four times on its own. Low
headroom there is evidence that spelling variance rather than script is the right
framing, so it gets reported, not buried.
"""

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VARIANTS = Path(__file__).resolve().parent / "spelling_variants.tsv"

# SentencePiece and BPE byte fallbacks surface as <0xE0> style pieces. A high rate
# on a Roman-script slice means the tokenizer is falling off its vocabulary
# entirely, which is a different failure from merely splitting a word up.
BYTE_FALLBACK_RE = re.compile(r"^<0x[0-9A-Fa-f]{2}>$")

# Language tags we do not count as evidence of either language. Language-independent
# tokens (punctuation, numerals, emoji) must be excluded from CMI and SPF or every
# metric drifts with how heavily punctuated the corpus happens to be.
NEUTRAL_TAGS = {"univ", "ne", "other", "acro", "punct", "num", "x", "o", ""}


# --------------------------------------------------------------------- tokenizers

class WhitespaceTokenizer:
    """Stand-in used by --selftest so the metric maths can be checked without a
    network round trip. Splits on non-alphanumeric runs, which makes the expected
    numbers hand-computable."""

    name = "selftest/whitespace"

    def encode_tokens(self, text):
        return [t for t in re.split(r"([^\w]+)", text) if t.strip()]


class HFTokenizer:
    """Thin wrapper so the metric code never has to care which backend it got."""

    def __init__(self, model_id, trust_remote_code=False):
        try:
            from transformers import AutoTokenizer
        except ImportError:
            sys.exit(
                "transformers is required for real tokenizers: pip install transformers\n"
                "(or run --selftest, which needs nothing)"
            )
        self.name = model_id
        self._tok = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=trust_remote_code
        )

    def encode_tokens(self, text):
        ids = self._tok.encode(text, add_special_tokens=False)
        return self._tok.convert_ids_to_tokens(ids)


def load_tokenizer(spec, trust_remote_code=False):
    if spec == "selftest":
        return WhitespaceTokenizer()
    return HFTokenizer(spec, trust_remote_code=trust_remote_code)


# ----------------------------------------------------------------------- corpora

def read_corpus(path):
    lines = [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        sys.exit("empty corpus: {}".format(path))
    return lines


def parse_corpus_args(pairs):
    """--corpus name=path, repeatable. Order is preserved so the CSV comes out in
    the order the slices were named, which is the order the report table wants."""
    slices_ = OrderedDict()
    for pair in pairs:
        if "=" not in pair:
            sys.exit("--corpus expects name=path, got: {}".format(pair))
        name, path = pair.split("=", 1)
        name, path = name.strip(), path.strip()
        if not name or not path:
            sys.exit("--corpus expects name=path, got: {}".format(pair))
        if name in slices_:
            sys.exit("slice named twice: {}".format(name))
        slices_[name] = path
    return slices_


def load_variant_groups(path):
    """Spelling-variant lexicon: one group per line, tab-separated surface forms,
    first field is the group label. Lines starting with # are comments.

    Shared with Shibin's normalized chrF++ work (298-23) on purpose -- the same
    lexicon has to drive normalisation and burden measurement or the two numbers
    stop being about the same thing."""
    groups = OrderedDict()
    if not Path(path).exists():
        return groups
    owner = {}
    for lineno, raw in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f.strip() for f in line.split("\t") if f.strip()]
        if len(fields) < 3:
            # a label plus at least two surface forms, otherwise there is no
            # variation to measure
            continue
        label, variants = fields[0], fields[1:]
        if label in groups:
            sys.exit("{}:{}: group {!r} defined twice".format(path, lineno, label))

        # Duplicates would be counted twice in the mean and quietly move the
        # headline metric, so they are a hard error rather than a warning. The
        # same surface form in two groups is the subtler version of the same bug
        # (`kam` is both कम and काम) and is rejected for the same reason: the
        # burden has to be one number per underlying word.
        seen = set()
        for variant in variants:
            if variant in seen:
                sys.exit("{}:{}: {!r} repeated inside group {!r}".format(
                    path, lineno, variant, label))
            if variant in owner:
                sys.exit("{}:{}: {!r} appears in both {!r} and {!r}".format(
                    path, lineno, variant, owner[variant], label))
            seen.add(variant)
            owner[variant] = label
        groups[label] = variants
    return groups


# --------------------------------------------------------------------- fertility

def word_token_count(tok, word, cache):
    """Tokens a single word costs. Subword vocabularies encode a word differently
    depending on whether it follows a space, so we measure it the way it actually
    appears mid-sentence and take the cheaper of the two readings."""
    if word in cache:
        return cache[word]
    bare = len(tok.encode_tokens(word))
    spaced = len(tok.encode_tokens(" " + word))
    n = min(bare, spaced) if spaced else bare
    cache[word] = n
    return n


def fertility_stats(tok, lines, variant_groups):
    """All fertility metrics for one tokenizer against one slice.

    Two token counts are reported on purpose. `fertility` encodes whole lines,
    which is what the model actually pays for. `fertility_wordlevel` encodes words
    in isolation, and is the count the split-rate metrics are consistent with.
    Reporting only one of them invites the reader to compare numbers that were
    computed differently.
    """
    n_line_tokens = 0
    n_byte_fallback = 0
    for line in lines:
        pieces = tok.encode_tokens(line)
        n_line_tokens += len(pieces)
        n_byte_fallback += sum(1 for p in pieces if BYTE_FALLBACK_RE.match(p))

    words = [w for line in lines for w in line.split()]
    n_words = len(words)
    if n_words == 0:
        sys.exit("slice contains no whitespace words")

    cache = {}
    counts = [word_token_count(tok, w, cache) for w in words]
    n_word_tokens = sum(counts)

    n_bytes = sum(len(line.encode("utf-8")) for line in lines)
    types = sorted(set(words))
    type_counts = [word_token_count(tok, w, cache) for w in types]

    row = OrderedDict()
    row["n_lines"] = len(lines)
    row["n_words"] = n_words
    row["n_word_types"] = len(types)
    row["n_tokens"] = n_line_tokens
    row["fertility"] = n_line_tokens / n_words
    row["fertility_wordlevel"] = n_word_tokens / n_words
    row["bytes_per_token"] = (n_bytes / n_line_tokens) if n_line_tokens else 0.0
    row["continuation_rate"] = sum(1 for c in counts if c >= 2) / n_words
    row["severe_split_rate"] = sum(1 for c in counts if c >= 4) / n_words
    row["byte_fallback_rate"] = (
        (n_byte_fallback / n_line_tokens) if n_line_tokens else 0.0
    )
    row["vocab_coverage"] = sum(1 for c in type_counts if c == 1) / len(types)

    burden, single_rate, _ = variant_burden(tok, variant_groups, cache)
    row["spelling_variant_burden"] = burden
    row["variant_single_token_rate"] = single_rate
    return row


def variant_burden(tok, variant_groups, cache=None):
    """The project's novel metric: mean tokens paid per surface form across known
    spelling variants of the same underlying word.

    Deliberately measured over the whole lexicon rather than only the variants that
    happen to appear in a given slice. It is a property of the tokenizer, so it has
    to stay comparable across slices and across candidate backbones. Above 1.0 means
    the vocabulary is paying for spelling noise; the gap between the cheapest and
    dearest variant in a group is where that cost is concentrated.
    """
    cache = {} if cache is None else cache
    if not variant_groups:
        return float("nan"), float("nan"), []

    per_group = []
    all_counts = []
    for label, variants in variant_groups.items():
        counts = [word_token_count(tok, v, cache) for v in variants]
        all_counts.extend(counts)
        per_group.append(
            OrderedDict(
                [
                    ("group", label),
                    ("n_variants", len(variants)),
                    ("mean_tokens", sum(counts) / len(counts)),
                    ("min_tokens", min(counts)),
                    ("max_tokens", max(counts)),
                    ("spread", max(counts) - min(counts)),
                    ("single_token_variants", sum(1 for c in counts if c == 1)),
                    (
                        "detail",
                        " ".join(
                            "{}:{}".format(v, c) for v, c in zip(variants, counts)
                        ),
                    ),
                ]
            )
        )

    burden = statistics.mean(g["mean_tokens"] for g in per_group)
    single_rate = sum(1 for c in all_counts if c == 1) / len(all_counts)
    return burden, single_rate, per_group


FERTILITY_FIELDS = [
    "tokenizer",
    "slice",
    "n_lines",
    "n_words",
    "n_word_types",
    "n_tokens",
    "fertility",
    "fertility_wordlevel",
    "bytes_per_token",
    "continuation_rate",
    "severe_split_rate",
    "byte_fallback_rate",
    "vocab_coverage",
    "spelling_variant_burden",
    "variant_single_token_rate",
]


def fmt(value):
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return "{:.4f}".format(value)
    return value


def write_csv(path, fieldnames, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: fmt(row.get(k, "")) for k in fieldnames})
    return path


def print_fertility_table(rows):
    cols = [
        ("slice", 18, "{}"),
        ("fertility", 11, "{:.3f}"),
        ("bytes_per_token", 16, "{:.2f}"),
        ("continuation_rate", 18, "{:.3f}"),
        ("severe_split_rate", 18, "{:.3f}"),
        ("vocab_coverage", 15, "{:.3f}"),
    ]
    by_tok = OrderedDict()
    for row in rows:
        by_tok.setdefault(row["tokenizer"], []).append(row)
    for name, group in by_tok.items():
        print("\n{}".format(name))
        print("  burden (spelling_variant_burden): {:.3f}".format(
            group[0]["spelling_variant_burden"]
        ) if not math.isnan(group[0]["spelling_variant_burden"]) else
            "  burden: no variant lexicon found")
        header = "".join(h.rjust(w) if i else h.ljust(w)
                         for i, (h, w, _) in enumerate(cols))
        print("  " + header)
        print("  " + "-" * len(header))
        for row in group:
            line = ""
            for i, (key, width, spec) in enumerate(cols):
                cell = spec.format(row[key])
                line += cell.rjust(width) if i else cell.ljust(width)
            print("  " + line)


# ----------------------------------------------------------------- code-mixing

def parse_conll_text(text):
    """Language-tagged corpus: one `token<TAB>lang` per line, blank line between
    utterances. Deliberately lenient about the number of columns -- taggers emit
    different numbers of them, and we only need the surface form and the last tag."""
    sentences, current = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if current:
                sentences.append(current)
                current = []
            continue
        if line.startswith("#"):
            continue
        fields = line.split("\t") if "\t" in line else line.split()
        tag = fields[-1].lower() if len(fields) > 1 else ""
        current.append((fields[0], tag))
    if current:
        sentences.append(current)
    return sentences


def read_conll(path):
    sentences = parse_conll_text(Path(path).read_text(encoding="utf-8"))
    if not sentences:
        sys.exit("no utterances parsed from {}".format(path))
    return sentences


def cmi(tags):
    """Code-Mixing Index, Das and Gamback. 100 * (1 - max language share) over the
    language-dependent tokens only. 0 means monolingual, 50 is an even two-way mix."""
    langs = [t for t in tags if t not in NEUTRAL_TAGS]
    if not langs:
        return 0.0
    counts = Counter(langs)
    return 100.0 * (1.0 - max(counts.values()) / len(langs))


def switch_points(tags):
    """Positions where the language changes, counted over the language-dependent
    tokens so that a comma between two Hindi words is not read as a switch."""
    langs = [t for t in tags if t not in NEUTRAL_TAGS]
    return sum(1 for a, b in zip(langs, langs[1:]) if a != b), len(langs)


def m_index(tags):
    """Multilingual Index, Barnett et al. 0 when monolingual, 1 when the languages
    are perfectly balanced. Complements CMI because it is defined over k languages
    rather than against the single dominant one."""
    langs = [t for t in tags if t not in NEUTRAL_TAGS]
    if not langs:
        return 0.0
    counts = Counter(langs)
    k = len(counts)
    if k < 2:
        return 0.0
    total = len(langs)
    sum_p2 = sum((c / total) ** 2 for c in counts.values())
    return (1.0 - sum_p2) / ((k - 1) * sum_p2)


def burstiness(spans):
    """Goh and Barabasi burstiness over monolingual run lengths. +1 is bursty
    (long unbroken stretches of one language), 0 is Poisson-like, -1 is regular
    alternation. This is what separates a corpus that switches in clauses from one
    that switches word by word, which matters for how synthetic data should look."""
    if len(spans) < 2:
        return float("nan")
    mean = statistics.mean(spans)
    sd = statistics.pstdev(spans)
    if (sd + mean) == 0:
        return float("nan")
    return (sd - mean) / (sd + mean)


def monolingual_spans(tags):
    langs = [t for t in tags if t not in NEUTRAL_TAGS]
    spans, run = [], 0
    prev = None
    for tag in langs:
        if tag == prev:
            run += 1
        else:
            if run:
                spans.append(run)
            run = 1
            prev = tag
    if run:
        spans.append(run)
    return spans


def code_mixing_stats(sentences):
    per_sentence_cmi = []
    total_switches = 0
    total_lang_tokens = 0
    all_tags = []
    all_spans = []
    mixed = 0

    for sent in sentences:
        tags = [tag for _, tag in sent]
        all_tags.extend(tags)
        value = cmi(tags)
        per_sentence_cmi.append(value)
        if value > 0:
            mixed += 1
        sw, n = switch_points(tags)
        total_switches += sw
        total_lang_tokens += n
        all_spans.extend(monolingual_spans(tags))

    lang_counts = Counter(t for t in all_tags if t not in NEUTRAL_TAGS)
    stats = OrderedDict()
    stats["n_utterances"] = len(sentences)
    stats["n_tokens"] = len(all_tags)
    stats["n_language_tokens"] = total_lang_tokens
    stats["languages"] = dict(lang_counts)
    stats["cmi_mean_all"] = statistics.mean(per_sentence_cmi)
    mixed_only = [c for c in per_sentence_cmi if c > 0]
    stats["cmi_mean_mixed_only"] = statistics.mean(mixed_only) if mixed_only else 0.0
    stats["frac_utterances_mixed"] = mixed / len(sentences)
    # SPF is defined over adjacent pairs, so the denominator is tokens minus one
    # per utterance, not tokens.
    denom = max(total_lang_tokens - len(sentences), 1)
    stats["switch_point_fraction"] = total_switches / denom
    stats["n_switch_points"] = total_switches
    stats["m_index"] = m_index(all_tags)
    stats["burstiness"] = burstiness(all_spans)
    stats["mean_span_length"] = statistics.mean(all_spans) if all_spans else 0.0
    return stats


def print_code_mixing(stats):
    print("\ncode-mixing statistics  [298-22]")
    print("-" * 58)
    for key, value in stats.items():
        if isinstance(value, float):
            shown = "nan" if math.isnan(value) else "{:.4f}".format(value)
        else:
            shown = json.dumps(value) if isinstance(value, dict) else str(value)
        print("  {:<26} {}".format(key, shown))
    print("-" * 58)
    print(
        "Report switch_point_fraction = {:.4f} to the team. The GCM sampling in\n"
        "298-17 matches this distribution; sampling randomly instead produces\n"
        "synthetic data with an unnatural switching profile.".format(
            stats["switch_point_fraction"]
        )
    )


# ------------------------------------------------------------------- self-test

SELFTEST_SLICE = [
    "i will call you tomorrow morning",
    "the meeting was moved to friday",
]

SELFTEST_CONLL = """\
main\thi
kal\thi
office\ten
jaunga\thi
.\tuniv

this\ten
is\ten
totally\ten
theek\thi
hai\thi
"""


def selftest():
    """Checks the metric maths against numbers that can be worked out by hand, so a
    broken refactor fails here rather than silently in a reported table."""
    tok = WhitespaceTokenizer()
    groups = load_variant_groups(DEFAULT_VARIANTS)
    row = fertility_stats(tok, SELFTEST_SLICE, groups)

    failures = []

    def check(label, got, want, tol=1e-9):
        if abs(got - want) > tol:
            failures.append("{}: got {!r}, want {!r}".format(label, got, want))

    # 6 + 6 words, and the whitespace tokenizer never splits a word, so fertility
    # is exactly 1.0 and nothing is a continuation.
    check("n_words", row["n_words"], 12)
    check("fertility", row["fertility"], 1.0)
    check("fertility_wordlevel", row["fertility_wordlevel"], 1.0)
    check("continuation_rate", row["continuation_rate"], 0.0)
    check("severe_split_rate", row["severe_split_rate"], 0.0)
    check("byte_fallback_rate", row["byte_fallback_rate"], 0.0)
    check("vocab_coverage", row["vocab_coverage"], 1.0)

    sents = parse_conll_text(SELFTEST_CONLL)
    stats = code_mixing_stats(sents)
    check("n_utterances", stats["n_utterances"], 2)
    # utterance 1: hi hi en hi -> max share 3/4 -> 25.0 ; utterance 2: en en en hi hi
    # -> max share 3/5 -> 40.0
    check("cmi_mean_all", stats["cmi_mean_all"], (25.0 + 40.0) / 2)
    # switches: hi->hi->en->hi gives 2, en->en->en->hi->hi gives 1
    check("n_switch_points", stats["n_switch_points"], 3)
    check("m_index_is_positive", 1.0 if stats["m_index"] > 0 else 0.0, 1.0)

    if groups:
        burden, single_rate, per_group = variant_burden(tok, groups)
        # the whitespace tokenizer charges one token per surface form, so the
        # burden floor is exactly 1.0 -- any real tokenizer above that is paying
        # for spelling noise, which is the whole point of the metric
        check("variant_burden_floor", burden, 1.0)
        check("variant_single_token_rate", single_rate, 1.0)
        print("[selftest] variant lexicon: {} groups, {} surface forms".format(
            len(per_group), sum(g["n_variants"] for g in per_group)
        ))
    else:
        print("[selftest] warning: {} not found, burden untested".format(
            DEFAULT_VARIANTS
        ))

    if failures:
        for f in failures:
            print("[selftest] FAIL {}".format(f))
        sys.exit(1)
    print("[selftest] ok")


# ------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--corpus",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="text slice, one sentence per line; repeat for each slice",
    )
    ap.add_argument(
        "--tokenizer",
        action="append",
        default=[],
        metavar="MODEL_ID",
        help="HuggingFace tokenizer id; repeat for each candidate backbone",
    )
    ap.add_argument("--variants", default=str(DEFAULT_VARIANTS),
                    help="spelling-variant lexicon (default: analysis/spelling_variants.tsv)")
    ap.add_argument("--out", help="fertility CSV; the per-group variant CSV sits beside it")
    ap.add_argument("--conll", help="language-tagged corpus for the code-mixing stats")
    ap.add_argument("--cmi-only", action="store_true",
                    help="code-mixing statistics only, no tokenizers needed (298-22)")
    ap.add_argument("--trust-remote-code", action="store_true",
                    help="pass through to AutoTokenizer for backbones that need it")
    ap.add_argument("--seed", type=int, default=42,
                    help="recorded for provenance; nothing here samples, but the "
                         "team rule is that every script takes --seed")
    ap.add_argument("--selftest", action="store_true",
                    help="verify the metric maths with no corpora and no network")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    # Seeding is a team-wide rule rather than a need of this script -- nothing in
    # here samples. Honoured when Prakhar's 298-26 scaffolding is present, skipped
    # quietly when it is not, so fertility work is not blocked on it.
    sys.path.insert(0, str(REPO_ROOT / "common"))
    try:
        from repro import set_seed
        set_seed(args.seed)
    except ImportError:
        pass

    if args.cmi_only:
        if not args.conll:
            ap.error("--cmi-only needs --conll")
        stats = code_mixing_stats(read_conll(args.conll))
        print_code_mixing(stats)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
            print("\nwrote {}".format(out))
        return

    if not args.corpus:
        ap.error("need at least one --corpus NAME=PATH (or --cmi-only, or --selftest)")
    if not args.tokenizer:
        ap.error("need at least one --tokenizer MODEL_ID")

    slices_ = parse_corpus_args(args.corpus)
    corpora = OrderedDict((name, read_corpus(path)) for name, path in slices_.items())
    variant_groups = load_variant_groups(args.variants)
    if not variant_groups:
        print("warning: no variant lexicon at {} -- spelling_variant_burden, the "
              "metric this analysis exists for, will be blank".format(args.variants),
              file=sys.stderr)

    rows, variant_rows = [], []
    for spec in args.tokenizer:
        print("loading tokenizer {} ...".format(spec))
        tok = load_tokenizer(spec, trust_remote_code=args.trust_remote_code)
        for name, lines in corpora.items():
            row = fertility_stats(tok, lines, variant_groups)
            row["tokenizer"] = tok.name
            row["slice"] = name
            rows.append(row)
        _, _, per_group = variant_burden(tok, variant_groups)
        for group in per_group:
            enriched = OrderedDict([("tokenizer", tok.name)])
            enriched.update(group)
            variant_rows.append(enriched)

    print_fertility_table(rows)

    if args.conll:
        print_code_mixing(code_mixing_stats(read_conll(args.conll)))

    if args.out:
        path = write_csv(args.out, FERTILITY_FIELDS, rows)
        print("\nwrote {}".format(path))
        if variant_rows:
            vpath = Path(args.out).with_suffix("")
            vpath = vpath.parent / (vpath.name + ".variants.csv")
            write_csv(vpath, list(variant_rows[0].keys()), variant_rows)
            print("wrote {}".format(vpath))


if __name__ == "__main__":
    main()
