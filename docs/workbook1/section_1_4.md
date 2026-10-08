# 1.4 Technology and Solution Survey

Linear **298-34**. Author: Savalia, Jenil Sanjaybhai.

This section compares the candidate technologies for each layer of the system — the
backbone model, the adaptation method, the evaluation stack, and the serving and
experiment infrastructure — and records a decision for each. Every candidate was judged
against the same four constraints, each traceable to §1.2: a single 40GB-class GPU per job
(AI-9), deterministic and seeded runs (FR-5, FR-8), a measured rather than assumed tokenizer
cost (AI-5, AI-6), and a licence that does not block the team from using or releasing its
results (DR-8).

**How model facts were verified.** No model identifier appears in this section unless it
was resolved against its official Hugging Face model card on **8 October 2026**. Licence,
gating and parameter count come from the Hub API record; vocabulary size and context length
come from the model's `config.json` where it is publicly readable; language and mode claims
are quoted from the model card. Anyone can repeat the check:

```bash
curl -s https://huggingface.co/api/models/Qwen/Qwen2.5-7B-Instruct
```

Parameter-memory figures marked *(our arithmetic)* are weights only — parameters × bytes per
parameter — and exclude activations, optimizer state and KV cache unless stated.

---

## 1.4.1 Backbone model

| Candidate | Class | Key features (verified 8 Oct 2026) | Fit for us | Decision |
|---|---|---|---|---|
| `Qwen/Qwen2.5-7B-Instruct` | Instruction-tuned decoder LLM | Apache-2.0, not gated; 7.62B parameters; vocabulary 152,064; card states support for "over 29 languages" and a 131,072-token context | The **only** candidate with a measured tokenizer cost on our data: Hinglish fertility 1.501 against 1.024 for English, `spelling_variant_burden` 1.832 (`reports/spelling_variance.md`). 15.2 GB in bf16, ~3.8 GB at 4 bits *(our arithmetic)* — fits one 40GB card under QLoRA. No reasoning mode to manage, so greedy decoding is straightforward (FR-8) | **Adopt — primary backbone for all four models.** One backbone across arms is required by AI-9, and the hypothesis measurement (AI-5) already exists for this one |
| `Qwen/Qwen3-8B` | Instruction-tuned decoder LLM with a reasoning ("thinking") mode | Apache-2.0, not gated; 8.19B parameters; vocabulary 151,936; card: thinking is **enabled by default** and is switched off with `enable_thinking=False`; needs `transformers>=4.51.0` (pinned 4.57.6 satisfies it). **There is no `Qwen/Qwen3-8B-Instruct`** — that name does not resolve on the Hub | Similar size and the same tokenizer family, but no fertility measured yet. Thinking-by-default conflicts with a short, deterministic translation output unless explicitly disabled | **Secondary — robustness check only**, and only after (a) its fertility and burden are measured with `analysis/tokenizer_fertility.py` and (b) generation passes `enable_thinking=False`. See the note below |
| `google/gemma-3-12b-it` | Instruction-tuned multimodal LLM | Gemma licence, **gated** (users must accept Google's usage terms); 12.19B parameters; card: "over 140 languages", 128K input context, text and image input | Broadest stated language coverage, but 24.4 GB in bf16 *(our arithmetic)* leaves little headroom on 40GB, the vision encoder is unused weight for a text-only task, and gating adds an access step for every team member and any outside reproducer | **Defer.** Revisit in 298B only if the primary and secondary disagree |
| `meta-llama/Llama-3.1-8B-Instruct` | Instruction-tuned decoder LLM | Llama 3.1 Community licence, **gated**; 8.03B parameters; card lists Hindi among eight officially supported languages; 128k context | The only candidate whose card names Hindi explicitly — but the card does not say which script, and our target is Romanized Hinglish. No fertility measured | **Defer.** Same gating cost as Gemma; adopt only if fertility on our slices beats the primary |
| mBART (Gahoi et al., 2022) | Multilingual encoder–decoder | `facebook/mbart-large-50` resolves (MIT licence). Which mBART checkpoint the paper used is not confirmed | Not a candidate backbone: it exists to reproduce the published baseline (AI-4), not to compete with the four models | **Use for baseline reproduction only.** Checkpoint to be confirmed from the paper before the run |

**Note on the merged M1 script.** `models/generate_zeroshot.py` currently defaults to
`--model Qwen/Qwen3-8B` and calls `apply_chat_template` without `enable_thinking=False`. With
thinking on by default, the 128-token generation budget would be spent on reasoning text
rather than the translation. Under the decision above, M1 runs on `Qwen/Qwen2.5-7B-Instruct`;
if Qwen3-8B is used for the robustness check, the script must disable thinking first. The
fertility numbers and the generation script must name the same backbone, or the hypothesis
measurement and the model results describe different tokenizers.

## 1.4.2 Adaptation method

| Candidate | Class | Key features | Fit for us | Decision |
|---|---|---|---|---|
| Full fine-tuning | All parameters updated | Highest capacity; mixed-precision Adam needs roughly 16 bytes per parameter, about 122 GB for 7.6B parameters *(our arithmetic)* | Does not fit one 40GB card; would also break the equal-compute design (AI-9) | **Reject** |
| LoRA (Hu et al., 2022) | Parameter-efficient: frozen base, trainable low-rank updates | Base kept in bf16 (15.2 GB for the primary); only adapter matrices train | Fits, and the adapter form is what M2, M3's second stage and M4 share | **Adopt as the adapter form**; bf16-base LoRA is the fallback if 4-bit quantisation measurably costs quality |
| QLoRA (Dettmers et al., 2023) | LoRA over a 4-bit quantised frozen base | 4-bit NormalFloat, double quantisation, paged optimizers; the paper fine-tunes a 65B model on one 48GB GPU | Leaves the most memory for sequence length and batch size on a 40GB card; `peft` 0.17.1 and `bitsandbytes` 0.47.0 already pinned | **Adopt for M2** (rank 32, all linear projections) and reuse the recipe for M4 |
| Vocabulary extension + continued pretraining | Representation change: new tokens, new embeddings | Hinglish-trained SentencePiece model (`sentencepiece` 0.2.0 pinned) supplies new tokens; embeddings and LM head trained first, adapters second | The only arm that changes how `nahi`/`nhi`/`nahin` are tokenized — the direct test of the hypothesis. Must be paired with a CPT-without-extension control so a gain is attributable | **Adopt for M3 (298B)**, with the control arm |
| Prompt / prefix tuning | Learned soft prompt, base and tokenizer frozen | Very few trainable parameters | Cannot change tokenization, which is the variable under test; adds a fifth method without isolating a new explanation | **Reject** |

## 1.4.3 Evaluation stack

| Candidate | Class | Key features | Fit for us | Decision |
|---|---|---|---|---|
| chrF++ and BLEU via `sacrebleu` 2.6.0 | Surface-overlap metrics | `corpus_chrf(..., word_order=2)` is chrF++ (Popović, 2017); standard, versioned implementation | chrF++ tolerates Romanized spelling variation better than BLEU; BLEU kept for comparability only | **Adopt** — chrF++ primary, BLEU secondary; implemented in `evaluation/run_eval.py` |
| ROUGE-L and WER, in-house | Sequence-overlap and edit-distance metrics | LCS and edit-distance implementations in `evaluation/run_eval.py` | Required to compare against Gahoi et al.'s Table 2 (AI-4). Tokenisation differences from the paper's scorer are a reproduction risk | **Adopt**; the reproduction itself is the check that our implementation matches theirs within 0.01 ROUGE-L |
| Normalised chrF++ | chrF++ after collapsing spelling variants | Current implementation is regex-based | The raw-vs-normalised gap is the evaluation-side evidence for the hypothesis — but today it collapses only 3 of the 72 lexicon groups | **Adopt with a stated defect**; no normalised number is reported until lexicon-based normalisation replaces the regex (298-23) |
| COMET (Rei et al., 2020) | Learned neural metric | Trained on human judgements | Coverage of Romanized Hinglish is uncertain; relying on it quietly would hide that | **Reject for now**; reported as a limitation (§1.2.4) |
| Bootstrap resampling, 1000 samples | Significance testing | Required by AI-3 | **Not yet implemented** in `evaluation/run_eval.py` | **Adopt — open work item**; no comparison is called significant until it exists |
| Krippendorff's alpha (Krippendorff, 2011) | Inter-rater reliability | Any number of raters, missing ratings allowed; `human_eval/agreement.py` | Our design has three internal raters plus an external rater on a subset (AI-10) | **Adopt**; pilot threshold α ≥ 0.67 |
| Fertility and `spelling_variant_burden` | Tokenizer diagnostics | `analysis/tokenizer_fertility.py`; runs without a GPU | The direct measurement of the hypothesis (AI-5, AI-6) | **Adopt**; re-measured on every candidate backbone and again after M3's vocabulary extension |

## 1.4.4 Serving and experiment infrastructure

| Candidate | Class | Key features | Fit for us | Decision |
|---|---|---|---|---|
| Hugging Face `transformers` generate | Library inference | Already used by the M1 script; greedy decoding with `do_sample=False` | Simplest path for 298A batch generation over the evaluation set | **Adopt for 298A** batch inference |
| vLLM + FastAPI | Serving engine plus HTTP control layer | Batched serving of a base model with LoRA adapters; FastAPI for routing and request logging | Needed only for the 298B demo, where several adapters share one base model | **Adopt for 298B**; not on the 298A critical path |
| Text Generation Inference | Serving engine | Comparable role to vLLM | Duplicates vLLM; one serving engine is enough to maintain | **Reject** |
| CPU quantised inference (GGUF) | Local inference | Runs without a GPU | Re-quantising the weights means the served model is not the evaluated model | **Reject** |
| `RunLogger` in `common/repro.py` | Run logging to `runs/*.json` | Seed, config, metrics, git commit, package versions, GPU-hours; committed with the run | Evidence lives in the repository, where the grader checks (FR-5, FR-6) | **Adopt** |
| Weights & Biases | Hosted experiment tracking | Dashboards, artefact storage | Evidence would live outside the repository and behind an account | **Not adopted**; `wandb/` is gitignored |

---

## Summary of decisions

The system is built on one backbone, `Qwen/Qwen2.5-7B-Instruct`, because it is the only
candidate that is verified, ungated, small enough for QLoRA on one 40GB card, and already
carries a measured tokenizer cost on our data. `Qwen/Qwen3-8B` is held as a robustness
check, conditional on measuring its fertility and disabling its default reasoning mode;
Gemma 3 and Llama 3.1 are deferred because both are gated and neither has been measured.
Adaptation uses LoRA adapters throughout, quantised with QLoRA for M2 and M4, with
vocabulary extension plus continued pretraining reserved for M3 and its control. Evaluation
is chrF++ first, with ROUGE-L and WER for the baseline comparison; two pieces the plan
depends on — lexicon-based normalisation and bootstrap significance — are named here as
open work rather than described as finished.
