# Baseline reproduction: what we tried, what broke, and what replaces it

Owner: Waghmare (surface and evidence), Thomas Lnu (298-52, the reproduction itself).
Written 10 November 2026. This is the evidence behind Team Meeting 2 slide 7, which asks for
"the published number, your reproduction, the gap, and your explanation — **or**, if you could
not reproduce it: what you tried, with evidence."

## 1. The gate we committed to cannot be run

Workbook 2 §4.4 pins the reproduction gate to:

> ROUGE-L … the published baseline's own metric, needed to check the harness against
> Gahoi et al. (2022), Table 2 — **MixMT Subtask-1 test set, 500 sentences**

That test set was never released.

**Evidence.** The WMT22 MixMT task page (`statmt.org/wmt22/code-mixed-translation-task.html`)
links, for Subtask 1, four Google Drive files: synthetic training, synthetic validation,
human-generated training, human-generated validation. There is **no test download**, and the
page's own test-phase entry under Submission Requirements reads:

> Test phase — TBD

The page points to a CodaLab competition (`codalab.lisn.upsaclay.fr/competitions/2861`) for
submission. The task's test phase ran 1–30 July 2022 and the references were never published.
So the 500-sentence figure in §4.4 cannot be checked against anything, and a reproduction
reported against it would be a reproduction against a set we do not have.

This is not a licensing problem that a signed form fixes. It is an availability problem.

## 2. What replaces it, and why it is a fair swap

**CMU Hinglish DoG**, fetched by `scripts/fetch_data.py --only cmu_dog` from
`festvox/cmu_hinglish_dog` at pinned revision `19796c6f`, CC-BY-SA-3.0 and GFDL.

It is the same task in the same direction — **English → Romanised Hinglish** — and it is the
dataset behind two published evaluations:

- the **English→Hinglish machine translation task in GLUECoS** (Khanuja et al., ACL 2020), whose
  baseline method is mBART fine-tuned on this data;
- the **CALCS 2021 shared task** on machine translation for code-switched data
  (Chen et al., arXiv 2202.09625).

Our extracted split sizes match the shared task's reported sizes exactly, which is how we know
it is the same data:

| Split | Turns | Usable En→Hinglish pairs | Unique pairs |
|---|---:|---:|---:|
| train | 8,060 | 8,060 | 7,533 |
| validation | 942 | 942 | 929 |
| test | 960 | 960 | 891 |
| **total** | **9,962** | **9,962** | — |

The splits are **fixed upstream** and we do not re-draw them. Unlike the HinGE splits, these are
not ours to freeze.

## 3. The published numbers to reproduce against

| System | Metric | Score | Source |
|---|---|---:|---|
| CALCS 2021 `baseline1` | BLEU | **11.00** | CALCS 2021 shared-task overview |
| CALCS 2021 best system (`UBC_HImt`) | BLEU | **12.67** | same |
| GLUECoS MT baseline | — | mBART fine-tuned; no BLEU in the repo README | `microsoft/GLUECoS` |
| Gahoi et al. (2022), MixMT Subtask-1 | ROUGE-L | 0.617 | unreachable, see §1 |

**Reproduction target.** Fine-tune on the 8,060-pair train split and score the 960-pair test
split with BLEU. A result in the region of 11 would reproduce the shared-task baseline; the
interesting number is where our M1 and M2 land relative to 11.00 and 12.67.

BLEU is the comparison metric **here only**, because it is what the published work reports.
chrF++ remains this project's primary metric on its own evaluation sets, and §4.4 is not
revised: BLEU was already committed there as a secondary metric "for comparability with prior
machine-translation work".

## 4. The caveat that must travel with any number we report

**Our 960-turn test split may not be byte-identical to the shared task's scored test set.**
The CALCS leaderboard was computed on CodaLab against references the organisers held; what the
Hugging Face distribution calls `test` is the dataset's own test split. The counts agree with
the published description, which is good evidence they are the same data, but we have not seen
the organisers' file.

So any comparison with 11.00 and 12.67 is **indicative, not a leaderboard-equivalent result**,
and must be labelled that way on the slide and in the final report. The alternative — reporting
against the MixMT number we cannot obtain at all — is worse.

## 5. What is done and what is not

| Step | State |
|---|---|
| Establish that the MixMT gate is unrunnable, with evidence | **Done** (§1) |
| Obtain a surface with published numbers and downloadable references | **Done** — fetched, pinned, hashed in `data/raw/MANIFEST.json` |
| Record the published numbers to beat | **Done** (§3) |
| Extract En→Hinglish pairs from the `translation` dicts | **Done** — 9,962 pairs |
| Fine-tune and score on this split | **Not done** — 298-52 |
| Report the gap and explain it | **Not done** — depends on the above |

Slide 7 can therefore be honest in full: we have the published number, the surface, and the
reason the original gate failed, with a page citation for each. The reproduction run itself is
outstanding, and that is what the slide should say.

## 6. Provenance

| Item | Value |
|---|---|
| Dataset | `festvox/cmu_hinglish_dog`, revision `19796c6f`, CC-BY-SA-3.0 and GFDL |
| Fetched by | `scripts/fetch_data.py --only cmu_dog` |
| Hashes | `data/raw/MANIFEST.json` |
| Original paper | Zhou, Kang & Black (2018), *A Dataset for Document Grounded Conversations*, EMNLP 2018 |
| Benchmark papers | Khanuja et al. (2020), GLUECoS, ACL 2020; Chen et al. (2022), CALCS 2021 shared task, arXiv 2202.09625 |
| MixMT task page checked | `statmt.org/wmt22/code-mixed-translation-task.html`, 10 November 2026 |
