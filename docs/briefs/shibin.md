# Shibin — Workbook 1 brief

**Your issues: 298-33, 298-41. 6 points.**

| Issue | What | Est | Due |
|---|---|---|---|
| [298-33](https://linear.app/298a-team-2-topic-23/issue/298-33) | §1.2 Requirements with numeric success criteria | 3 | 5 Oct |
| [298-41](https://linear.app/298a-team-2-topic-23/issue/298-41) | References, checklist, honest self-assessment | 3 | 6 Oct |

You have the lightest load, and Yash has the heaviest at 16 points. **If he is
short, §1.4/1.5 (298-34) moves to you.** Agree that today, not on the 7th.

You also close the demo. See [DEMO_RUNBOOK.md](../DEMO_RUNBOOK.md).

Read [README.md](README.md) for setup and the PR workflow before you start.

---

## 298-33 — §1.2 Requirements

The template says it explicitly: **state your success criteria as numbers.** A
requirement whose test column has no number scores "incomplete". That is the whole
mark.

Three tables.

**Functional (FR-n)**

| ID | Requirement | Test and measure |
|---|---|---|
| FR-1 | System generates Romanized Hinglish from English input | 100% of 800 eval items produce non-empty Latin-script output; 0 Devanagari characters |
| FR-2 | One command produces a scored run | `python evaluation/run_eval.py --hyp … --ref …` exits 0 and prints all six metrics |
| FR-3 | Every run is seeded and logged | one JSON per run in `runs/`, carrying seed, git commit, elapsed GPU-hours |

**AI-powered (AI-n)**

| ID | Requirement | Test and measure |
|---|---|---|
| AI-1 | Adapted model beats zero-shot | **+3 chrF++** over M1 on the 800-item set, non-overlapping error bars over seeds 13/42/1337 |
| AI-2 | Null result reported honestly | **under 1 chrF++**, or overlapping bars, is reported as a null result |
| AI-3 | Baseline reproduced within tolerance | ROUGE-L within **0.01** of 0.617 (Gahoi et al. 2022, Table 2) |
| AI-4 | Tokenizer cost measured | `spelling_variant_burden` reported; **> 1.0** means the vocabulary pays for spelling noise |

**Data (DR-n)**

| ID | Requirement | Test and measure |
|---|---|---|
| DR-1 | Splits are disjoint | leakage gate reports **0 shared keys**; pipeline halts otherwise |
| DR-2 | Splits are reproducible | same seed → **byte-identical** SHA-256 in the manifest |
| DR-3 | No raw data committed | `git ls-files data/` returns only manifests and the gold set |
| DR-4 | Every source licensed | 100% of sources have a licence entry in `docs/datasheet.md` |

Numbers you can quote, all already real: chrF++ is primary; seeds are 13/42/1337;
bootstrap 1000 samples; the baseline is ROUGE-L 0.617 / WER 0.633.

Cross-reference the IDs from the Linear issues that implement them — that is the
"requirement IDs referenced by the Linear issues" criterion.

---

## 298-41 — references, checklist, self-assessment

### References

APA, only works actually read, **journal and conference sources above 80%**. Expand
every author list — APA does not permit `et al.` in a reference list. Check each
entry against the ACL Anthology record.

### Checklist

Complete it honestly, including whether every closed Linear issue has a linked
artifact. Several currently do not.

### The self-assessment is graded on accuracy

This is the part people get wrong. **A team that rates every row excellent and is
then found to have gaps scores worse than one that finds its own gaps.** So name
the real ones:

| Gap | Status | Owner |
|---|---|---|
| Backbone model identifier unverified against the official model card | open | Sarvesh |
| Splits are a requirement, not an achieved fact — PR #4 closed unmerged, no `scripts/make_splits.py` on main | open | Yash |
| HinGE reference count unreconciled: **4,799** measured vs **4,803** published | open | Yash |
| `main` has no branch protection; no PR has had an approving review | open | Prakhar |
| Normalised chrF++ collapses only 3 of 72 lexicon groups | open | Shibin |

Each with an owner and a date. That reads as a team in control of its own state.

---

## One thing in your own code you should know about

`evaluation/run_eval.py` normalises with regex rules. Measured against
`analysis/spelling_variants.tsv` (72 groups, 227 attested forms), those rules
**fully collapse 3 groups — 4%.**

The rules handle vowel *lengthening* (`aa→a`, `ii→i`). The dominant Hinglish
pattern is vowel *deletion* — `nhi`, `kr`, `gya`, `krna` — which they cannot catch.
Two cases are also actively corrupted, because `y` is in the consonant class of the
`h(?=consonant)` rule:

- `hai · hain · hy · h` → `{hai, h, y}` — `hy` becomes **`y`**
- `hona · honaa · hna` → `{hona, na}` — `hna` loses its `h`

This matters because the **raw-vs-normalised chrF++ gap is what the write-up
presents as evidence of orthographic instability**. If normalisation is near-inert,
that gap is not measuring what we say it measures.

That is exactly the scope of **298-23**, your lexicon-based normalised chrF++ issue.
The lexicon is already in the repo and ready to drive it. Until then, do not report
a normalised number as evidence — and list it in the self-assessment above.
