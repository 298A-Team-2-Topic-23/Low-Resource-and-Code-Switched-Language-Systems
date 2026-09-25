#!/usr/bin/env python3
"""
Model 1: zero-shot English -> Romanized Hinglish.  [Linear 298-24, owner: Sarvesh]

This is the baseline every other number in the project is measured against.
No training. Prompt the instruction-tuned backbone and record what it produces.

Report 0-shot and 5-shot separately -- they are different conditions and the
abstract's success criterion (+3 chrF++ over zero-shot, non-overlapping error
bars) is defined against this baseline, so which one we mean has to be
unambiguous.

Usage
-----
  # 0-shot
  python models/generate_zeroshot.py --src data/test.en.txt --out out/m1.0shot.txt \
      --model Qwen/Qwen3-8B --shots 0 --seed 42

  # 5-shot, examples drawn from the TRAIN split only
  python models/generate_zeroshot.py --src data/test.en.txt --out out/m1.5shot.txt \
      --model Qwen/Qwen3-8B --shots 5 \
      --examples data/splits/train.tsv --seed 42

  # smoke test on 10 sentences before committing a GPU to the full set
  python models/generate_zeroshot.py --src data/test.en.txt --out /tmp/x.txt --limit 10

  # check the prompt without loading a model at all
  python models/generate_zeroshot.py --src data/test.en.txt --out /tmp/x.txt \
      --shots 5 --examples data/splits/train.tsv --dry-run

Then score it with Shibin's harness (298-14):

  python evaluation/run_eval.py --hyp out/m1.0shot.txt \
      --ref data/test.hinglish.txt --system "Model 1 zero-shot"

Three things this gets right that are easy to get wrong
------------------------------------------------------
  * padding_side = "left" -- batched generation produces garbage with right padding
  * do_sample=False -- greedy decoding, so the baseline is deterministic and
    reproducible across the three seeds rather than noisy
  * few-shot examples come from train only. Drawing them from dev or test leaks
    the answer, and this script refuses to read anything but an explicit
    --examples file so that leak has to be deliberate rather than accidental

The prompt below is tuned on dev only and is reported verbatim in the write-up.
Changing it changes the baseline, which changes every delta in the benchmark
table, so it is versioned here rather than passed in on the command line.
"""

import argparse
import random
import sys
import time
from pathlib import Path

SYSTEM_PROMPT = (
    "You translate English into Hinglish: Hindi written in Roman script, mixed "
    "naturally with English words the way bilingual speakers actually write on "
    "messaging apps. Do not use Devanagari. Do not translate into formal Hindi. "
    "Output only the Hinglish sentence, nothing else."
)


def read_lines(path):
    raw = Path(path).read_text(encoding="utf-8").splitlines()
    lines = [line.rstrip("\n") for line in raw if line.strip()]
    if not lines:
        sys.exit("empty file: {}".format(path))
    # Blank source lines are skipped, which means the output file is shorter than
    # the source file and therefore shorter than the reference file. The harness
    # hard-errors on that mismatch, but it errors long after the GPU time is spent,
    # so say it here.
    if len(lines) != len(raw):
        print(
            "warning: dropped {} blank line(s) from {} -- the output will not line "
            "up with a reference file that still has them".format(
                len(raw) - len(lines), path
            ),
            file=sys.stderr,
        )
    return lines


