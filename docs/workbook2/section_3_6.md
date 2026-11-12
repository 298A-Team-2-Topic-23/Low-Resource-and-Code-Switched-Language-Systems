# 3.6 Data Statistics

Linear **298-65**. Written by Waghmare, Sarvesh.

Every corpus figure here is read from a committed artifact of the 8 October run on the real
HinGE corpus (`reports/data_statistics.json`, `reports/fertility.variants.csv`), and every plot
is regenerable from a clean clone. Nothing is typed in by hand.

## 3.6.1 What each stage produced

| Stage | Rows | Columns | Notes |
|---|---|---|---|
| Raw | 1,976 file rows → **4,799** records | 6 | one record per *reference*: `id, english, hindi, hinglish, row, ref` |
| Pre-processed | **4,674** | 7 | adds `tags`, the per-token language label; 125 removed by six filters |
| Transformed | **4,674** | 5 | the split TSV layout: `id, group, english, hindi, hinglish` |
| Prepared | **3,738 / 468 / 468** | 5 | train / validation / test, frozen under SHA-256 |

Column counts are the fields a record carries at that stage, which is the meaningful width once
stage 1 has expanded one source row into several records.

**The single most misread number here is the first one. 1,976 is sentences; 4,799 is
references.** HinGE gives multiple human renderings of the same English sentence, so the corpus
is about 2.4× larger in records than in distinct source material, and a reader who takes 4,799
as independent data overestimates it by that factor.

Attrition is 125 removed of 4,799, 2.6%, each removal charged to the first filter that rejected it
(§3.3). The pipeline runs in 7.48 s — ingest 0.14, clean 0.38, split 6.58, statistics 0.39. The
split stage dominates because it is the only quadratic-ish step: MinHash over 1,938 sources.

## 3.6.2 Distributions

Four figures are committed: `fig1_sentence_lengths.png`, `fig2_cmi_distribution.png`,
`fig3_switch_point_fraction.png`, `fig4_spelling_variants.png`.

**Length.** English averages 15.24 words (median 12, p95 37, range 3–60); Hinglish 15.87 (median
12, p95 39, range 2–60). The mean Hinglish-to-English ratio is **1.062** — code-switching is
close to length-neutral, which matters because `length_ratio` would otherwise remove signal.

**Vocabulary.** English contributes 6,780 types over 71,217 tokens; Hinglish **13,204 types over
74,165 tokens** — nearly double the vocabulary for the same quantity of text, at a type-token ratio of 0.178. That is the orthographic-variance problem in plain counts. The tokenizer
measurement now agrees on real text: fertility **1.636 on Hinglish against 1.247 on English**,
re-measured on the fetched corpus on 10 November (`reports/fertility_ai6.md`), superseding the
synthetic slices this section first quoted. The coverage contrast once quoted alongside them,
98.5% against 52.6%, did not survive re-measurement and is withdrawn (carry-forward).

**Code-mixing.** Mean CMI 25.34 across all sentences, 29.42 across mixed ones; 86.1% of
sentences are mixed. Switch-point fraction 0.240 overall over 10,861 switch points, mean monolingual span 3.22 tokens, M-index 0.693, burstiness 0.056 — switching is close to evenly
spaced rather than clustered. These rest on a tagger covering **68.2%** of tokens, a limitation
that belongs with the number every time it is quoted.

## 3.6.3 Imbalance

![References per source sentence](../../reports/figures/fig5_references_per_source.png)

The corpus's main imbalance is not class imbalance — the task has no classes — but **how
unevenly supervision is distributed across sources**. 1,938 sources carry 4,674 references, a mean of 2.41 each:

| References for one source | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Source sentences | 26 | 1,470 | 166 | 210 | 37 | 21 | 5 | 3 |

**76% of sources have exactly two references**, with a 14% tail at four or more. Three
consequences: a source with eight references appears eight times per epoch, so the tail is
up-weighted eightfold purely as an artifact of collection; because splits are assigned by whole
group, a heavily-referenced source lands entirely in one split, which is why the splits land at 79.97 / 10.01 / 10.01; and **multiple valid references are a property of the task, not noise** —
single-reference chrF++ systematically understates a model that produces a legitimate rendering
the reference did not happen to use, which is the argument for §4.4's multi-reference scoring.

