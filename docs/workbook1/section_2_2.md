# 2.2 Project Management Plan

Linear **298-36**. Owner: Sarvesh. Expands the skeleton at
`docs/project_management_plan.md` into the eight subsections the template requires.

---

## 2.2.1 Stakeholder analysis

A stakeholder is listed here only if some decision changes depending on what they
want. Named roles with no decision attached are omitted.

| Stakeholder | What they need | What changes if they are not served |
|---|---|---|
| Project supervisor (Dr. Shim) | A defensible scientific claim with evidence, delivered against the checkpoint dates | The methodology is re-scoped. The four models exist to isolate three competing explanations; if that framing is rejected, the ablation ladder is rebuilt |
| ISA | Board and repository corroborating the written report, checked live | Evidence discipline changes. This is not hypothetical — Progress Report 1 scored the bottom band on Minutes for exactly this |
| Bilingual raters (3 internal, 1 external) | Guidelines unambiguous enough to produce usable agreement | The annotation protocol changes. If Krippendorff's alpha is low, the guidelines are rewritten and the pilot re-run before authoring continues |
| Future researchers | Splits, seeds and manifests sufficient to reproduce a scored run | The artifact policy changes. Manifests with SHA-256 are committed precisely so results are citable without redistributing licensed data |
| Dataset licensors | Non-commercial terms respected, attribution via citation | Data use changes. HinGE has no stated licence and inherits the IIT Bombay CC-BY-NC-4.0 restriction, so commercial deployment is out of scope |

The sharpest conflict is between the supervisor and the ISA. The supervisor's
interest is in the claim; the ISA's is in whether the evidence is visible on the
board and in the repository. Work can be scientifically sound and still score
badly on the second. Section 2.2.8 is the response.

## 2.2.2 Business requirements

Stated as numbers, matching the requirement IDs in section 1.2.

| ID | Requirement | Criterion |
|---|---|---|
| BR-1 | An adapted model measurably beats the zero-shot baseline | +3 chrF++ on the 800-item set, non-overlapping error bars across seeds 13 / 42 / 1337 |
| BR-2 | A null result is reported rather than buried | Under 1 chrF++, or overlapping bars, is published as a null result |
| BR-3 | The evaluation harness is validated against a published number | ROUGE-L within 0.01 of 0.617 (Gahoi et al., 2022, Table 2) |
| BR-4 | The tokenizer cost of orthographic variance is quantified | `spelling_variant_burden` reported; above 1.0 means the vocabulary pays for spelling noise. **Measured: 1.832** |
| BR-5 | Results are reproducible by a third party | One command to a scored run; same seed reproduces byte-identical splits |
| BR-6 | No evaluation on seen data | Leakage gate reports zero shared keys, or the pipeline halts |

BR-2 is a requirement, not a disclaimer. The project is pre-committed to reporting
a null result, and the success criterion was fixed in writing before any result
was produced so that it could not be adjusted afterwards.

## 2.2.3 Development methodology

The project follows an **intelligent-system life cycle**: problem framing → data
acquisition and auditing → representation analysis → model adaptation → evaluation
→ failure analysis → iteration. It differs from a conventional software life cycle
in that the output is a measurement rather than a feature, so the evaluation
harness is built *first* and validated against a published number before any model
result is interpreted.

Build order follows dependency, not enthusiasm:

1. Evaluation harness first — nothing can be scored without it, and building it
   against a published number is the cleanest way to prove it is correct
2. Frozen splits before any training
3. Fertility analysis before M3 is designed — the measured numbers set the
   vocabulary size
4. M1, then M2 — M2 establishes the training loop M3 and M4 reuse
5. Deploy something trivial early, so the infrastructure path is proven before the
   model is good

The methodology is operationalised in Linear and GitHub:

- One Linear team (`298`), six-state workflow, Fibonacci estimates, two-week cycles
  anchored to the four graded checkpoints