def load_examples(path, k, seed):
    """Few-shot examples. MUST come from train, never dev or test."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
            rows.append((parts[0], parts[1]))
    if len(rows) < k:
        sys.exit("need {} examples, found {} in {}".format(k, len(rows), path))
    return random.Random(seed).sample(rows, k)


def build_messages(src, examples):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for en, hi in examples:
        msgs.append({"role": "user", "content": en})
        msgs.append({"role": "assistant", "content": hi})
    msgs.append({"role": "user", "content": src})
    return msgs


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--src", required=True, help="English source, one sentence per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--shots", type=int, default=0)
    ap.add_argument("--examples", help="TSV of train examples; required when --shots > 0")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, help="only process the first N lines (smoke test)")
    ap.add_argument("--max-new-tokens", type=int, default=128)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the prompt for the first source line and exit, no model loaded",
    )
    args = ap.parse_args()

    if args.shots > 0 and not args.examples:
        ap.error("--examples is required when --shots > 0")

    srcs = read_lines(args.src)
    if args.limit:
        srcs = srcs[: args.limit]
    # Few-shot selection uses its own seeded RNG rather than the global one, so the
    # same --seed picks the same examples no matter what else has consumed
    # randomness earlier in the process.
    examples = load_examples(args.examples, args.shots, args.seed) if args.shots else []

    if args.dry_run:
        # Cheap way to confirm the few-shot examples and the chat framing look right
        # before a GPU is committed to the full set.
        print("model:  {}".format(args.model))
        print("shots:  {}".format(args.shots))
        print("source lines: {}".format(len(srcs)))
        for role_msg in build_messages(srcs[0], examples):
            print("\n[{}]\n{}".format(role_msg["role"], role_msg["content"]))
        return

    # Seed everything before anything random happens. Deliberately after --dry-run:
    # a real generation run must be seeded and logged, but inspecting the prompt
    # should not be blocked on 298-26 landing.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
    try:
        from repro import set_seed, RunLogger
    except ImportError:
        sys.exit("common/repro.py must be importable (Prakhar's 298-26)")
    set_seed(args.seed)

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        sys.exit("pip install torch transformers accelerate")

    name = "model1-{}shot".format(args.shots)
    cfg = {
        "model": args.model,
        "shots": args.shots,
        "n_src": len(srcs),
        "max_new_tokens": args.max_new_tokens,
        "decoding": "greedy",
    }

    with RunLogger(name, seed=args.seed, config=cfg) as run:
        print("loading {} ...".format(args.model))
        tok = AutoTokenizer.from_pretrained(args.model)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        tok.padding_side = "left"  # required for correct batched generation
        model = AutoModelForCausalLM.from_pretrained(
            args.model, torch_dtype=torch.bfloat16, device_map="auto"
        )
        model.eval()

        outs, t0 = [], time.time()
        for i in range(0, len(srcs), args.batch_size):
            batch = srcs[i : i + args.batch_size]
            prompts = [
                tok.apply_chat_template(
                    build_messages(s, examples),
                    tokenize=False,
                    add_generation_prompt=True,
                )
                for s in batch
            ]
            enc = tok(prompts, return_tensors="pt", padding=True).to(model.device)
            with torch.no_grad():
                gen = model.generate(
                    **enc,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,  # greedy: the baseline must be deterministic
                    pad_token_id=tok.pad_token_id,
                )
            for j in range(len(batch)):
                new = gen[j][enc["input_ids"].shape[1] :]
                text = tok.decode(new, skip_special_tokens=True).strip()
                outs.append(text.split("\n")[0].strip())  # first line only
            done = min(i + args.batch_size, len(srcs))
            rate = done / max(time.time() - t0, 1e-6)
            print("  {}/{}  ({:.1f} sent/s)".format(done, len(srcs), rate), end="\r")
        print()

        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text("\n".join(outs) + "\n", encoding="utf-8")

        # An empty generation is scored as a zero rather than dropped, which is
        # correct, but a high rate of them means the prompt or the chat template is
        # wrong and the baseline is measuring a broken run. Surface it in the run
        # record instead of letting it average away into the chrF++ number.
        n_empty = sum(1 for o in outs if not o.strip())
        run.log_metric("sentences", len(outs))
        run.log_metric("empty_generations", n_empty)
        if n_empty:
            run.note("{} empty generations ({:.1%})".format(n_empty, n_empty / len(outs)))
            print("warning: {} of {} generations were empty".format(n_empty, len(outs)))

        # Devanagari in the output is a direct instruction failure -- the system
        # prompt forbids it and the task is Romanized Hinglish. Worth counting here
        # because it is one of the failure-taxonomy categories and this is the
        # cheapest place to measure it.
        n_deva = sum(1 for o in outs if any("ऀ" <= ch <= "ॿ" for ch in o))
        run.log_metric("outputs_with_devanagari", n_deva)
        if n_deva:
            run.note("{} outputs contain Devanagari despite the system prompt".format(n_deva))
            print("warning: {} of {} outputs contain Devanagari".format(n_deva, len(outs)))

        run.note("greedy decoding, {}-shot".format(args.shots))
        print("wrote {} lines -> {}".format(len(outs), args.out))


if __name__ == "__main__":
    main()
