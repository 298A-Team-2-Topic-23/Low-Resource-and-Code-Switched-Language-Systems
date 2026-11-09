# Phase 3 — Waghmare, Sarvesh

**New: 18 points.** Cycle 5: 298-74, 298-75. Cycle 6: 298-82.
**Still outstanding:** 298-53 (M1), 298-54 (M2) — both In Progress, both blocked on 298-51.

You own the model ladder and the tokenizer argument, so Phase 3 puts the project's central claim
on your plate. Two of your three new issues cannot start until the GPU question is settled; the
third can start today and should.

---

## 298-75 — Measure fertility on all four text slices, close AI-6
`https://linear.app/298a-team-2-topic-23/issue/298-75`
**2 points · due 12 November · not blocked · start here**

`docs/workbook2/carry_forward.md` records AI-6 as corrected from *met* to *partly met*: the
requirement names four text slices and only English and Hinglish were ever measured. The honest
correction is in the workbook. The fix is not.

- Run `analysis/tokenizer_fertility.py` over all four slices named in AI-6, on **real HinGE**, not
  the 1,091-pair synthetic slice that produced the original figures.
- Extend `reports/fertility.csv` with the missing rows. One table, not a second file.
- Change the carry-forward row from "partly met" to a definite state.
- If a slice cannot be measured because the data does not exist, say that in the requirement. A
  requirement that cannot be evaluated should not be scored as partly met.

Two points, and it closes a numbered requirement the workbook is graded against. Do it first
because it needs no GPU and no one else's work.

**Caveat you already know:** this needs `HinGE.pkl`, which is not in the repository and is not
committable. `scripts/convert_hinge_pkl.py` now exits 3 with a message naming the file instead of
dumping a traceback, but it still cannot invent the corpus. Get the file from Shibin, who ran it
under 298-44.

---

## 298-74 — Model 3: sweep K, continued pre-training, two controls
`https://linear.app/298a-team-2-topic-23/issue/298-74`
**8 points · due 20 November · blocked by 298-54, 298-51, 298-72**

This is the project. Everything else is scaffolding for this measurement.

Recipe as revised in `docs/workbook2/section_4_1.md`:

- Sweep K from **500**, not 3,000. The original figure was picked without evidence, and the
  fertility data suggests the useful forms concentrate in a minority of groups, so the curve may
  flatten early.
- Replay at **20%** monolingual English, not 10%.
- Name the continued-pre-training corpus in the run config. Section 4.1.3 names it; the code must
  not quietly use something else.
- Initialise each new embedding as the **mean of its subword pieces** under the old tokenizer. A
  random init confounds the vocabulary effect with an optimisation effect, and the whole point of
  this arm is to separate those.

**The controls are the issue.** Control A is continued pre-training with the *original* tokenizer.
Control B is the extended tokenizer with *no* continued pre-training. If M3 beats M2 but Control A
matches M3, the gain is extra Hinglish pre-training and the tokenizer claim is dead. Report that
outcome exactly as readily as the other one — it is a finding, not a failure.

Acceptance: three seeds per configuration, a `run.json` per run under 298-73's contract, fertility
and coverage re-measured on the extended tokenizer and reported beside the pre-extension figures,
the K sweep plotted against both fertility and the dev metric, scored through the harness.

**Do not start the 45-hour sweep before 298-72 resolves the budget.** The arms currently sum to 177
GPU-hours against a 145-hour cap, and M3 at 45 hours is the largest single item in that overrun.

---

## 298-82 — Model 4: synthetic code-mix fine-tune
`https://linear.app/298a-team-2-topic-23/issue/298-82`
**8 points · due 2 December · blocked by 298-74, 298-76**

Takes the best M3 configuration and adds Equivalence-Constraint synthetic data to the fine-tuning
mixture. The real question is whether synthetic switching adds anything *once the tokenizer is
already fixed*, or whether both interventions address the same deficiency.

- Sweep at least two mixture ratios. A single arbitrary ratio makes a null result uninterpretable —
  it could be the method or it could be the mixture.
- Report the batch's *actual* switch-point distribution from the stats JSON, not just that it was
  matched by design to 0.2398.
- **Re-run the contamination check on the exact batch you train on.** Data gets regenerated and
  gates go stale; inheriting 298-76's check is how test-set leakage gets in.
- Three seeds, `run.json` each, compared against M3 with the paired bootstrap from 298-79.

Depends on Yash's 298-76 producing a real corpus. Do not train on the 30-sentence fixture —
`reports/codemix/README.md` says so explicitly and it is right.

---

## Your blocked work

298-53 and 298-54 now carry blocking relations on the board (298-53 ← 298-51, 298-54 ← 298-53), so
the dependency is visible rather than a thing you keep explaining. Both have real smoke-test
evidence committed: M1 at 0-shot chrF++ 15.919 and 5-shot 31.448 on 48 synthetic lines with a 0.5B
stand-in, M2 at 17.6M trainable parameters and chrF++ 45.118 over 30 steps. Those prove the paths
execute. They are not results and the issues correctly say so.

One finding from the M1 smoke run worth carrying into the error analysis: **0-shot leaked Devanagari
into 13 of 48 outputs** despite a system prompt forbidding it, while 5-shot produced none. That is
exactly the "script" category in Jenil's 298-84 taxonomy, and it is already evidence.

## Order of work

1. 298-75 now — no dependencies, closes a graded requirement.
2. Chase `HinGE.pkl` from Shibin. It blocks 298-75's real-corpus numbers and 298-62's real samples.
3. 298-74 the moment 298-51 and 298-72 clear.
4. 298-82 after 298-74 and Yash's 298-76.