A second imbalance sits in the lexicon: of 72 variant groups, 68 are observed and only **28
carry two or more spellings**, with 13% of their 3,812 occurrences spelled non-canonically. The
burden of 1.832 is therefore driven by a minority of groups — exactly the condition under which
vocabulary extension could buy less than expected, recorded in §4.3 as a way M3 loses.

## 3.6.4 Correlation

![Spelling-variant correlations](../../reports/figures/fig6_variant_correlations.png)

Two relationships the hypothesis predicts were tested, both named before being computed, and
both reported as measured.

**(a) Do words with more attested spellings cost more tokens per form?** Over all 72 groups:
Pearson **r = +0.29**, Spearman **ρ = +0.32**. The direction matches the hypothesis; the
strength is weak-to-moderate — real, but far from deterministic. Spearman exceeding Pearson
indicates a monotonic rather than linear relationship, which is what a subword tokenizer should
produce. This is the quantitative core of the project's claim, and it is honest to call it
*present and modest*: a group can have six spellings and still average 1.83 tokens if the
backbone carries most of them, and `nahi` is exactly that case.

**(b) Are commoner words spelled more inconsistently?** Over the 15 most frequent groups:
Pearson **r = −0.15**, Spearman **ρ = −0.10**. **This is a null result**, and it is informative:
frequency neither protects a word from spelling variance nor drives it. Variance looks like a
property of phonology and transliteration ambiguity — `hai` occurs 934 times and is
non-canonical 8.8% of the time, while rarer groups reach 77% and 91%. The caveat is n: panel (b)
rests on 15 groups, too few to exclude a weak effect, and the full-lexicon version should be
recomputed before it is relied on. Panel (a), at n = 72, is the whole lexicon.

## 3.6.5 Coverage gaps, and who they disadvantage

The data is not representative of the population a deployed system would meet. Five gaps, each
with the group it would fail.

**Language pair.** HinGE is Hindi–English only, and nothing transfers automatically to Tamil,
Bengali, Marathi, Telugu or Punjabi code-switching. *Disadvantaged: speakers of every Indian
language other than Hindi* — the majority of India's multilingual internet users.

**Tagger coverage.** The tagger resolves 68.2% of tokens; **19,382 of 83,922** are `unk`.
Unresolved tokens are disproportionately the rare and unusually-spelled ones, so **the
measurement is weakest exactly where the hypothesis is strongest**. *Disadvantaged: anyone whose
spelling is already atypical* — regional and younger informal writers — whose text is both least
well measured and least well modelled, and who would not appear in an error analysis built on
these tags.

**Register.** HinGE's English sources are formal and literary. Conversational Hinglish —
abbreviations, repeated characters, sentence-initial Roman Hindi — is essentially absent, though
it is where Hinglish overwhelmingly occurs. *Disadvantaged: ordinary users in chat and social
contexts*, the actual deployment setting.

**Monolingual inputs.** 86.1% of sentences are code-mixed, so monolingual Hindi and English are
under-represented. *Disadvantaged: users who switch in and out of code-mixing* — most
bilinguals — on their monolingual turns, the simplest case and the least tested.

**Demographics.** No speaker metadata is recorded: no region, age, gender or first language.
Representation therefore **cannot be checked at all**, only assumed. *Disadvantaged: any group
whose transliteration conventions differ from the annotators'* — Mumbai, Bihar and the South
romanise differently — with no way to detect the gap before deployment.

The last is the most serious, because it is the only one that cannot be fixed by adding data
later. The team-authored 800-item set (298-55) is where this is still in our control, and the
annotation guidelines should record annotator region and first language even though HinGE did
not.

**Provenance.** Stage rows, attrition, splits, timings, lengths, vocabulary, code-mixing and
spelling variance from `reports/data_statistics.json`; correlations from
`reports/workbook2_figures.json` via `scripts/workbook2_figures.py`; fertility from
`reports/fertility.csv` and `reports/fertility_ai6.md`.
