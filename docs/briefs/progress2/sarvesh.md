# Sarvesh — Progress Report 2 brief

| Issue | What | Est | Due |
|---|---|---|---|
| [298-46](https://linear.app/298a-team-2-topic-23/issue/298-46) | **Part A: status percentages** — 2 of 5 points | 2 | **tonight** |
| [298-53](https://linear.app/298a-team-2-topic-23/issue/298-53) | Model 1 zero-shot: scored run, 3 seeds | 5 | 3 Nov |
| [298-54](https://linear.app/298a-team-2-topic-23/issue/298-54) | **Model 2 QLoRA: trained and scored** | 8 | 9 Nov |

Also still open: **298-39** (EDA figures) — close it or restate what remains.

---

## 298-46 — Part A, tonight

Four numbers per row across all 25 template rows, including sections not started, listed at
0% rather than omitted. They are usually four different numbers, and the template explicitly
calls a row at 90% complete and 0% documented a warning sign.

**Check each against `main`, not against intention.** Rough guidance from the actual repo:

| Rows | Honest position |
|---|---|
| 3.1–3.6 Data engineering | **High on Complete.** The pipeline is merged, runs on the real corpus in 12 s, 27 tests pass. Document is lower — §3 prose is 298-57, not yet written |
| 2.1–2.4 | High on both — Workbook 1 covered them |
| 1.1–1.5 | High on both |
| **4.5 First Model Implementation** | **Low.** `generate_zeroshot.py` exists; no model has been trained and no run scored |
| **4.6 Baseline Reproduction** | **Low.** Not run. Gahoi released no code |
| 4.1–4.4 | Moderate — proposals, comparison and evaluation methods are written; the harness exists but bootstrap is missing |
| 5 Prototype, 6 Benchmarking | Near zero — nothing deployed, no benchmark table |
| 7 Reproducibility | High — pinned env, seeding, run logs, manifests, splits reproduce byte for byte |
| 8 298B Plan | Low |

Any row where Complete and Document differ by more than 40 points needs a written reason.
Expect that on 3.x: the work is done and the prose is not.

**Do not inflate 4.5 and 4.6.** They are the two rows a grader can disprove fastest, and
Part D has to name them as blockers anyway — inconsistency between the two parts is worse
than a low number.

## 298-53 — Model 1, and what "Done" actually requires

298-24 is marked Done but **no scored run exists**. The script is merged and its CPU paths
are tested; what is missing is a generation run and a score.

M1 is the reference every other number is measured against, so: 0-shot and 5-shot reported
separately, few-shot examples drawn **only** from train, greedy decoding, three seeds
(13 / 42 / 1337), scored through `run_eval.py`, every run logged to `runs/` with GPU-hours.

Verify the model identifier against its official model card before it enters any document.
The repo adopts `Qwen/Qwen2.5-7B-Instruct`; the Workbook 1 table still names the family.

## 298-54 — Model 2, the checkpoint deliverable

The course requires the first of four models to be **trained, fine-tuned or adapted**. A
prompted zero-shot backbone does not satisfy that, so M2 is what Team Meeting 2 actually
checks on 12 November. 298-25 is marked Done with no artifact and is being reset.

Recipe is already decided — QLoRA rank 32, alpha 64, dropout 0.05, **all linear projections**
(q, k, v, o plus gate, up, down), not attention-only. LR 1e-4 to 2e-4, cosine, 3% warmup,
2–3 epochs, effective batch 32–64, bf16, gradient checkpointing, 4-bit NF4 base, loss masked
to completion tokens.

Three seeds, identical token and step budget recorded, GPU-hours logged in
`docs/COMPUTE_BUDGET.md` **in the same commit as the run**.

**If the gain is under 1 chrF++ or the error bars overlap, that is a null result and gets
reported.** It does not get retried until it wins. We committed to that in writing before any
result existed, which is the only reason the commitment is worth anything.

Both of these are blocked by **298-51** — Prakhar confirming the GPU. If that slips past this
week, say so loudly rather than absorbing it.
