# Shibin — Progress Report 2 brief

| Issue | What | Est | Due |
|---|---|---|---|
| [298-49](https://linear.app/298a-team-2-topic-23/issue/298-49) | **Part D: blockers, risks, next period** | 2 | **tonight** |
| [298-59](https://linear.app/298a-team-2-topic-23/issue/298-59) | Bootstrap + lexicon-driven normalised chrF++ | 5 | 2 Nov |
| [298-52](https://linear.app/298a-team-2-topic-23/issue/298-52) | **Reproduce the Gahoi baseline** | 8 | 7 Nov |

---

## 298-49 — Part D, tonight

Blockers with impact, a named owner and a dated next action. Then **three to five specific
outcomes** for the next period — and those outcomes must exist as Linear issues or they are
not outcomes.

The real blockers, all verifiable:

| Blocker | Impact | Owner | Next action |
|---|---|---|---|
| Team Meeting 2 needs 4 things on 12 Nov; **none exists** | the graded checkpoint fails | all | 298-51 → 298-56, three weeks |
| GPU allocation unconfirmed since 26 Sep | blocks baseline, M1 and M2 | Prakhar | written answer by 24 Oct (298-51) |
| No model trained | 4.5 cannot progress | Sarvesh | M1 by 3 Nov, M2 by 9 Nov |
| Baseline not reproduced; no public code | quality gate for every number | Shibin | 298-52 by 7 Nov |
| Gold set at 0 of 800 | success criterion has no surface | Jenil | 200 items by 5 Nov |
| No reviews, branch protection off | individual contribution evidence is weak | Prakhar | 298-60 by 26 Oct |
| **No commits 8–22 October** | a cycle lost against a fixed date | all | cycle 4 plan above |

Map the outcomes to **298-51, 298-52, 298-53, 298-54, 298-55**, by ID. State that three
weeks remain before 12 November and that it is the binding constraint.

Part D is where an honest report wins. The rubric asks for realistic issues with an adequate
plan — a thin Part D on a project with this many open items reads as not having looked.

## 298-52 — the baseline, the quality gate

This is the project's gate: **until the harness reproduces a published number, no model
result can be interpreted.** 298-15 and 298-16 are marked Done without artifacts and are
being reset.

Gahoi et al. released no code, so the mBART recipe is rebuilt from the description —
fine-tuned on English **and** Hindi input, with Devanagari-to-Roman transliteration as
post-processing. Target ROUGE-L within **0.01 of 0.617** on the 500-sentence MixMT Subtask-1
set; WER compared against 0.633.

Run both conditions: the original two-input for comparability with the paper, and
English-only as our own reference point.

**If the reproduction misses, that is a reportable finding.** Report it with evidence rather
than hiding it — and in that case no model result gets interpreted, which is a project-level
consequence worth flagging early rather than at the end.

## 298-59 — two gaps we found ourselves

**Bootstrap resampling.** Requirement AI-3 commits to 1000-sample bootstrap significance
testing and it is **not implemented** in `run_eval.py`. M1 versus M2 lands next cycle, and
no comparison can be called significant until this exists.

**Normalised chrF++.** 298-23 says Done, but the harness still normalises by regex. Measured
against `analysis/spelling_variants.tsv`, those rules fully collapse **3 of 72 groups**. The
rules handle vowel *lengthening*; the dominant Hinglish pattern is vowel *deletion* — `nhi`,
`kr`, `gya` — which they cannot catch. Two rules also actively corrupt: `hy` → `y` and
`hna` → `na`, because `y` sits in the consonant class of the `h(?=consonant)` rule.

This matters because the **raw-versus-normalised gap is what we present as evidence of
orthographic instability**. If normalisation is near-inert, that gap measures nothing.
`src/lrcs/lexicon.py` already loads the lexicon for the pipeline — point the harness at the
same source, drop the two corrupting rules, and report collapse coverage before quoting any
normalised figure.

Write a test that **fails against the regex version and passes against the new one**,
otherwise there is no proof the fix did anything.
