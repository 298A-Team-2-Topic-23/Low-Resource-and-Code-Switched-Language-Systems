# GPU allocation and fallback runbook

Owner: Prakhar Kumar Singh. Issues: [298-10](https://linear.app/298a-team-2-topic-23/issue/298-10)
and [298-51](https://linear.app/298a-team-2-topic-23/issue/298-51), due 24 October 2026.
Prepared 22 October 2026. **Allocation and fallback funding remain unconfirmed.**

## Obtain a written allocation outcome

Ask the university allocation administrator to identify the team/project and confirm:

- approval or formal refusal, with the response date;
- three requested concurrent, independent single-GPU slots, or the actual lower limit;
- exact card class and VRAM, including whether at least one 40 GB-or-larger card is available;
- GPU-hour quota, validity dates, charging basis, account and access procedure;
- whether 64 GB host RAM and 500 GB scratch are available; these are requests, not confirmed specs.

No NVLink or distributed multi-GPU job is requested. A queued reservation, account
approval or a successful `nvidia-smi` alone does not establish the slot/hour quota.
Record only the non-sensitive approval summary in Linear and
`docs/COMPUTE_BUDGET.md`; keep credentials, billing details and private correspondence
outside this public repository. A response about an earlier personal lab request
does not answer the team allocation request.

If only 24 GB cards are available, record the constraint immediately. M2 already
enables gradient checkpointing, but this does not establish that M3's embedding
training fits. Profile M3 peak memory before scheduling it. If a smaller backbone
is needed, agree one common backbone for the compared arms and document the
change before collecting results.

## Fund the fallback only after approval

The planned fallback is Colab Pro+. A paid plan does not guarantee a particular
GPU, uninterrupted capacity or three concurrent slots. Google's
[resource-limit FAQ](https://research.google.com/colaboratory/faq.html#resource-limits)
describes variable GPU availability and runtime limits (checked 22 October 2026).
The [pricing page](https://colab.research.google.com/signup) requires sign-in here,
so a current account-specific price has **not** been verified.

Before purchase, the owner must review the displayed price, currency, tax,
renewal terms, compute units and expiry, and approve a spending limit. Record a
non-sensitive funding summary and the actual balance. Do not translate compute
units into GPU-hours until the assigned GPU's consumption rate is measured.
Record the quoted hourly rate, storage charges and termination controls if the
team instead approves a dedicated cloud GPU. The workbook's $2/GPU-hour is a
planning assumption, not a vendor quote. Resolve the budget discrepancy in
`COMPUTE_BUDGET.md` before authorizing full runs.

## Validate the funded runtime

Use an authorized Linux CUDA runtime. The commands below are prepared, **not GPU
validated by this change**. They use the existing trainer and preserve its recipe.
The model download and pilot also consume time/balance; approve them before running.

1. Clone a reviewed commit, then record it with the provider's job/session ID.
   Use Python 3.11 or 3.12 and install `requirements.txt` in a clean environment.
   Select a torch CUDA build compatible with the actual driver, as described in
   that file. Record `python -m pip freeze`, `python --version` and the output of:

   ```bash
   git rev-parse HEAD
   nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
   python -c 'import torch; assert torch.cuda.is_available(), "CUDA required"; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))'
   ```

   Use an A100-class supported CUDA device for the planned 40 GB route. A newer
   GPU may require different torch/bitsandbytes builds; do not claim the pinned
   environment supports an untested architecture. On a T4, the trainer must report
   fp16, not emulated bf16. Record measured VRAM instead of inferring it from a
   notebook profile name.

2. First run a bounded synthetic pilot. This proves CUDA training and adapter
   loading without staging licensed corpus data. All outputs stay under `out/`
   except the trainer/generator's normal `runs/*.json` records.

   ```bash
   python scripts/run_pipeline.py --synthetic --n-synthetic 1200 --seed 42 \
     --processed-dir out/allocation/data --manifest-dir out/allocation/manifests \
     --reports-dir out/allocation/reports --no-figures --no-run-log
   python models/train_qlora.py \
     --train out/allocation/data/synthetic/train.tsv --src-col 2 --tgt-col 4 \
     --out out/allocation/adapter --model Qwen/Qwen2.5-7B-Instruct \
     --seed 13 --limit 64 --max-steps 10 --batch-size 1 --grad-accum 32 --max-len 512
   ```

   This uses the adopted 7B backbone, NF4 double quantisation, all linear
   projections, rank 32/alpha 64 and effective batch 32. Stop on failure; preserve
   the failed run JSON and its cost. Do not silently substitute the 0.5B stand-in.

3. Confirm the adapter can be reloaded for inference. Use eight **training** rows;
   this is a functionality check, not a held-out score.

   ```bash
   python - <<'PY'
   import csv
   from pathlib import Path
   with open('out/allocation/data/synthetic/train.tsv', encoding='utf-8') as f:
       rows = list(csv.DictReader(f, delimiter='\t'))[:8]
   assert len(rows) == 8
   Path('out/allocation/input.txt').write_text(
       '\n'.join(r['english'] for r in rows) + '\n', encoding='utf-8')
   PY
   python models/generate_zeroshot.py --src out/allocation/input.txt \
     --out out/allocation/output.txt --model Qwen/Qwen2.5-7B-Instruct \
     --adapter out/allocation/adapter --shots 0 --seed 13
   python - <<'PY'
   from pathlib import Path
   p = Path('out/allocation/adapter')
   assert (p / 'adapter_config.json').exists()
   assert list(p.glob('adapter_model.*')), 'missing adapter weights'
   lines = Path('out/allocation/output.txt').read_text(encoding='utf-8').splitlines()
   assert len(lines) == 8 and all(line.strip() for line in lines)
   print('Adapter saved and reloaded; eight non-empty outputs. Synthetic pilot only.')
   PY
   python common/repro.py --summary runs/
   ```

4. Copy the adapter and new run records to persistent storage before releasing
   the runtime. Confirm the new training record says `status: ok`, seed 13,
   expected model, CUDA GPU, 10 optimizer steps, finite training loss and positive
   GPU-hours. Compare the pre/post balance or invoice to account for idle/download
   time as well: `RunLogger` is execution evidence, not the provider's bill.
   Stop/release the runtime after saving evidence.

5. A bounded synthetic pilot alone does not prove the planned real-data workload.
   After authorized access to HinGE, regenerate the splits and verify their hashes
   against `data/processed/manifests/hinge_split_manifest.json`. Run a bounded
   real-corpus pilot with the same adopted backbone and reload its adapter. Record
   actual step time and peak memory before approving the three-seed training
   schedule. Full scored M1/M2 experiments remain 298-53/298-54.

The existing [`m1_m2_colab.ipynb`](../notebooks/m1_m2_colab.ipynb) is an interactive
alternative. Set its `BRANCH` to `main` (or the reviewed commit's branch): its old
default predates the merged trainer fixes. Do not run its full `a100` profile just
to validate funding, and do not interpret the profile name as proof of an A100.

## Evidence and closure

Record the allocation response date and approved slots/card/VRAM/hours, or a formal
refusal and the funded fallback outcome. For fallback execution, link the new run
JSON, code commit, provider job/session reference, adapter reload outcome and
GPU-hours; keep billing and authentication data private. Commit the budget entry
in the same change as new run records and obtain an independent PR review.

The 22 October free-T4 0.5B synthetic run is useful prior evidence and must remain
labelled as such. Do not call it a funded fallback or a real-corpus result.
Leave 298-10 and 298-51 open until their respective acceptance criteria are met.
