# Evaluation Harness

One command, all metrics, multi-seed aware. Produces every number the
abstract commits us to reporting.

## Install

    pip install -r requirements.txt

## Metrics

| Metric | Scale | Role | Why |
|---|---|---|---|
| chrF++ | 0-100 | **primary** | character n-grams plus word bigrams; tolerant of Romanised spelling variance in a way BLEU is not |
| chrF++ (normalised) | 0-100 | secondary | same metric after mapping every form in `analysis/spelling_variants.tsv` to its group label; the gap against case- and punctuation-folded chrF++ (`chrf++_fold`) is the **spelling gap**: how much of our error is orthographic rather than semantic |
| BLEU | 0-100 | secondary | reported for comparability; expected to be pessimistic here |
| ROUGE-L | 0-1 | secondary | needed to compare against Gahoi et al. (2022), Table 2 |
| WER | 0-1 | secondary | same reason |
| CS penalty | chrF++ points | secondary | monolingual chrF++ minus code-switched chrF++ on identical sources |

Neural metrics (COMET) are deliberately excluded for now: coverage for
Romanized Hinglish is uncertain, and the abstract commits us to reporting that
limitation rather than quietly relying on the metric.

Every metric is reported as mean ± standard deviation over seeds **and** a 95%
confidence interval from a 1,000-sample bootstrap over test items. ROUGE-L and
WER are computed on case- and punctuation-folded tokens with spelling left
alone, so they see the words the published baseline was scored on.

## Normalisation

Normalisation is driven by the team's spelling-variant lexicon, the same file
the pipeline tags with (`src/lrcs/lexicon.py`). It lower-cases, strips
punctuation, cuts letter runs of three or more to one (`nahiiii` → `nahi`),
and replaces each lexicon form with its group label. Words outside the lexicon
are left untouched. Every run prints how many lexicon groups the normaliser
collapses; quote no normalised figure without it.

It replaced regex rules that collapsed 3 of the 72 groups, missed vowel
deletion (`nhi`, `kr`, `gya`) and corrupted correct words (`khyal` → `kyal`,
`sahna` → `sana`). `tests/test_run_eval.py` runs the same checks against a copy
of those rules and expects them to fail.

Normalisation applies to the metric only. Training data and references are
never normalised: the variance is what the project measures.

## Usage

Single run:

    python run_eval.py --hyp out/model1.txt --ref data/test.hinglish.txt \
        --system "Model 1 zero-shot"

Multi-seed - one hypothesis file per seed, get mean +/- standard deviation:

    python run_eval.py \
        --hyp out/m2.s1.txt out/m2.s2.txt out/m2.s3.txt \
        --ref data/test.hinglish.txt \
        --system "Model 2 QLoRA"

Code-switching penalty - also score the same sources against the monolingual
Hindi reference:

    python run_eval.py --hyp out/m2.hinglish.txt --ref data/test.hinglish.txt \
        --mono-hyp out/m2.hindi.txt --mono-ref data/test.hindi.txt \
        --system "Model 2 QLoRA"

Baseline reproduction check against the published numbers:

    python run_eval.py --hyp out/gahoi_repro.txt --ref data/mixmt.test.ref.txt \
        --system "Gahoi et al. repro" --check-baseline

Paired significance test against another system on the same references:

    python run_eval.py --hyp out/m2.s1.txt out/m2.s2.txt out/m2.s3.txt \
        --ref data/test.hinglish.txt --system "Model 2 QLoRA" \
        --vs-hyp out/m1.s1.txt out/m1.s2.txt out/m1.s3.txt --vs-system "Model 1"

This prints, for each metric, the difference, its 95% bootstrap interval and a
one-sided p-value (the share of resamples in which the first system does not
win). `--bootstrap 0` turns the intervals off for a quick look.

Accumulate results and print the report table:

    python run_eval.py ... --out results/results.jsonl
    python run_eval.py --report results/results.jsonl

## Input format

Plain text, one sentence per line, hypotheses and references aligned by line
number. The harness exits with an error if the line counts differ, so a
misaligned file fails loudly rather than producing a quietly wrong score.

## Published reference point

Gahoi et al. (2022), *Gui at MixMT 2022: English-Hinglish - An MT Approach for
Translation of Code Mixed Data*, WMT, pp. 1126-1130, **Table 2**:

- ROUGE-L **0.617**
- WER **0.633**

on the 500-sentence MixMT Subtask-1 test set. `--check-baseline` compares our
reproduction against these with a tolerance of 0.01, as committed in the
abstract. Until that check passes, no model result should be interpreted - the
reproduction exists to validate this harness.

## A note on normalisation

`normalise()` collapses common Romanised Hindi spelling variants
(*nahi / nhi / nahii / nahin* into one form). It is used **only** for the
normalised metric and for ROUGE-L/WER tokenisation.

Never apply it to training data or to the gold references. Orthographic
variance is the phenomenon this project studies, not noise to be removed.

## Demo

`demo/` holds five aligned sentences so the harness can be exercised without
the real dataset. Numbers from the demo are meaningless - it exists to prove
the pipeline runs.

    python run_eval.py --hyp demo/hyp.seed1.txt demo/hyp.seed2.txt \
        --ref demo/ref.hinglish.txt --system "smoke test"

`demo/ref.hindi.txt` and `demo/hyp.hindi.txt` (Devanagari) exercise the
code-switching penalty:

    python run_eval.py --hyp demo/hyp.seed1.txt --ref demo/ref.hinglish.txt \
        --mono-hyp demo/hyp.hindi.txt --mono-ref demo/ref.hindi.txt \
        --system "CS penalty smoke test"
