# Yash — Progress Report 2 brief

| Issue | What | Est | Due |
|---|---|---|---|
| [298-35](https://linear.app/298a-team-2-topic-23/issue/298-35) | **Section 2.1 Data Management Plan** — overdue | 3 | **tonight** |
| [298-57](https://linear.app/298a-team-2-topic-23/issue/298-57) | Workbook 2 sections 3.1–3.6 | 5 | 6 Nov |
| [298-58](https://linear.app/298a-team-2-topic-23/issue/298-58) | Back-translation corpus + contamination check | 5 | 9 Nov |

---

## Tonight

**Close 298-35.** It has been In Progress since 8 October and is one of the four issues
making Cycle 3 read 0 of 13 points. The content largely exists in `docs/datasheet.md` —
your own merged work — so this is assembling rather than starting.

**Then help Sarvesh with Part A rows 3.1–3.6.** You own the data engineering, so you are the
one who knows whether those rows are 80% complete or 40%. The pipeline is merged and runs on
the real corpus, so Complete is high; the §3 prose is not written, so Document is low. That
gap is expected and needs the written explanation the template asks for.

## 298-57 — Workbook 2 section 3, and why it is the easiest marks available

Workbook 2 is due **11 November**. Unusually for this project, the work is already done and
merged — what is missing is prose. Every number is committed in
`reports/data_statistics.json` and the demo notebook, so you are writing against evidence
rather than producing new engineering.

| § | What it needs | Numbers you already have |
|---|---|---|
| 3.1 Data Process | the four stages; gate **halts**, not warns | 12 s end to end |
| 3.2 Collection | provenance, SHA-256, restricted unpickler | 1,976 rows → **4,799** records (paper says 4,803) |
| 3.3 Pre-processing | six filters, each charged its own removals | 25 not-romanized, 87 length, 11 ratio, 2 dup, **125 total**, 4,674 kept |
| 3.4 Transformation | NFC + whitespace, **and why spelling is not normalised** | — |
| 3.5 Preparation | near-duplicate grouping, splits, manifests | 1,938 → 1,937 groups; **3,738 / 468 / 468**; zero leakage |
| 3.6 Statistics | corpus character | CMI **25.3**, SPF **0.240**, M-index 0.693, **86.1%** mixed |

Two things to state as limitations rather than let someone find: the tagger resolves only
**68.2%** of word tokens, so every code-mixing figure carries that caveat; and the HinglishEval
leakage is **75.8% on valid and 78.1% on test** — the test figure is stronger evidence than
the one we have been quoting and it belongs in 3.5.

## 298-58 — the contamination check, before any generation runs

Back-translation is the sneakiest contamination vector in the project. If the monolingual
corpus used to generate synthetic pairs overlaps the test source, **every Model 4 number is
invalid and our own leakage gate will not catch it** — the gate only checks our splits
against each other.

So the check runs **before** generation, not after.

Reuse `lrcs.data.leakage` at the same Jaccard threshold the splits use — using a different
threshold is exactly the bug that let pairs slip through earlier in the project. Commit it as
a re-runnable script rather than a one-off result, and record the filter thresholds you
settle on: length ratio, LaBSE or LASER cosine similarity, round-trip chrF.

If an overlap turns up, remove the offending sources and report the count. That is a finding,
not a failure.