- Six labels — `data`, `model`, `eval`, `infra`, `research`, `writing`. Every
  member carries issues under at least three, and label balance is reviewed at each
  team meeting
- Cycle 2 (28 September – 12 October) carries all Workbook 1 work. Cycle 3 begins
  12 October
- Every change: Linear issue → branch carrying the issue ID → commits under the
  author's own GitHub identity → pull request → independent review → merge → issue
  closed with a linked artifact
- `Closes 298-XX` in the pull request body is what links the work to Linear

## 2.2.4 Work breakdown structure

| Deliverable | Owner | Issue | Est | Status |
|---|---|---|---|---|
| §1.1 Background and executive summary | Jenil | 298-32 | 3 | In Progress |
| §1.2 Requirements with numeric criteria | Shibin | 298-33 | 3 | In Progress |
| §1.4 / §1.5 Surveys and comparison tables | Yash | 298-34 | 5 | In Progress |
| §2.1 Data management plan | Yash | 298-35 | 3 | In Progress |
| §2.2 Project management plan | Sarvesh | 298-36 | 8 | In Progress |
| §2.3 / §2.4 Resources and schedule | Prakhar | 298-37 | 5 | In Progress |
| Data pipeline — the live demo | Yash | 298-38 | 8 | In Progress |
| EDA figures and spelling-variance evidence | Sarvesh | 298-39 | 5 | In Progress |
| Demo rehearsal, twice on a fresh clone | Prakhar | 298-40 | 3 | Todo |
| References, checklist, self-assessment | Shibin | 298-41 | 3 | Todo |
| Assembly and submission | Jenil | 298-42 | 3 | Todo |
| Minutes for every meeting | Jenil | 298-43 | 2 | In Progress |

Load is uneven by design, not by accident: Yash carries 16 points because the
pipeline and the data sections share context. If he is short, §1.4/1.5 moves to
Shibin, who carries the lightest load at 6.

## 2.2.5 Scope

**In scope.** One language pair (Hindi–English, Romanized). One generation task,
English → Romanized Hinglish. Four architecturally distinct models sharing one
backbone, an identical token and step budget, and three seeds. Two control arms:
continued pretraining without vocabulary extension, and M2 trained to the same
GPU-hours as M3. One reproduced published baseline. A team-authored 800-item
three-column evaluation set. Blinded human evaluation on adequacy, fluency and
code-switching naturalness.

**Out of scope, deliberately.** A learned language-identification model for
romanised Hinglish — it is its own research problem, and the marker-list tagger is
used instead with its limitations reported rather than overclaimed. Other language
pairs. Speech. Commercial deployment, which the non-commercial licence terms
exclude. Models larger than the 8B class, which the compute budget excludes.

**Priority order when these conflict.** Correctness of the comparison first; a
result that cannot be trusted is worth less than no result. Then reproducibility,
then scope breadth, then performance. Concretely: if the compute budget forces a
choice, single-seed ablations are dropped before the three-seed headline
comparison is weakened, and a fourth model is dropped before a control arm is.

## 2.2.6 Risk register

