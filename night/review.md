# Night phase 3: review

The coding phase and the job queue have finished. Check, report, commit. Do not write new features.

1. Run the regression checks:
   `wsl -d Ubuntu -u root --cd /mnt/c/dev/esp-night -e /root/esp-venv/bin/python night/check.py`
   and read `night/check_result.json`.
2. Read `night/logs/phase2.log`, and `runs/<name>/method.txt` for each queued job.
3. Evaluate every `sanity` entry in `night/reference.json` that applies to tonight's work.
4. Render each finished run: `... python esp_figure.py render <name>`.
5. Write `NIGHT_REPORT.md` with these sections, in this order:
   1. **Needs you**: questions from STATE "Skipped", each with your
      recommendation; package installs to approve.
   2. **Verdict**: ✅ merge / ⚠️ look first / ❌ don't merge, plus a one-line
      reason. ❌ if any regression check fails.
   3. **Checks**: a table of name, value, limit, pass/fail (regression and sanity).
   4. **Done tonight**: per item, one line that teaches the method, plus the commit hash.
   5. **Figures**: links to `night/figures/<name>/rwb_esp.png` (and the others).
      `runs/` is git-ignored, so the script copies the PNGs there after you finish.
   6. **Candidate references**: new numbers the user could add to `reference.json`.
   7. **Run info**: phase times (from `night/logs/`), anything cut short, and changed files (`git diff --stat main`).
6. Update `night/STATE.md`. Tick a roadmap box in `IMPROVEMENTS.md` **only** if
   that item's checks passed. Unvalidated items stay unticked.
7. Commit: `night: report`. Stop. The script pushes the branch.

Same file restrictions as phase 1. Be blunt about weaknesses; the user reads this first.
