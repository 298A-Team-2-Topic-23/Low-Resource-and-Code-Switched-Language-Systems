# Low-Resource and Code-Switched Language Systems

An adaptation and evaluation framework for Hindi–English (Hinglish) generation.

**Task:** English sentence → Romanized Hinglish (Hindi–English code-switched, Latin script).

DATA 298A / 298B · San Jose State University, Department of Applied Data Science ·
Team 2, Section 11, Topic 23.

---

## The claim being tested

Quality loss on low-resource and code-switched text is usually blamed on missing data.
Prior work also blames non-Latin script for tokenizer inefficiency. Hinglish is *already*
written in Roman script, so if fertility is still high, neither explanation covers it. Our
claim is **orthographic variance**: `nahi`, `nhi`, `nahii` and `nahin` are one word that
the tokenizer sees as four unrelated vocabulary entries.

Four models form an ablation ladder isolating three competing explanations:

| Model | Adds | Isolates | Status |
|---|---|---|---|
| **M1** Zero-shot | nothing | how large the problem is | script landed, no run yet |
| **M2** PEFT fine-tune (QLoRA) | task supervision | is it just missing task data? | not started |
| **M3** Vocab extension + CPT | representation | is it the tokenizer? | 298B |
| **M4** Augmented | distribution | is it scarcity of code-switched text? | 298B |

Plus two control arms that the hypothesis rests on: **continued pretraining without
vocabulary extension** (so an M3 gain is attributable to the vocabulary rather than the
extra training), and **M2 trained to the same GPU-hours as M3** (so "M3 wins" cannot just
mean "M3 got more compute").

**A null result is an acceptable outcome and is pre-committed to.** Tight error bars and an
attributable cause matter more than the size of any delta. Success is defined as +3 chrF++
over zero-shot with non-overlapping error bars; under 1 chrF++, or overlapping bars, is
reported as a null result.

---

## Quickstart

```bash
git clone https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems.git
cd Low-Resource-and-Code-Switched-Language-Systems
pip install -r requirements.txt
```

`requirements.txt` pins the full training stack including `torch`. If you only want to run
the evaluation harness, `pip install -r evaluation/requirements.txt` is enough — it needs
`sacrebleu` alone.

If the cluster's CUDA driver needs a different torch build, install torch first from the
matching index and then the rest; see the note at the top of `requirements.txt`.

### Verify the install

Three self-tests. None needs a GPU, a model download, or any dataset — they run on a fresh
clone and each one is checked in CI-friendly isolation:

```bash
python common/repro.py --selftest
python analysis/tokenizer_fertility.py --selftest
python evaluation/run_eval.py --hyp evaluation/demo/hyp.seed1.txt evaluation/demo/hyp.seed2.txt --ref evaluation/demo/ref.hinglish.txt --system "smoke test"
```

The third prints a full metric table over five bundled demo sentences. The numbers are
meaningless by design — the demo exists to prove the pipeline runs, not to measure anything.

Then the test suite:

```bash
python -m pytest tests/
```

---

## One command to a scored run

This is a graded deliverable, so it is kept to a single invocation:

```bash
python evaluation/run_eval.py --hyp out/m1.0shot.txt --ref data/test.hinglish.txt --system "Model 1 zero-shot"
```

Multi-seed — one hypothesis file per seed, reported as mean ± standard deviation, which is
what the success criterion requires:

```bash
python evaluation/run_eval.py --hyp out/m2.s1.txt out/m2.s2.txt out/m2.s3.txt --ref data/test.hinglish.txt --system "Model 2 QLoRA" --out results/results.jsonl
```

Accumulate across systems, then print the comparison table for the report:

```bash
python evaluation/run_eval.py --report results/results.jsonl
```

Check a baseline reproduction against the published numbers:

```bash
python evaluation/run_eval.py --hyp out/gahoi_repro.txt --ref data/mixmt.test.ref.txt --system "Gahoi et al. repro" --check-baseline
```

Hypotheses and references are plain text, one sentence per line, aligned by line number. The
harness exits with an error if the counts differ, so a misaligned file fails loudly instead
of producing a quietly wrong score.

---

## Data pipeline — one command, four stages

```bash
python scripts/run_pipeline.py --synthetic --n-synthetic 1200     # offline, no data needed
python scripts/run_pipeline.py --input data/raw/hinge.csv         # the real corpus
```

