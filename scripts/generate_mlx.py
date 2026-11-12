#!/usr/bin/env python3
"""
Generate English-to-Hinglish output with MLX, on Apple Silicon.

This is the inference side of Models 1 and 2. With no `--adapter` it is M1, the
zero-shot baseline; with a LoRA adapter directory it is M2.

Why MLX and not bitsandbytes
----------------------------
Section 4.1 specifies QLoRA with 4-bit NF4 quantisation, which `bitsandbytes`
provides and which is CUDA-only. The GPU allocation (298-51) has been
outstanding since 26 September. MLX does 4-bit quantised LoRA natively on
Apple Silicon, so the ablation ladder can start on the development machine
instead of waiting. The substitution is NF4 -> MLX affine 4-bit, and it is
recorded in the Workbook 2 carry-forward table rather than absorbed silently.

Honesty about what a run is
---------------------------
Every run writes a `runs/*.json` record with the model, the adapter, the prompt,
the decode settings, the seed, wall-clock time, tokens per second and peak
memory. A number without that record is not reportable -- `docs/COMPUTE_BUDGET.md`
already treats three earlier smoke runs that way.

The prompt is read from the supervision manifest, not hardcoded here, so
training and inference cannot drift apart.

Usage
-----
  # M1, zero-shot
  python3 scripts/generate_mlx.py --system "M1 zero-shot" --out results/m1.test.txt

  # M2, after training
  python3 scripts/generate_mlx.py --adapter models/adapters/m2_seed42 \\
      --system "M2 LoRA seed 42" --out results/m2.s42.test.txt

Score what it writes with the harness, multi-reference as section 4.4 commits:
  python3 evaluation/run_eval.py --hyp results/m1.test.txt \\
      --ref-jsonl data/sft/hinge/test_references.jsonl --system "M1 zero-shot"
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

SFT_DIR = REPO_ROOT / "data" / "sft" / "hinge"
DEFAULT_MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
DEVA = re.compile(r"[ऀ-ॿ]")


def load_prompt():
    """The system prompt and user template, from the supervision manifest."""
    path = SFT_DIR / "manifest.json"
    if not path.exists():
        raise SystemExit(
            "{}: not found. Run scripts/build_sft_data.py first -- the prompt "
            "lives there so training and inference cannot drift.".format(path))
    m = json.loads(path.read_text(encoding="utf-8"))
    return m["system_prompt"], m["user_template"]


def load_sources(path):
    sources = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                sources.append(json.loads(line)["english"])
    if not sources:
        raise SystemExit("{}: no sources".format(path))
    return sources


def clean_output(text):
    """One line, no chat scaffolding.

    The harness is line-aligned, so a newline in a hypothesis would shift every
    later line against its reference. Models also like to add "Hinglish:" or a
    bulleted gloss; the first non-empty line is the translation.
    """
    text = (text or "").strip()
    for marker in ("Hinglish:", "Translation:", "hinglish:"):
        if text.startswith(marker):
            text = text[len(marker):].strip()
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    return " ".join(first.split())


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--adapter", default=None,
                   help="LoRA adapter directory; omit for the zero-shot M1 run")
    p.add_argument("--sources", default=str(SFT_DIR / "test_references.jsonl"),
                   help="JSONL with an 'english' field per source")
    p.add_argument("--out", required=True, help="hypotheses, one per line")
    p.add_argument("--system", default="unnamed", help="system name for the run record")
    p.add_argument("--max-tokens", type=int, default=128)
    p.add_argument("--temp", type=float, default=0.0,
                   help="0.0 is greedy. M1 and M2 are compared greedily so the "
                        "difference is the model, not the sampler")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--limit", type=int, default=None, help="first N sources only (smoke runs)")
    p.add_argument("--runs-dir", default=str(REPO_ROOT / "runs"))
    args = p.parse_args(argv)

    import mlx.core as mx
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    mx.random.seed(args.seed)
    system, user_tpl = load_prompt()
    sources = load_sources(args.sources)
    if args.limit:
        sources = sources[: args.limit]

    print("model    {}".format(args.model))
    print("adapter  {}".format(args.adapter or "(none -- zero-shot)"))
    print("sources  {:,} from {}".format(len(sources), args.sources))
    print("decode   greedy" if args.temp == 0 else "decode   temp {}".format(args.temp))

    t0 = time.time()
    model, tokenizer = load(args.model, adapter_path=args.adapter)
    load_s = time.time() - t0
    print("loaded in {:.1f}s\n".format(load_s))

    sampler = make_sampler(temp=args.temp)
    hyps, n_out_tokens = [], 0
    t0 = time.time()
    for i, src in enumerate(sources, start=1):
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user_tpl.format(english=src)}]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        raw = generate(model, tokenizer, prompt=prompt, sampler=sampler,
                       max_tokens=args.max_tokens, verbose=False)
        line = clean_output(raw)
        hyps.append(line)
        n_out_tokens += len(tokenizer.encode(line))
        if i % 25 == 0 or i == len(sources):
            el = time.time() - t0
            print("  {:>4}/{:<4}  {:.1f}s elapsed, {:.2f}s/sentence, eta {:.0f}s".format(
                i, len(sources), el, el / i, (len(sources) - i) * el / i))
    elapsed = time.time() - t0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(hyps) + "\n", encoding="utf-8")

    empty = sum(1 for h in hyps if not h)
    deva = sum(1 for h in hyps if DEVA.search(h))
    peak_gb = mx.get_peak_memory() / 2 ** 30

    record = {
        "kind": "generate",
        "system": args.system,
        "model": args.model,
        "adapter": args.adapter,
        "prompt": {"system": system, "user_template": user_tpl},
        "decode": {"temp": args.temp, "max_tokens": args.max_tokens, "seed": args.seed},
        "sources_file": args.sources,
        "n_sources": len(sources),
        "output_file": str(out),
        "load_seconds": round(load_s, 2),
        "generate_seconds": round(elapsed, 2),
        "seconds_per_sentence": round(elapsed / max(len(sources), 1), 3),
        "output_tokens": n_out_tokens,
        "output_tokens_per_second": round(n_out_tokens / max(elapsed, 1e-9), 2),
        "peak_memory_gb": round(peak_gb, 2),
        # Hardware, because "compute actually consumed" is a Team Meeting 2
        # slide and "a laptop" is not an answer.
        "device": "Apple M4, 16 GB unified memory (MLX)",
        "gpu_hours": round(elapsed / 3600, 5),
        "empty_outputs": empty,
        "devanagari_outputs": deva,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    runs = Path(args.runs_dir)
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = re.sub(r"[^A-Za-z0-9]+", "-", args.system).strip("-").lower()
    rec_path = runs / "{}_{}_seed{}.json".format(stamp, tag or "generate", args.seed)
    rec_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print("\nhypotheses -> {}".format(out))
    print("run record -> {}".format(rec_path))
    print("{:.1f}s total, {:.2f}s/sentence, {:.1f} tok/s, peak {:.2f} GB, {:.4f} GPU-hours"
          .format(elapsed, record["seconds_per_sentence"],
                  record["output_tokens_per_second"], peak_gb, record["gpu_hours"]))
    if empty:
        print("{} empty output(s): the harness is line-aligned, so these score 0 "
              "rather than being skipped".format(empty))
    if deva:
        print("{} output(s) contain Devanagari despite the instruction not to. "
              "That is a finding about the model, not a bug: the target is "
              "Romanised, so they will score near zero.".format(deva))
    return 0


if __name__ == "__main__":
    sys.exit(main())
