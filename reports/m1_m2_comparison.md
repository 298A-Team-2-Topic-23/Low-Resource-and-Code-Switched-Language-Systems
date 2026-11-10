# M1 against M2, on real data — the first reportable comparison

Measured 10 November 2026. Qwen2.5-7B-Instruct-4bit, 197 HinGE test sources, multi-reference
scoring as Workbook 2 §4.4 commits. Apple M4, 16 GB, via MLX. No GPU allocation was used.

**Headline: M2 wins the primary metric decisively and moves *away* from human code-switching at
the same time.** Both halves of that sentence are the result.

## 1. Quality metrics — M2 wins, and it is not close

| Metric | M1 zero-shot | M2 LoRA (it500) | Paired difference, 2,000-sample bootstrap |
|---|---:|---:|---|
| **chrF++** (primary) | 43.270 | **57.808** | **+14.538** 95% CI [10.776, 18.241], p < 0.0001 |
| chrF++ normalised | 44.189 | 59.017 | +14.828 [10.984, 18.560], p < 0.0001 |
| BLEU | 30.740 | 51.482 | +20.742 [14.141, 27.445], p < 0.0001 |
| ROUGE-L | 0.444 | 0.551 | +0.107 [0.075, 0.138], p < 0.0001 |
| WER (lower better) | 0.763 | 0.684 | −0.079 [−0.166, 0.003], p = 0.031 |

The 95% intervals on chrF++ do not overlap at all (M1 [40.324, 46.461], M2 [55.592, 60.026]).

**Devanagari leakage is fixed.** M1 produced 12 outputs containing Devanagari despite an explicit
instruction not to. M2 produced **zero**. For a project whose target is Romanised Hinglish, that
is a real gain that no quality metric above shows clearly.

## 2. Code-mixing metrics — M2 goes the wrong way

Measured with the same LinCE-style tagger the pipeline uses, so these are comparable with
`reports/data_statistics.json`.

| System | CMI | CMI (mixed only) | % sentences mixed | SPF | M-index | Tagger coverage |
|---|---:|---:|---:|---:|---:|---:|
| **Human references (target)** | **25.86** | **30.26** | **85.5%** | **0.2366** | **0.6956** | 0.686 |
| M1 zero-shot | 15.40 | 30.04 | 51.3% | 0.2007 | 0.7951 | 0.679 |
| M2 LoRA (it500) | 11.88 | 20.71 | 57.4% | 0.0951 | 0.2978 | 0.872 |
| English source (floor) | 0.00 | 0.00 | 0.0% | 0.0000 | 0.0000 | 0.901 |

M2 is further from the human target than M1 on CMI, on mixing strength, on switch-point fraction,
and on M-index. Only "% sentences mixed" improved, 51.3% to 57.4%.

**This is not a tagger artifact, and I checked that before reporting it.** The obvious worry is
that M2 writes spellings the tagger cannot resolve, deflating its CMI. The opposite is true:
M2's tagger coverage is **0.872**, close to the English floor's 0.901, while M1 (0.679) and the
human references (0.686) sit far below. M2's output is *more* resolvable because *more of it is
recognisable English*.

## 3. The mechanism: the two systems mix in opposite directions

| | Example |
|---|---|
| Source | `install the standard and TSC pumps` |
| Human | `Manak aur TSC pump install kre` |
| M1 | `install the standard aur TSC pumps` |
| M2 | `Install the standard and TSC pumps.` |

| | Example |
|---|---|
| Source | `Project Manager Plugin for Anjuta.` |
| Human | `Pariyojana prabandhak plugin for Anjuta.` |
| M1 | `Project Manager Plugin for Anjuta.` |
| M2 | `Anjuta ke liye Project Manager Plugin.` |

| | Example |
|---|---|
| Source | `The Englishman ' s eyes lit up .` |
| Human | `Angrej ki eyes lit up.` |
| M1 | `The Englishman's eyes lit up.` |
| M2 | `The Englishman ka aankh lit up.` |

**Humans write a Hindi frame and insert English content words.** `Manak aur TSC pump install kre`
is mostly Hindi, with `TSC pump` and `install` kept in English.

