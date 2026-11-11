# Night phase 1: code

You are working alone overnight in a git worktree on branch `night/<date>`.
Nobody will answer questions. Work through the roadmap carefully; it's fine to do less.

## Start
1. Read `night/STATE.md` (especially **Answers**: the user's decisions), then the
   **Roadmap** section of `IMPROVEMENTS.md`, then `CLAUDE.md`.

## Loop: at most 3 items
Take the first unchecked roadmap item not already in STATE "Done".
- If it needs a scientific decision not answered in STATE Answers, or a package
  install (`pip`/`apt`), do not build it. Add it to STATE "Skipped (waiting on
  you)" with the exact question and your recommendation, and go to the next item.
- Otherwise:
  1. Implement it **behind a CLI flag**. Defaults must not change, because the
     regression check compares default output with fixed numbers.
  2. Add a fast `test_<feature>.py` (seconds to a few minutes, water or formamide) where possible.
  3. Run it, and `test_water.py`:
     `wsl -d Ubuntu -u root --cd /mnt/c/dev/esp-night -e /root/esp-venv/bin/python test_<x>.py`
  4. Dispatch one review subagent on `git diff` with this brief: "Find weakened
     checks, changed defaults, and science claims without a test. Be blunt."
     Fix what it finds.
  5. Commit: `night: <item>`.
  6. Append its heavy validation jobs to `night/queue.txt`, one per line, as
     `esp_figure.py` arguments, e.g.
     `calc CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O --name pam3_d3 --opt --d3`.
     Every line needs a unique `--name`. Never run long jobs yourself; the
     queue runs after you finish.
  7. If `night/reference.json` has no `sanity` entry for this feature, note
     "unvalidated: needs a sanity check" in STATE.

## Rules
- You may not edit: `night/*.ps1`, `night/code.md`, `night/review.md`,
  `night/settings.json`, `night/reference.json`, `night/test_check.py`, `night/check.py`, `night/baseline/`,
  `CLAUDE.md`, `test_water.py`. Never weaken a test to make it pass.
- No git push, merge, branch changes, or installs. They're blocked anyway; don't try workarounds.
- Follow CLAUDE.md: minimal code, stdlib and existing packages first, figure rules.
- Python files must stay UTF-8 (they contain Å and ·).
- Finish by updating `night/STATE.md` "Done" and "Next", then commit. Stop.