| Risk | Likelihood | Impact | Trigger | Mitigation | Owner |
|---|---|---|---|---|---|
| Splits not derived — PR #4 closed without merging | **Occurred** | High | No `scripts/make_splits.py` or manifests on `main` | Re-open 298-11 and land it; the determinism fix is already written and reviewed | Yash |
| Board claims Done for work absent from the repo | **Occurred** | High | 298-11, 298-21, 298-25, 298-17, 298-15/16 marked Done with no corresponding file | Reconcile statuses before the 8 October session | All |
| Backbone model identifier unverified | **Occurred** | Medium | An earlier draft named a configuration that does not exist | No identifier enters a submitted document until checked against its official model card | Sarvesh |
| Reference count unreconciled | **Occurred** | Medium | 4,799 measured against 4,803 published | Recount from Table 1 of the source paper; report both until settled | Yash |
| Normalised chrF++ near-inert | **Occurred** | High | Regex rules collapse 3 of 72 lexicon groups | Lexicon-driven normalisation under 298-23; no normalised number reported until then | Shibin |
| No branch protection, no approving reviews | **Occurred** | Medium | API returns 404; nine PRs, zero reviews | Enable protection with one required non-author review | Prakhar |
| Pipeline fails on Python 3.9 at the split stage | **Occurred** | High | `zip(strict=)` is 3.10+; fails *after* stages 1–2 print | Remove the seven call sites; verify on every demo machine | Yash |
| GPU allocation insufficient for M3 | Medium | High | Only 24GB cards available | Gradient checkpointing or a smaller backbone; decide at allocation, not week 7 | Prakhar |
| Gold set not authored in time | High | Medium | 0 of 800 items written | Reduce to 500 items if the piloted rate is too low | Jenil |
| Baseline reproduction fails | Medium | Medium | No public code release from Gahoi et al. | Report the failure with evidence; it is a legitimate finding | Shibin |

Seven of these have already occurred. They are listed as occurred rather than
possible, because a risk register that describes a comfortable project is not a
risk register.

## 2.2.7 Communication and feedback tracking

Team meetings are held at least weekly, with additional working sessions before
each graded checkpoint. Minutes are committed to `docs/minutes/YYYY-MM-DD.md`
**within 24 hours** of the meeting — the commit timestamp is what makes them
verifiable, which back-dating a file cannot. A Linear Project Update is posted
after each meeting.

Every action item in a set of minutes must exist as a Linear issue with an
assignee and a date, or it is not an action item.

Instructor and ISA feedback is tracked to closure on the same path: the feedback is
recorded in the minutes of the session where it was given, converted into a Linear
issue with an owner and a date, and the issue is closed only with a linked
artifact. The Progress Report 1 comment — *"No issue updated on Linear, Repo also
not synched"* — is tracked this way, and section 2.2.8 reports what actually
changed as a result.

## 2.2.8 Evidence that the plan is applied

The rubric asks for evidence that the plan is *in use*, and section 2.5 is graded
on accuracy. A team that rates every row excellent and is then found to have gaps
scores worse than one that finds its own. So this section reports both sides.

**In place and checkable.**

- Linear team live, instructor and ISA holding admin access. Forty-two issues,
  six labels, Fibonacci estimates, cycles anchored to the checkpoint dates
- Nine pull requests, every commit attributable to a named member's GitHub identity
- Evaluation harness producing a scored run from one command, with multi-seed
  aggregation and a `--check-baseline` mode
- Pinned environment, deterministic seeding, per-run JSON logging with GPU-hours
- Datasheet recording provenance and licence findings for four sources, with
  measured row counts rather than quoted ones
- Tokenizer fertility analysis with the project's novel metric, reproducible from
  one command with no GPU
- Test suite in `tests/`, six tests, green

**Not in place, with owners and dates.**

| Gap | Owner | Date |
|---|---|---|
| `main` has no branch protection; the API returns 404 against a report that claims it is on | Prakhar | 8 Oct |
| No pull request has ever received an approving review; two were self-merged | All | 8 Oct |
| PR #6 merged with an empty body, so it links to no Linear issue | Jenil | 8 Oct |
| Several issues marked Done have no corresponding file on `main` | All | 8 Oct |
| `CONTRIBUTING.md` is referenced in Progress Report 1 and does not exist | Prakhar | 8 Oct |
| Splits not yet derived; PR #4 closed without merging | Yash | 10 Oct |
| Gold set at 0 of 800 items | Jenil | 20 Oct |

The honest summary is that the engineering discipline is real and the **process
discipline is behind it**. Code is tested, seeded, logged and reviewable. What has
not been enforced is the review gate and the board-to-repository correspondence —
which is the same finding the ISA recorded against Progress Report 1, and it had
not been fully closed at the time of writing.
