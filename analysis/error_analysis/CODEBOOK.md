# Error analysis codebook: pre-registration

Linear **298-84**. Written by Savalia, Jenil Sanjaybhai, on **9 November 2026**.

This codebook was committed before any Model 2, 3 or 4 output on the real corpus existed. On that
date `results/results.jsonl` held only the 22 October smoke runs, on synthetic data with a 0.5B
stand-in model. The commit date is the evidence that the categories were not chosen after seeing
the outputs. Any later change goes in the changelog at the end, with its date and reason. The
earlier text stays as committed.

## The question

A chrF++ difference says that a model improved. It does not say on what. The project claims
that Model 3's vocabulary extension acts on **spelling variance**. If that is the mechanism, M3's
advantage over M2 should be concentrated in spelling errors. If M3 instead improves every category
by about the same amount, the gain is real but the claimed mechanism is not shown, and the report
says so.

## Sample

| Decision | Value | Why |
|---|---|---|
| Surface | HinGE test split, frozen (`hinge_split_manifest.json`, `6ac5d302…`) | The only real evaluation surface until the gold set exists |
| Unit | One **unique English source**, not one reference record | 468 test records cover 197 sources; sampling records would over-weight sources with more references |
| Size | **50 sources**, drawn uniformly at random with seed **84** | The brief's 150 outputs; no stratification, so agreeing and diverging cases appear at their natural rates |
| Systems | M2, M3 and M4, each at training seed **13** | One seed per system, fixed now, so a seed cannot be picked for its outputs |
| Pairing | The **same 50 sources** for all three systems | Differences between systems are paired, item by item |
| References shown | All human references for the source | So a valid output that differs from one reference is recognisable |

The report states how many of the 50 sources have identical outputs from all three systems.

## Blinding

`scripts/error_analysis_sheet.py sheet` writes four files:

| File | Who sees it | When |
|---|---|---|
| `coding_sheet.csv`: all 150 outputs, shuffled, no system names | Coder 1 | During coding |
| `coding_sheet_overlap.csv`: 30 of those rows, drawn at random with seed 84 | Coder 2 | During coding |
| `key.csv`: row to system and line | Nobody | Opened only by `summarise`, after both sheets are complete |
| `auto.csv`: automatic indicators per row | Nobody | Opened only by `summarise` |

Coders see the English source, the references and the output, and nothing else. They do not see
sentence scores, system names or the automatic indicators.

**Declared conflict of interest.** Savalia is the provisional owner of Model 3 and is coder 1. Blind
coding and the second coder are the mitigation. The report states this next to the results.

## Codes

Each output receives **one or more** codes, or `OK` alone. Each output is also marked acceptable,
`yes` or `no`: would it be accepted as a gold reference under annotation guidelines v1?

| Code | Assign when | Do not assign when |
|---|---|---|
| `SPELLING_VARIANT` | A word is right, but written in an attested non-canonical form, such as `nhi` for *nahi* | The form is canonical, or the word itself is wrong |
| `SPELLING_ERROR` | A word is recognisably right, but written in a form a Hinglish writer would not use, such as `nhaai` | The reader cannot tell which word was meant: that is `ADEQUACY` |
| `SWITCH_LOW` | Too little English: formal Hindi where a bilingual writer keeps the English word or phrase, as in technical terms and common nouns | The English source has no such items |
| `SWITCH_HIGH` | Too much English: essentially the English sentence with token Hindi, or a verbatim copy of the source | The English kept is what a bilingual writer would keep |
| `SWITCH_BOUNDARY` | A switch inside a constituent whose word order differs between the languages, as in `main going hoon` | The switch falls where both word orders agree |
| `SCRIPT` | **Any** Devanagari character in the output | Never a judgement call; the automatic indicator must agree |
| `ADEQUACY` | Meaning is omitted, added or wrong | Only the wording is awkward |
| `FLUENCY` | Ungrammatical or unnatural Hinglish not explained by any code above | The problem is already coded as spelling, switching or script |
| `OK` | Acceptable and none of the above apply | Any other code applies |

**Reference artifact** is computed, not coded, so no coder sees a score. An output is a reference
artifact when it is marked acceptable and its sentence chrF++ against all references is below that
system's median over the 50 sources. This counts how often the single-reference scoring that
section 3.6.3 warns about understates a valid output.

Rules that decide the hard cases:

1. Code every problem present. An output can be both `ADEQUACY` and `FLUENCY`.
2. `SCRIPT` is objective, and a disagreement with `auto.csv` is a coding error to correct, not a
   finding.
3. If a word is both misspelled and the wrong word, code `ADEQUACY` only.
4. Spelling is judged against the lexicon (`analysis/spelling_variants.tsv`). The canonical form is
   the group label. A form outside the lexicon is judged by whether a Hinglish writer would use it.

## Analysis, fixed now

**Primary: is M3's gain concentrated in spelling?** For each code, the rate per system is the share
of the 50 outputs carrying it. For each code, the paired difference is M2's rate minus M3's rate,
with a 95% interval from 1,000 bootstrap resamples of the 50 sources at seed 84. Spelling combines
`SPELLING_VARIANT` and `SPELLING_ERROR`.

| Observed | Reported as |
|---|---|
| Spelling difference above 0 with an interval excluding 0, **and** larger than the adequacy and fluency differences | Consistent with the claimed mechanism |
| Differences above 0 in several categories, with overlapping intervals | A general improvement; the mechanism is not shown |
| Spelling difference at or below 0 | Evidence against the claimed mechanism, reported as such |
| Every interval includes 0 | Inconclusive at this sample size. Not reported as "no effect" |

With 50 paired sources, rate differences much below 15 to 20 percentage points are unlikely to be
distinguishable. The report says this rather than letting an inconclusive interval read as a null.

**Secondary, all automatic (`auto.csv`):**

- **Canonical spelling rate:** the share of lexicon-matched output tokens written in their group's
  canonical form, per system. This answers whether M3 writes *more canonical* spellings or only
  different ones.
- **Script:** the share of outputs containing Devanagari, per system. The M1 0-shot smoke run
  leaked Devanagari into 13 of 48 outputs, and 5-shot into none (`docs/COMPUTE_BUDGET.md`).
- **Switching:** mean CMI and switch-point fraction of the outputs, against the corpus values of
  25.34 and 0.240 (`reports/data_statistics.json`), using the pipeline's own tagger.
- **M4:** the same per-code differences, M2 minus M4, read for switching rather than spelling,
  since M4 changes the distribution of code-switched text.

**Coding reliability:** coder 2's 30 rows are compared with coder 1's. Krippendorff's alpha, on a
nominal scale, is reported for the presence of each code and for acceptability, alongside raw
agreement and the code's prevalence. On a rare code, high agreement can still give a low alpha. A
code with alpha below 0.667 is reported with its results marked as unreliable, not dropped.

## Changelog

No changes since the version committed on 9 November 2026.
