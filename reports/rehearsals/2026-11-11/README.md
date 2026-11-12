# Fresh-clone dry run of the no-GPU demo — 11 November 2026

Issue [298-85](https://linear.app/298a-team-2-topic-23/issue/298-85). Run by Singh.
**A dry run, not the 298-85 rehearsals.** Those are due 1 December, on team machines, timed from
`git clone` to the last slide. This exercised the demo path that exists today, with
`scripts/rehearse_demo.py`, to find what breaks before the end-of-term demo is built on it.

The path rehearsed is the one the team gives if the GPU never arrives (Phase 3 README, "The honest
fallback"): tests, the reproducibility and tokenizer self-tests, the four-stage pipeline into the
SQLite warehouse with monitoring, stage samples, the code-mixing generator, the evaluation harness,
the GPU-hour roll-up and the section 4.2 diagrams. No model outputs: none exist on real data.

## Conditions

| | Clone 1 | Clone 2 |
|---|---|---|
| Commit | `5429ad3` (298-73 before its test fixture fix; amended to `ab8821c`) | `6da38f6` (with both fixes below) |
| Clone | `git clone` into an empty temporary directory | same |
| Dependencies | `requirements-demo.txt` into a new venv, network on, cold: 339.5 s | same, warm pip cache: 5.2 s |
| Demo steps | network **off** (`unshare -rn`), `HF_HUB_OFFLINE=1`, `PIP_NO_INDEX=1` | same |
| Machine | Linux x86_64 sandbox, Python 3.13.18 | same |
| Demo steps, total | 21.6 s | 16.1 s |

## What broke

**Clone 1 found two problems. Clone 2, after the fixes, found none.**

1. **The demo overwrote committed evidence.** `make demo-298-70` ran the synthetic pipeline with
   the default output paths, so it replaced the real-HinGE `reports/data_statistics.json`
   (4,799 records) with a 1,200-row synthetic run, and also rewrote figures 1–4 and
   `reports/pipeline_monitor.json`. Anyone who commits after giving the demo would replace
   section 3.6's evidence with synthetic numbers, and nothing on screen would say so.
   *Fixed* in the `Makefile` (commit `0dd70f9`, also on its own branch for 298-70's owner): the
   demo writes to `out/demo/`, which is gitignored, and the monitor compares against the committed
   real baseline. *Until that merges:* after any demo, run `git checkout -- reports/` before
   committing.
2. **Twelve new 298-73 tests errored offline.** Their throwaway git repository inherited the
   machine's global git config, here a commit-signing service that cannot be reached with the
   network off. A laptop with commit signing or hooks configured would fail the same way.
   *Fixed* in `tests/test_run_contract.py`: the fixture ignores global and system git config.

Clone 2 also confirmed that no step reaches the network and that no tracked file changes.

## What this does not show

- Both runs were on one Linux sandbox, not on two team machines. macOS has no `unshare`, so on a
  team laptop the driver reports networking as **on** and Wi-Fi has to be turned off by hand.
- No slides, no speaking order, no presenter: the steps are timed, not the talk.
- The clone source was a local checkout of the branch, because the branch is not yet on GitHub.
  The 1 December rehearsals should clone from GitHub: `--source <repo URL> --ref <commit>`.
- Clone 2's install was warm. A cold install took 5.7 minutes here; budget for it, or install the
  night before.

298-85 stays open.

## Files

- `clone-1.json`, `clone-2.json`: commit, conditions, per-step exit code and seconds, what broke
- `clone-1/`, `clone-2/`: one log per step

Re-run: `python scripts/rehearse_demo.py --label clone-1` (add `--source` and `--ref` for a GitHub
clone).
