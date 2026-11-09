# Phase 3 — Shevkar, Yash

**New: 12 points.** Cycle 5: 298-76, 298-77. Cycle 6: 298-86.
**Still outstanding:** 298-64 (section 3.5), 298-69 (section 4.3) — both Urgent, due 10 November —
and 298-58 (back-translation corpus).

You own the data layer end to end: ingest, cleaning, splits, the leakage gate, the warehouse. Phase
3 asks you to take the code-mix generator from a fixture to a real corpus, which is the last
unbuilt piece of the data pipeline, and then to prove the whole thing reproduces.

**Finish Workbook 2 first.** 298-64 and 298-69 are due the 10th and the workbook is due the 11th.
Nothing below outranks them.

---

## 298-77 — Reconcile the HinGE reference count
`https://linear.app/298a-team-2-topic-23/issue/298-77`
**1 point · due 12 November · not blocked**

The pipeline counts 4,799 human references from 1,976 source rows. The paper publishes 4,803.
`docs/datasheet.md` reports both and the carry-forward table lists it as still open.

Four references is 0.08% and changes no conclusion — but an unexplained gap between our count and
the published one is what a reader uses to decide whether to trust the rest of the numbers.

Candidates, cheapest first: whitespace-only reference strings that `ast.literal_eval` yields and
ingest drops; duplicate references inside one source row, if the paper counts positions and we
count distinct strings; malformed lists where the parser silently returns fewer items; or the
published figure counting something we exclude.

**Do this early in the cycle.** If the cause is a parser bug that drops data, every downstream
number in section 3.6 needs re-running, and you want to know that before the 11th, not after.

A documented dead end closes this issue. A silent one does not.

---

## 298-76 — Code-mix generator on a licensed parallel corpus, with transliteration
`https://linear.app/298a-team-2-topic-23/issue/298-76`
**8 points · due 20 November · blocks 298-82**

298-17 built the generator: IBM Model 1 alignment by EM, monotonic-block cutting, switch-point
matched sampling, 28 tests. It runs on a 30-sentence fixture. Model 4 needs a real corpus behind it.

**Two gaps, and the second is harder.**

*The corpus.* You licence-checked Samanantar and IIT Bombay under 298-20 and the outcome is in
`docs/datasheet.md`. Pull a slice, confirm the licence permits derived redistribution, record rows
and a SHA-256. Then run the near-duplicate check against the HinGE splits **before anything else** —
synthetic training data overlapping the test set is the most damaging leak available to this
project, and your gate in `src/lrcs/data/split.py` already exists to catch it.

*Transliteration.* `src/lrcs/data/codemix.py` refuses Devanagari deliberately: `read_parallel`
raises above 5% Devanagari because the target is Romanised Hinglish and mixed-script output would
be neither. Samanantar's Hindi side is Devanagari. So this needs Dakshina wired in as a Romanisation
step before alignment.

**Do not weaken the refusal to get around it.** The refusal is correct and
`test_devanagari_is_refused_with_a_reason` should keep passing. Romanisation is a step you add in
front of it, not a check you remove.

Acceptance: at least 20,000 sentences with mean SPF within 0.05 of HinGE's 0.2398; transliteration
as a named, tested step with a 100-item accuracy spot-check, because Romanisation is not
deterministic and its error rate belongs in the datasheet; zero overlap with the test split
demonstrated by the gate rather than asserted; `reports/codemix/README.md` updated to stop calling
the output a fixture.

**Share the contamination check with 298-58.** Back-translation and code-mixing both produce
synthetic training data and both need the same check. Build it once.

---

## 298-86 — 298A close-out: reproducibility audit and the 298B hand-off
`https://linear.app/298a-team-2-topic-23/issue/298-86`
**3 points · due 5 December**

Two halves. The audit is the reproducibility check this project has claimed and never performed end
to end.

On a fresh clone, on a machine that has never run this: install, then every documented command in
order, timed. Record what fails, what needs an uncommitted file, what needs a licence the clone
does not have. **Verify the frozen split manifest SHA-256 still matches what regenerating
produces** — if it does not, that outranks everything else in the cycle. Then test section 3.6's
claim that every number in it traces to a committed artifact.

The hand-off document says what is done with the artifact that proves it, and what is not done
while distinguishing *blocked* (the GPU) from *descoped* (an arm cut by 298-72) from *not
attempted*. Name what a new contributor must obtain themselves: `HinGE.pkl` is not committed,
Dakshina is not in the repository, the allocation may still be unresolved. Say who to ask.

An audit on a project this size that reports no problems will not be believed. Commit the failures.
And do it in the last week, not the last day — the point is finding problems while they can be
fixed.
