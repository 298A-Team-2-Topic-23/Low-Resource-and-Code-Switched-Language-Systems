# Requirement AI-6 — tokenizer fertility across four text slices

**Status: MET.** 4 of 4 slices measured, on the real HinGE corpus, 10 November 2026.

Supersedes the 9 November verdict in this file, which read *"not met, 3 of 4"*. What
changed is not the code — `scripts/make_slices.py` already had the Devanagari path — but
the data. HinGE turned out to be published by the authors' own lab at
[`LingoIITGN/HinGE`](https://huggingface.co/datasets/LingoIITGN/HinGE) under **CC-BY-4.0**,
and `docs/datasheet.md` had recorded its licence as *"Unstated … non-commercial (inferred)
… unresolved"*. The corpus was obtainable the whole time.

## Reproducing this table

```bash
python3 scripts/fetch_data.py --only hinge
python3 scripts/make_slices.py --from-hinge data/raw/hinge/HinGE.csv
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 analysis/tokenizer_fertility.py \
  --tokenizer Qwen/Qwen2.5-7B-Instruct \
  --corpus en=data/slices/en.txt --corpus hi_deva=data/slices/hi_deva.txt \
  --corpus hi_roman=data/slices/hi_roman.txt --corpus hinglish=data/slices/hinglish.txt \
  --out reports/fertility.csv
```

The fetch is pinned to revision `e25a1038`, so the input cannot drift under the numbers.

## The measurement

Tokenizer: `Qwen/Qwen2.5-7B-Instruct`. `spelling_variant_burden` 1.832 against a floor of 1.0.

| Slice | Source | Lines | Words | Fertility | Bytes/token | Continuation | Severe split | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `en` | HinGE English | 1,976 | 33,837 | **1.247** | 4.50 | 0.166 | 0.013 | 0.541 |
| `hi_deva` | HinGE Hindi (Devanagari) | 1,976 | 36,906 | **4.636** | 2.78 | 0.982 | 0.554 | **0.012** |
| `hi_roman` | team parallel fixture | 30 | 165 | **1.909** | 2.77 | 0.715 | 0.012 | 0.219 |
| `hinglish` | HinGE human references | 4,799 | 81,114 | **1.636** | 3.47 | 0.385 | 0.046 | 0.310 |

## Finding 1 — script choice costs more than code-mixing does

The ordering is `hi_deva 4.64 > hi_roman 1.91 > hinglish 1.64 > en 1.25`.

Devanagari Hindi costs **3.7× more tokens per word than English**, and its vocabulary
coverage is **1.2%** — the tokenizer has essentially no Devanagari vocabulary. 55.4% of
its words are severely split and 98.2% of its tokens are word-continuation pieces, which
together say the text is being reassembled almost byte by byte.

Romanising the same Hindi content drops fertility to 1.91 (a **2.4× saving**) and raises
coverage to 21.9% (**18×**). Hinglish then costs *less* than Romanised Hindi, because it
carries English words the tokenizer already knows.

**This is the first measured justification for a design decision the project had only
asserted.** Workbook 1 targets Romanised Hinglish rather than Devanagari output. Until now
that was argued from how people write; it is now also a quantified efficiency claim, and
the question could not even be asked without the fourth slice.

## Finding 2 — the synthetic corpus was easier than reality

Measured on the seeded generator, Hinglish coverage was 0.548. On real human Hinglish it
is **0.310**. Fertility barely moved (1.653 → 1.636), so the generator was producing text
of realistic token *length* built from a far more tokenizer-friendly *vocabulary* than
people actually use.

Any model scored on synthetic Hinglish would have been flattered by roughly 24 coverage
points. The superseded table is kept at `reports/fertility_synthetic_slice.csv` so the
comparison stays auditable.

This also retires the 7 October coverage claim for good. Workbook 1 reported 98.5% English
coverage against 52.6% Hinglish; the cause was a slice with only 67 distinct word types
across 9,866 words, so it measured repetitiveness. On real text the English figure is
**0.541**. The honest headline gap is not English-versus-Hinglish at all — it is
**Devanagari-versus-everything**, and it is much larger than the number originally claimed.

## What this does not establish

- **`hi_roman` is still a 30-line team-authored fixture**, not a corpus. It is the one
  slice with no real source: HinGE has no Romanised-Hindi column, and producing one means
  transliterating Devanagari, which needs Dakshina (2.0 GB, CC-BY-SA-4.0, in
  `docs/datasheet.md`). Its fertility of 1.909 is therefore indicative, not a corpus
  measurement, and 30 lines cannot support a confidence interval. **This is the remaining
  honest weakness in AI-6** and it is tracked for 298-76.
- **One tokenizer.** Every figure is Qwen2.5's. A different tokenizer would give different
  numbers, and the Devanagari result in particular is a fact about this tokenizer's
  vocabulary, not about Devanagari.
- **Fertility is not quality.** A low token count does not mean better generation. These
  numbers justify the vocabulary-extension rung (M3) and the Romanised target; they do not
  predict chrF++.
- **Multiple references inflate `hinglish` line count.** 4,799 lines come from 1,976 source
  sentences, mean 2.41 renderings each. Treating each as a line is deliberate — each is a
  real observation of human spelling choice, which is what `spelling_variant_burden`
  measures — but the slice is not 4,799 independent sentences.

## Provenance

| Item | Value |
|---|---|
| Corpus | HinGE, `LingoIITGN/HinGE`, revision `e25a1038`, CC-BY-4.0 |
| Corpus SHA-256 | `dcfaf37ca9d7528e27da7be6b0cfffafb8bbe7825fe4da45077b96236cd9c9c3` |
| Rows / human references | 1,976 / 4,799 |
| Slice hashes | `data/slices/manifest.json` |
| Measured table | `reports/fertility.csv` |
| Superseded (synthetic) | `reports/fertility_synthetic_slice.csv` |
| Superseded (7 Oct, 1,091-line slice) | `reports/fertility_1091_slice.csv` |
| Citation | Srivastava, V. and Singh, M. (2021). HinGE. Eval4NLP 2021, 200–208. |