**M2 learned to write an English frame and insert Hindi function words.** `Anjuta ke liye Project
Manager Plugin` keeps every content word in English and adds the postpositional phrase `ke liye`,
reordering to Hindi word order. `The Englishman ka aankh lit up` is the same move.

Those are opposite directions of insertion, and they explain the contradiction. chrF++ rewards
M2's direction, because preserving the English source words preserves exactly the character n-grams
that also appear in the references. CMI punishes it, because CMI counts the share of tokens from
the non-dominant language and M2's outputs stay English-dominant.

**So M2's gain is partly a gain in surface agreement rather than in code-switching.** That is a
finding about the metric as much as about the model, and it is the concern Srivastava & Singh raise
in the HinGE paper itself: standard generation metrics behave poorly on code-mixed text. Our own
§4.4 anticipated it, which is why chrF++ was never the only committed measure.

## 4. What this does not establish

- **M2 is undertrained, deliberately.** 600 iterations at batch size 1 is ~0.16 epochs over 3,738
  pairs, and the evaluated checkpoint is iteration 500, so about 500 examples were seen. The
  direction of the code-mixing result may reverse with a longer run. **This is a preliminary
  comparison, not the ablation result.**
- **One seed.** 298-54 asks for three. Everything here is seed 42, so none of these numbers carries
  a seed-variance estimate, and the bootstrap intervals are over test items only.
- **M2's outputs are about 20% longer** than the references (18.6 words against 15.5; M1 is 16.1).
  chrF++ is an F-score and so not freely gamed by length, but some of the +14.5 is plausibly length
  agreement rather than content agreement, and that is not separated here.
- **Checkpoint selection was constrained.** Validation loss was 2.003 at iteration 450, 2.111 at
  500, 2.025 at 550 and 2.378 at 600. The best measured point, 450, was not saved; the final
  adapter is the worst of the three saved. Iteration 500 is the best *saved* checkpoint with a
  *measured* validation loss, so it is what was evaluated. A cleaner run would align `save_every`
  with `steps_per_eval`.
- **Both systems still copy the source verbatim** on about 17% of sentences: M1 on 35 of 197, M2 on
  33. Fine-tuning barely touched that failure.

## 5. What it does establish, for Team Meeting 2

1. The ablation ladder produces a large, significant, reproducible improvement from M1 to M2 on the
   committed primary metric, measured on real data with run records for both.
2. Training on real Hinglish eliminates Devanagari leakage entirely.
3. **The project needs its code-mixing metrics, and this run is the proof.** A reader shown only
   chrF++ would conclude M2 had learned to code-switch. It had partly learned to agree with the
   references' surface while code-switching less. Slide 4's question — "when would your preferred
   model lose?" — now has a measured answer rather than a hypothetical one.
4. Compute: M1 inference 0.222 GPU-hours, M2 training 0.889, M2 inference 0.216. **1.33 GPU-hours
   total on a laptop**, against a 145-hour cap.

## 6. Provenance

| Item | Value |
|---|---|
| Base model | `mlx-community/Qwen2.5-7B-Instruct-4bit` |
| Corpus | HinGE, `LingoIITGN/HinGE` rev `e25a1038`, CC-BY-4.0, input SHA-256 `dcfaf37c…` |
| Splits | `data/processed/manifests/hinge_split_manifest.json`, 3,738/468/468, leakage gate passed |
| Test set | 197 sources, 468 references, mean 2.376 per source |
| Supervision | `data/sft/hinge/manifest.json` (carries the exact prompt) |
| Recipe | `configs/m2_lora_qwen7b.yaml` |
| M1 run record | `runs/20261110T210413Z_m1-zero-shot-qwen2-5-7b-4bit_seed42.json` |
| M2 train record | `runs/20261110T220440Z_m2-lora-qwen2-5-7b-4bit-seed-42.json` |
| M2 inference record | `runs/20261110T221902Z_m2-lora-qwen2-5-7b-4bit-seed42-it500_seed42.json` |
| Scores | `results/results.jsonl`, `reports/codemixing_systems.json` |
| Learning curve | `reports/figures/fig7_training_curves.png` |