| Stage | Module | What it prints / writes |
|---|---|---|
| 1 ingest | `src/lrcs/data/ingest.py` | path, file timestamp, bytes, SHA-256, **measured** row and reference counts |
| 2 clean | `src/lrcs/data/clean.py` | attrition table — six filters, each reporting its own removals; rule-based language tags |
| 3 split | `src/lrcs/data/splits.py`, `leakage.py` | near-duplicate grouping, disjoint splits, **leakage gate**, hashed manifest |
| 4 EDA | `src/lrcs/analysis/eda.py`, `codemixing.py` | statistics, spelling variance, four figures, `reports/data_statistics.json` |

`PYTHONPATH=src` is not needed; the script adds `src/` itself. Needs only the standard
library plus `matplotlib` for the figures, and runs on Python 3.9+. `--dup-threshold` is
shared by dedupe and the leakage gate, and the gate **halts** the run (exit code 3, no
manifest written) on any cross-split overlap rather than warning.
`--inject-leak K` exists only to demonstrate the gate halting.

The committed `reports/data_statistics.json` and `reports/figures/` come from a
**synthetic** run — every figure title and the JSON's `"synthetic": true` say so. HinGE
splits are still to be derived from the real file.

---

## Repository layout

```
analysis/          tokenizer fertility, code-mixing statistics, variant lexicon
common/repro.py    seeding + run logging — import from every script that runs anything
data/              raw/ interim/ processed/ are gitignored; manifests are committed
data/goldtestset/  the team-authored gold set, its schema and validator
docs/              datasheet, project management plan, compute budget, decisions
evaluation/        the scoring harness and its demo fixtures
human_eval/        rater agreement tooling and the annotation pilot
models/            generation and training scripts
reports/           pipeline statistics and figures
runs/              one JSON per run — committed, this is the GPU-hour evidence
scripts/           run_pipeline.py — the four-stage data pipeline
src/lrcs/          the pipeline package (ingest, clean, splits, leakage gate, EDA)
tests/             the pytest suite
```

Two rules that matter more than they look:

- **Never commit data.** `.gitignore` covers `data/raw/`. Licences go in the datasheet, not
  the repo.
- **Seed everything.** Import `set_seed` from `common/repro.py` at the top of every script
  that does anything random. The headline result depends on non-overlapping error bars
  across three seeds, so an unseeded run makes it unprovable.

---

## Evaluation

| Metric | Scale | Role | Why |
|---|---|---|---|
| **chrF++** | 0–100 | **primary** | character n-grams plus word bigrams; tolerant of Romanized spelling variance in a way BLEU is not |
| chrF++ (normalised) | 0–100 | secondary | same metric after collapsing spelling variants; **the gap against raw chrF++ is itself evidence of orthographic instability** |
| BLEU | 0–100 | secondary | comparability only; expected to be pessimistic here |
| ROUGE-L | 0–1 | secondary | required to compare against Gahoi et al. (2022), Table 2 |
| WER | 0–1 | secondary | same reason |
| CS penalty | chrF++ points | secondary | monolingual chrF++ minus code-switched chrF++ on identical sources |

Metrics were chosen and justified **in writing before any results were produced**, and are
not to be changed afterwards. Significance is bootstrap resampling (1000 samples); every
reported number is mean ± std over seeds `13, 42, 1337`.

Perplexity, when reported, must be **per byte, not per token** — per-token perplexity is not
comparable across different vocabularies, so it cannot compare M2 to M3.

COMET is deliberately excluded for now: coverage for Romanized Hinglish is uncertain, and
the commitment is to report that limitation rather than quietly rely on the metric.

### Tokenizer fertility — the hypothesis test

`analysis/tokenizer_fertility.py` computes fertility, bytes per token, continuation and
severe-split rates, byte-fallback rate, single-token vocabulary coverage, and
**`spelling_variant_burden`** across four text slices (English, Devanagari Hindi, Romanized
Hindi, Romanized Hinglish) for every candidate tokenizer.

`spelling_variant_burden` is the project's novel metric and the direct test of the claim: the
mean number of tokens paid per surface form across known spelling variants of one word.
Above 1.0 means the vocabulary is paying for spelling noise. A `--cmi-only` mode computes
Code-Mixing Index, Switch-Point Fraction, M-index and burstiness; the measured SPF governs
synthetic-data sampling for M4.

