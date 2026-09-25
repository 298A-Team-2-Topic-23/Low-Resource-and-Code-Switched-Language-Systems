# Tokenizer fertility and code-mixing analysis

Linear **298-13** (fertility, four slices) and **298-22** (code-mixing statistics).
Owner: Sarvesh.

This is the CPU-only test of the project's central hypothesis, so it is not blocked
on the GPU allocation (298-10) or on the frozen splits (298-11).

## Why this exists

Quality loss on Hinglish is usually blamed on missing data, and tokenizer
inefficiency is usually blamed on non-Latin script. Hinglish is already written in
Roman script. If fertility is still high, neither explanation covers it — our claim
is **orthographic variance**: `nahi`, `nhi`, `nahii` and `nahin` are one word that
the tokenizer sees as four unrelated vocabulary entries.

`spelling_variant_burden` measures that directly and is the project's novel metric.
Everything else in the table is context for it.

The output of this analysis determines the vocabulary size for M3, so it has to land
before M3 is designed.

## Running it

Self-test first. No corpora, no network, no `transformers`:

```bash
python analysis/tokenizer_fertility.py --selftest
```

Fertility across the four slices, for every candidate backbone:

```bash
python analysis/tokenizer_fertility.py \
    --corpus en=data/slices/en.txt \
    --corpus hi_deva=data/slices/hi_deva.txt \
    --corpus hi_roman=data/slices/hi_roman.txt \
    --corpus hinglish=data/slices/hinglish.txt \
    --tokenizer Qwen/Qwen3-8B \
    --tokenizer google/gemma-3-12b-it \
    --out results/fertility.csv
```

Writes two files. `results/fertility.csv` is one row per tokenizer × slice.
`results/fertility.variants.csv` is one row per tokenizer × variant group, so the
burden number is auditable group by group instead of arriving as a single mean that
nobody can check.

Code-mixing statistics (298-22), on a language-tagged corpus:

```bash
python analysis/tokenizer_fertility.py --cmi-only --conll data/hinge_tagged.conll
```

Emits CMI, Switch-Point Fraction, M-index, burstiness and mean monolingual span
length. Add `--out results/cmi.json` to record it.

**The SPF number from this mode is what the GCM synthetic sampling in 298-17 has to
match.** Sampling GCM output randomly instead of SPF-matched produces synthetic data
with an unnatural switching distribution, which is worse than no synthetic data.

## The metrics

| Column | Definition |
|---|---|
| `fertility` | subword tokens ÷ whitespace words, counted over whole lines |
| `fertility_wordlevel` | same ratio with words encoded in isolation |
| `bytes_per_token` | UTF-8 bytes ÷ subword tokens |
| `continuation_rate` | fraction of words split into ≥ 2 pieces |
| `severe_split_rate` | fraction of words split into ≥ 4 pieces |
| `byte_fallback_rate` | fraction of tokens that are raw-byte fallbacks |
| `vocab_coverage` | fraction of word **types** present as a single token |
| `spelling_variant_burden` | mean tokens paid per surface form across known variant groups |
| `variant_single_token_rate` | fraction of all variant forms that cost exactly one token |

Two token counts are reported deliberately. `fertility` encodes whole lines, which
is what the model actually pays for. `fertility_wordlevel` encodes words in
isolation and is the count the split-rate columns are consistent with. Reporting
only one of them would invite comparing numbers computed two different ways.

`spelling_variant_burden` is measured over the whole lexicon rather than only the
variants that appear in a given slice, because it is a property of the *tokenizer*
and has to stay comparable across slices and across candidate backbones. It is
therefore constant down the slice column for a given tokenizer — that is expected,
not a bug.

### Expected fertility ranges

| Slice | Expected |
|---|---|
| English | 1.2 – 1.4 |
| Devanagari Hindi | 2.5 – 4.0 |
| Romanized Hindi | 1.8 – 2.5 |
| Romanized Hinglish | similar to Romanized Hindi, possibly higher |

If the numbers are far outside these, suspect the slices before suspecting the
tokenizer.

## Preliminary numbers — not a result

Run on a 5-sentence-per-slice smoke fixture against `Qwen/Qwen2.5-7B-Instruct`,
purely to prove the script is correct. **These are not reportable**: the sample is
far too small, and the real slices do not exist until 298-11 freezes the splits.

| slice | fertility | bytes/token | continuation | severe split | vocab coverage |
|---|---|---|---|---|---|
| en | 1.00 | 4.78 | 0.00 | 0.00 | 1.00 |
| hi_deva | 4.27 | 2.73 | 1.00 | 0.46 | 0.00 |
| hi_roman | 1.89 | 2.69 | 0.65 | 0.04 | 0.36 |
| hinglish | 1.74 | 2.89 | 0.59 | 0.00 | 0.41 |

`spelling_variant_burden` = **1.83**.

Two things worth flagging early, both of which survive if they hold on the real
slices:

1. **Hinglish fertility came out *below* Romanized Hindi**, not above. Romanization
   is known to cut fertility two to four times on its own, so there may be little
   headroom left for a vocabulary extension to recover. Per the task breakdown this
   gets reported as a finding rather than treated as a failure — and it is evidence
   *for* our framing, since it says the remaining cost is not script.
2. **Burden is 1.83, well above the 1.0 floor**, so the vocabulary is paying for
   spelling noise. The cost is not evenly spread. Short forms are cheap because they
   collide with existing English tokens (`log`, `kam`, `din`, `kal` all cost one
   token); longer Hindi-specific content words are where it concentrates
   (`shukriya` 3.33, `chahiye` 2.75, `kitna` 2.67 mean tokens per form). Five groups
   have a canonical form costing one token and a variant costing three or more —
   that gap is the hypothesis in miniature.

## Open items

- **The tokenizer identifiers in the commands above are unverified.** `Qwen/Qwen3-8B`
  and `google/gemma-3-12b-it` are carried over from the task breakdown. An earlier
  draft named a configuration that does not exist, so per `CLAUDE.md` every
  identifier is checked against the official model card before it appears in a
  submitted document. The only one confirmed to resolve so far is
  `Qwen/Qwen2.5-7B-Instruct`, used for the smoke run above. This has to be settled
  before the backbone decision is written down.
- Real slices depend on 298-11. Until then only `--selftest` and smoke fixtures run.
- `data/hinge_tagged.conll` does not exist yet. Language tagging of HinGE is an
  upstream dependency of 298-22; the `--cmi-only` path is verified against a
  hand-checked fixture in the meantime.
- The variant lexicon is a hand-seeded v1 (72 groups, 227 surface forms). It is
  scheduled to be extended and frequency-ranked from the frozen train split rather
  than from intuition. Extensions are versioned changes to the file, never in-place
  edits, so an already-reported burden number stays reproducible.

## The variant lexicon

`analysis/spelling_variants.tsv`. One group per line, tab-separated: group label
then attested surface forms. Curation rules and versioning policy are in the file
header.

It is also the intended input to **Shibin's normalized chrF++ (298-23)**. The same
lexicon has to drive normalisation and burden measurement, otherwise the two numbers
stop being about the same thing — and their divergence is what we report as evidence
of orthographic instability, so it has to be interpretable.

The loader rejects duplicate forms inside a group and the same form in two groups.
Both would quietly double-count into the headline mean. The cross-group case is the
subtler one: `kam` is both कम and काम, and letting it sit in two groups would make
the burden stop being one number per underlying word.
