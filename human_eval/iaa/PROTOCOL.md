# Gold-set inter-annotator agreement: protocol

Linear **298-80**. Written by Savalia, Jenil Sanjaybhai, on **9 November 2026**, before any gold item
or annotation existed: `data/goldtestset/gold_set.csv` held 0 of 800 items that day. The commit date
is the evidence that the design and the decision rules were not fitted to the results. A later
change goes in the changelog at the end, with its date and reason.

## Why this exists

A hand-authored evaluation set with no agreement figure is one person's opinion. This protocol
measures three things on the first 200 gold items:

1. How often two annotators agree that a rendering is acceptable.
2. How far apart two competent humans are when they render the same sentence. This **human
   ceiling** is reported next to the model scores, since no model should be expected to beat it.
3. What kinds of disagreement occur. Recurring kinds go back into the annotation guidelines.

## Design

| Step | Decision | Why |
|---|---|---|
| Items | **100**, drawn at random with seed **80** from the first 200 rows of `gold_set.csv` in file order | Random rather than hand-picked, so easy items cannot be chosen |
| Annotators | Two, called **A** and **B**. Neither is the author of the sampled gold rows | Fresh renderings, not a re-statement of the gold column |
| Rendering | Each writes Romanized Hinglish for the 100 English sources, alone, under guidelines v1, without seeing the gold column, model output or the other annotator's work | Independence is what agreement measures |
| Judging | Each annotator then judges all **200** renderings, both their own and the other's, shuffled, with authorship hidden: **acceptable as a gold reference, yes or no** | Agreement on acceptability is the brief's measure |
| Metadata | Region, first language and other languages for A and B, with no names (`annotators.csv`) | Section 3.6.5 names this as the one coverage gap the team can still fix |

A third team member may judge the 200 renderings as well. If so, alpha is computed over all judges,
and the two-judge figure is still reported.

## Measures, fixed now

**Acceptability agreement.** Krippendorff's alpha on a nominal scale over the 200 judged renderings
(`human_eval/agreement.py`). It is reported with raw agreement and with the share of renderings
judged acceptable. When nearly every rendering is acceptable, alpha can be low even though raw
agreement is high, so all three figures are always reported together.

**Self-preference.** Each judge's acceptance rate for their own renderings and for the other
annotator's. Blind authorship reduces this bias but cannot rule out recognising one's own style.

**Human ceiling.** chrF++ between the two annotators' renderings, computed in both directions
(A as hypothesis against B, and B against A) and averaged, with a 95% interval from 1,000 bootstrap
resamples of the 100 items at seed 80. It is computed through `evaluation/run_eval.py`, the same
code that scores the models. The same figure is computed on lexicon-normalised text.

**What the normalised ceiling adds.** The gap between raw and normalised chrF++ between two
**humans** shows how much of human-to-human divergence is spelling alone. That is the baseline
against which the models' raw-to-normalised gap means anything.

**Disagreement categories.** Every item where the two renderings differ after case and punctuation
folding is classified once, by agreement between A and B after both have finished:

| Category | The two renderings differ in |
|---|---|
| `spelling` | Romanisation of the same words, such as `nahi` against `nhi` |
| `lexical` | Word choice, Hindi or English, with the same meaning |
| `switching` | How much is in English and where the switches fall |
| `error` | One rendering is wrong: a meaning error, an omission or a guideline violation |

`spelling` is suggested automatically when lexicon normalisation makes the two renderings identical.
The annotators confirm or change each suggestion.

## Decision rules, fixed now

The thresholds are those already set in `data/goldtestset/annotation_guidelines.md`:

| Alpha on acceptability | Action |
|---|---|
| 0.67 or above | Usable. The 800-item set continues under guidelines v2 |
| 0.40 to 0.67 | Revise the guideline sections behind the most frequent disagreement category, and re-judge a fresh 30-item sample |
| Below 0.40 | Retrain on shared examples before any further authoring |

A low alpha is reported as a finding about how hard the task is, with the action taken. It is not
re-run until a number looks better.

**Guidelines v2.** Every recurring disagreement case becomes a guideline change. Each change is
logged with the disagreement category and the item ids that drove it.

## Running it

```bash
# once the first 200 gold rows validate
python human_eval/gold_agreement.py sample --gold data/goldtestset/gold_set.csv
# after A and B have filled annotator_a.csv and annotator_b.csv
python human_eval/gold_agreement.py pool
# after both judges have filled judge_a.csv and judge_b.csv
python human_eval/gold_agreement.py score
```

Everything is written under `human_eval/iaa/`. `results.json` is the record to cite.
`pool_key.csv`, which maps each judged rendering to its author, is read only by `score`.

## Changelog

No changes since the version committed on 9 November 2026.