See [analysis/README.md](analysis/README.md) for the full metric definitions, expected
fertility ranges, and preliminary smoke numbers.

### Human evaluation

Three trained bilingual raters plus one external rater on a shared subset; 150–250 segments
stratified across monolingual / code-switched / CMI buckets; blinded and randomised with
system identities hidden and order shuffled per item. Dimensions are adequacy, fluency, and
**code-switching naturalness** — the third is novel and is this project's contribution to
evaluation protocol. Krippendorff's alpha is reported per dimension.

**Declared conflict of interest:** the team authors the evaluation set and also rates
outputs. Mitigated by blinding, randomisation and the external-rater subset, with internal
and external agreement reported separately. This is disclosed in every write-up.

---

## Data

| Source | Role | Licence status |
|---|---|---|
| **HinGE** | primary parallel supervision | unresolved — treat as CC-BY-NC-4.0-equivalent |
| MixMT Subtask-1 test set | baseline reproduction | public research release |
| Samanantar | source text for synthetic generation | see datasheet |
| IIT Bombay En–Hi | source text for synthetic generation | CC-BY-NC-4.0 |
| Dakshina | Romanized–Devanagari alignment | see datasheet |
| Team-authored eval set | held-out benchmark, 800 items | released by us |

Full provenance, verified row counts, licence findings and known limitations are in
[docs/datasheet.md](docs/datasheet.md).

The team-authored evaluation set carries three columns per item — English source, Devanagari
Hindi reference, Romanized Hinglish reference. The third column is what makes the
code-switching penalty directly measurable.

### Split integrity

**HinGE's downstream released train/dev splits are not mutually exclusive.** Our audit found
**285 of dev's 376 unique English sources (75.8%) also present in train**. They are not used
anywhere in this project. Splits are re-derived with near-duplicate grouping — exact
normalised match plus MinHash/LSH over character 4-gram shingles — so paraphrases cannot
straddle a boundary, and manifests with SHA-256 hashes are committed under
`data/processed/manifests/`.

Splits are frozen. **No tuning on test.** Back-translation is the sneakiest contamination
vector: verify the BT source corpus does not intersect the test source before generating
anything.

---

## Reproducibility

- Pinned environment in `requirements.txt`, resolved together with pip.
- Every run takes `--seed`; reported numbers use seeds **13, 42, 1337**.
- Every run is logged. `RunLogger` writes one JSON per run into `runs/`, capturing seed,
  config, metrics, elapsed GPU-hours, git commit (with a `-dirty` marker), package versions
  and GPU name.

```bash
python common/repro.py --summary runs/
```

prints the run table and the total GPU-hours against the 80–145 budget. This is what
evidences the compute claim in the report, so **log every training run in the same commit as
the run**.

Budget: 120–170 GPU-hours across both semesters plus ~20 for inference and evaluation, on
40GB-class cards, one training job per GPU. Continued pretraining and synthetic data
generation count *inside* the budget of the model that uses them.

---

## Reproduced baseline

Gahoi, A., Duneja, J., Padhi, A., Mangale, S., Rajput, S., Kamble, T., Sharma, D., & Varma, V.
(2022). *Gui at MixMT 2022: English-Hinglish — An MT approach for translation of code mixed
data.* Proceedings of the Seventh Conference on Machine Translation (WMT), 1126–1130.

**Table 2**, MixMT Subtask-1: **ROUGE-L 0.617, WER 0.633** on the 500-sentence test set.
System: mBART fine-tuned on English + Hindi input, with Devanagari→Roman transliteration as
post-processing. Target is reproduction within **0.01 ROUGE-L**; `--check-baseline` enforces
that tolerance.

The shared task's own baseline (Google Translate) was rejected as unreproducible — a closed,
continuously updated commercial system cannot satisfy a reproducibility requirement.

**Until the reproduction lands within tolerance, no model result should be interpreted.** The
reproduction's only job is proving the harness is correct; it is *not* one of the four models.

**Known risk:** Gahoi et al. released no code, so the recipe is being re-implemented from the
paper description. If reproduction fails, that is a reportable finding and will be reported
with evidence rather than hidden.

One caveat that matters: MixMT Subtask-1 supplies both English **and** Devanagari Hindi as
input, while our four models receive English only. The reproduction is therefore run under
both conditions — the original for comparability with the paper, English-only as our own
reference point.

