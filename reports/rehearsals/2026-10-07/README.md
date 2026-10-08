# Automated preflight evidence — 7 October 2026

Issue 298-40. **Synthetic CPU checks only; full team / real-corpus rehearsals remain pending.**

Both attempts used separate fresh remote clones of `jenil/298-38-data-pipeline` at
`b7494e5a7db52008fa20bb3c83df9fa76c9b1144`. They used a shared Python 3.11.14
CPU environment, not two machines or fresh full training-stack installations.
Package versions and UTC execution timestamps are in [preflight.json](preflight.json).
UTC timestamps on 8 October correspond to the evening of 7 October in America/Los_Angeles.

| Check | Fresh clone 1 | Fresh clone 2 |
|---|---|---|
| pytest | exit 0, 2.719 s | exit 0, 2.562 s |
| Repro self-test | exit 0, 0.188 s | exit 0, 0.165 s |
| Fertility self-test | exit 0, 0.034 s | exit 0, 0.034 s |
| Synthetic four-stage pipeline | exit 0, 1.765 s | exit 0, 1.829 s |

Both suites: **21 tests passed**, with one matplotlib/pyparsing deprecation warning.
Both pipeline runs: 1,200 ingested → 1,004 kept; train/dev/test **801/100/103**.
Both produced all four figures and passed the leakage gate with zero exact and
near overlaps. Input SHA-256 and all three split TSV SHA-256 values matched.
Timing includes the Python subprocess; it excludes cloning, environment setup
and any presentation. No recording, team speech, backup machine or real data run is evidenced.

The isolated injected-overlap drill returned **exit 3** and wrote no manifest
directory. Its diagnostic output is in [leakage-gate.log](leakage-gate.log).

Logs:
- [clone-1-fertility-selftest.log](clone-1-fertility-selftest.log)
- [clone-1-pipeline.log](clone-1-pipeline.log)
- [clone-1-repro-selftest.log](clone-1-repro-selftest.log)
- [clone-1-tests.log](clone-1-tests.log)
- [clone-2-fertility-selftest.log](clone-2-fertility-selftest.log)
- [clone-2-pipeline.log](clone-2-pipeline.log)
- [clone-2-repro-selftest.log](clone-2-repro-selftest.log)
- [clone-2-tests.log](clone-2-tests.log)

Completion checklist and proposed speaking order: [DEMO_RUNBOOK.md](../../../DEMO_RUNBOOK.md).
Pipeline implementation is owned by 298-38 and is not copied into this PR.
