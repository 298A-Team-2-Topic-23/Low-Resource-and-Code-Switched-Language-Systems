# Workbook 1 briefs — read this first

One file per member. Find yours, work only your issues, open one PR per issue.

| Member | Brief | Issues | Points |
|---|---|---|---|
| Savalia, Jenil Sanjaybhai | [jenil.md](jenil.md) | 298-32, 298-42, 298-43 | 8 |
| Shevkar, Yash | [yash.md](yash.md) | 298-34, 298-35, 298-38 | 16 |
| Singh, Prakhar Kumar | [prakhar.md](prakhar.md) | 298-37, 298-40 | 8 |
| Thomas Lnu, Shibin Biji | [shibin.md](shibin.md) | 298-33, 298-41 | 6 |
| Waghmare, Sarvesh | [sarvesh.md](sarvesh.md) | 298-36, 298-39 | 13 |

Yash carries 16 points — the heaviest load, and 298-38 is the one that cannot
slip. If he is short, 1.4/1.5 (298-34) moves to Shibin.

---

## Setup — everyone, once

```bash
git clone https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems.git
cd Low-Resource-and-Code-Switched-Language-Systems
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Check it works. All three must pass before you start:

```bash
python -m pytest tests/
python common/repro.py --selftest
python analysis/tokenizer_fertility.py --selftest
```

### Python version — check this now

```bash
python3 --version
```

**You need 3.10 or newer.** The pipeline kit uses `zip(..., strict=False)` in
three modules, which is a syntax error on 3.9 and kills the pipeline at stage 3 —
one of the four graded demo components. At least one team machine is on 3.9.6.

If you are on 3.9 and cannot upgrade before the demo, the fix is to delete
`, strict=False` from the seven call sites — `strict=False` is the default, so
removing it changes nothing:

```bash
grep -rln "strict=False" src/ | xargs sed -i '' 's/, strict=False)/)/g'
```

Confirm whoever drives the demo laptop has run the pipeline on their own machine.

---

## The workflow — this is graded individually

1. Move your issue to **In Progress today**, not when you finish
2. Branch: `<yourname>/298-XX-<short-slug>`
3. Commit: `Refs 298-XX: what you did`
4. PR body: **`Closes 298-XX`** — this line is what links the PR to Linear
5. Request a review from someone who is not you. **Nobody merges their own PR**
6. On merge, attach the PR to the issue and move it to Done

```bash
git checkout -b yash/298-38-data-pipeline
# ...work...
git add -A && git commit -m "Refs 298-38: add four-stage data pipeline"
git push -u origin yash/298-38-data-pipeline
```

**An issue is Done only when it carries a linked artifact** — a PR, a commit, a
dataset version, a run URL, or a generated report. A verbal "I did it" is not.

### Why this matters more than it sounds

Progress Report 1 scored 1/3 on Minutes because the grader checked Linear,
checked the repo, and found nothing corroborating the report. The ISA will check
both again on 8 October, in the room. The work being real is not enough — it has
to be visible on those two surfaces.

---

## Two warnings that affect everyone's sections

**Do not write that the splits are done.** Issue 298-11 is marked Done on the
board, but PR #4 was closed without merging. There is no `scripts/make_splits.py`
and no `data/processed/manifests/` on main. Splits are a *requirement*, not an
achieved fact. Section 2.5's self-assessment says so explicitly — and a grader
can disprove the opposite claim in one click.

**Do not quote 4,803 as a measured count.** `docs/datasheet.md` measured **4,799**
directly off the released file. The paper says 4,803. State both and say the
reconciliation is open. The same applies to the backbone model identifier, which
is still unverified against the official model card.

Before you submit anything, apply the one-click test to each factual claim you
make: **can a grader disprove this by clicking once?**