---

## Open questions and known discrepancies

Recorded here rather than resolved silently, because each one affects a number that would
otherwise reach a submitted document unchallenged.

- **HinGE human reference count.** Counting directly off `HinGE.pkl` gives **4,799** human
  Hinglish references; the project's locked figure is **4,803**. Four apart. Needs a second
  person to re-count from Table 1 of the source paper before either number is reported. (A
  figure of 6,694 circulates in secondary literature and is wrong for this count.)
- **Backbone model identifier is not settled.** An earlier draft named a configuration that
  does not exist. Every identifier must be checked against the official model card before it
  appears in any submitted document. The commands in `analysis/README.md` carry
  `Qwen/Qwen3-8B` and `google/gemma-3-12b-it` from the task breakdown; neither has been
  verified here yet.
- **Normalisation is near-inert against the variant lexicon.** `evaluation/run_eval.py`
  normalises with regex rules, which fully collapse only **3 of the 72 groups (4%)** in
  `analysis/spelling_variants.tsv`. The dominant Hinglish pattern is vowel *deletion*
  (`nhi`, `kr`, `gya`, `krna`), which vowel-lengthening rules cannot catch, and two forms are
  actively mangled (`hy` → `y`, `hna` → `na`). Since the raw-vs-normalised gap is what the
  write-up presents as evidence of orthographic instability, this must be resolved before any
  normalised number is reported — it is the substance of the open lexicon-based normalisation
  issue.
- **Orthography policy undecided.** Preserve raw spelling, or normalise via a lexicon?
  Preserving raw is more honest and less work; normalising requires shipping the mapping
  table. Must be decided before annotation begins.
- Deployment target and artifact versioning approach are both still open.

---

## How we work

Every change follows: **Linear issue → branch containing the issue ID → commits under the
author's own GitHub identity → PR → independent review → merge → issue Done with the artifact
linked.**

- Branch: `<name>/<ISSUE-ID>-<slug>`
- Commit: `Refs 298-13: add tokenizer fertility script`
- PR body: `Closes 298-13` when the PR completes the issue, otherwise `Refs 298-13`. That
  line is what links the PR to Linear.
- **Nobody approves their own PR.** One approving review from a non-author is required, and
  reviewers rotate each cycle.
- **Nothing closes as Done without a linked artifact** — a PR, commit, dataset version,
  experiment run URL or generated report. A report section counts; a verbal "I did it" does not.

| Member | Primary area |
|---|---|
| Savalia, Jenil Sanjaybhai | data and annotation |
| Shevkar, Yash | data / splits |
| Singh, Prakhar Kumar | infrastructure, cloud, CI |
| Thomas Lnu, Shibin Biji | evaluation harness, baseline reproduction |
| Waghmare, Sarvesh | modelling, training |

Every member carries issues under at least three different labels; label balance is graded
individually.

---

## Build order

Dependencies matter more than enthusiasm here.

1. **Evaluation harness first** — nothing can be scored without it, and building it against a
   published number is the cleanest way to validate that it is correct.
2. **Frozen splits before any training.**
3. **Fertility analysis before M3 design** — the measured numbers determine vocabulary size.
4. **M1, then M2** — M2 establishes the training loop that M3 and M4 reuse.
5. **Deploy something trivial early**, even a model returning garbage, so the infrastructure
   path is proven before the model is good. The demo fails on infrastructure, not modelling.
6. **M4 before M3 in 298B** — M4 reuses M2's recipe with different data; M3 needs new
   embeddings, an initialisation strategy, a CPT run with replay, and a fresh fertility analysis.

Prefer a small thing that runs over a large thing that nearly runs. And keep the failure
cases — bad outputs are a graded deliverable, not noise.

---

## References

Gahoi, A., Duneja, J., Padhi, A., Mangale, S., Rajput, S., Kamble, T., Sharma, D., & Varma, V.
(2022). Gui at MixMT 2022: English-Hinglish — An MT approach for translation of code mixed
data. *Proceedings of the Seventh Conference on Machine Translation (WMT)*, 1126–1130.

Srivastava, V., & Singh, M. (2021). HinGE: A dataset for generation and evaluation of
code-mixed Hinglish text. *Proceedings of the 2nd Workshop on Evaluation and Comparison of
NLP Systems (Eval4NLP)*, 200–208.
