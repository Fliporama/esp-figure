# Night Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command (`night\night.ps1`) that, overnight, has Claude Code implement roadmap items on a night branch, runs the heavy DFT jobs with a plain script, reviews the results against fixed references, and pushes a branch with a morning report.

**Architecture:** A PowerShell orchestrator (`night.ps1`) with helper functions in `night/lib.ps1` runs three phases in a git worktree: phase 1 `claude -p` (code), phase 2 a plain queue runner (compute, 0 tokens), phase 3 `claude -p` (review). The orchestrator also handles limits, the sleep block, the fallback report and the push. A Python checker (`night/check.py`) does the regression comparison against `night/reference.json`, so phase 3 reports numbers it didn't choose.

**Tech Stack:** Windows PowerShell 5.1, Claude Code CLI (`C:\Users\t14sg\.local\bin\claude.exe`), git worktrees, WSL Ubuntu with `/root/esp-venv` (Python 3.14, PySCF 2.15), existing `esp_figure.py`.

**Spec:** `docs/superpowers/specs/2026-11-11-night-runner-design.md`

## Global Constraints

- Branch name `night/<YYYY-MM-DD>`; dry runs use `night/<YYYY-MM-DD>-dry`. The script pushes **only** that branch.
- Worktree path `C:\dev\esp-night` (WSL: `/mnt/c/dev/esp-night`). Abort if it or the branch already exists.
- Caps: phase 1 3 h wall clock; each job 4 h; phase 2 total 8 h. Phase 3: 1 h wall clock.
- **Hard stop (added 2026-11-11, user request):** `-StopBy <HH:mm>`, default `08:00`. Nothing runs after it. Phase 3 must start by StopBy − 1 h. Phase 2 starts no job after that point and kills any running job then. Phase 1 cap = min(3 h, time left before that point). At StopBy everything still running is killed, then the fallback report is written and the branch pushed. Refuse to start if less than 1 h 15 min remains.
- **Deviation from spec:** the installed CLI has no `--max-turns`. Wall-clock caps plus "at most 3 items" in `code.md` replace it.
- **Deviation from spec:** permissions load via `claude --settings night/settings.json` rather than copying the file into the worktree's `.claude/`. Same effect, one less copy step.
- At most 3 roadmap items per night; new behaviour behind flags, defaults unchanged.
- Regression tolerances: SCF energy ±1e-6 Eh; ESP min/max ±1e-4 a.u.
- WSL call form (no `bash -c`): `wsl -d Ubuntu -u root --cd <wsl path> -e /root/esp-venv/bin/python <script> <args>`.
- Files written by PowerShell must be UTF-8 **without BOM** (`[IO.File]::WriteAllText(path, text, (New-Object Text.UTF8Encoding $false))`). PS 5.1 `Set-Content -Encoding utf8` adds a BOM.
- No new dependencies (no Pester tests: the installed Pester 3.4 is too old; plain-assert test scripts instead).

## Review Focus

1. **Python as an escape hatch:** the agent may run WSL Python, and Python can do anything (pip, network, `rm`). The settings file can't close this. Residual risk is accepted, contained by the worktree, the branch-only push and the morning review. Task 2 pins the allow rule to `esp_figure.py` and `test_*.py` prefixes, and the dry run confirms a bare `python -c` is refused.
2. **Permission path rules don't match** (relative-path semantics of `--settings` deny rules): the protected-file edit must actually be refused. Task 5 attempts one and expects refusal.
3. **Killed `claude` leaves child processes** (node, wsl) running into phase 2 and competing for CPU. `Invoke-Capped` kills the process tree (`taskkill /T /F`). Test in Task 3.
4. **Malformed or empty `queue.txt`** (blank lines, comments, a missing `--name`): blank and `#` lines are skipped, and a line without `--name` is recorded as failed with no crash. Test in Task 3.
5. **Git push asks for credentials at 2 AM and hangs:** the prerequisite check runs `git push --dry-run` with `GIT_TERMINAL_PROMPT=0` and fails fast. Test in Task 3.

---

### Task 1: Regression checker and reference file

**Files:**
- Create: `night/reference.json`, `night/check.py`, `night/test_check.py`

**Interfaces:**
- Consumes: `esp_figure.calc(spec, name, ..., root=...)`, `esp_figure.read_xyz`; `runs/pam3_opt/mol.xyz` (exists once the running comparison finishes; blocking for Step 5 only).
- Produces: `python night/check.py [--ref night/reference.json] [--out night/check_result.json]`. Exit 0 if all pass, 1 otherwise. Writes `{"checks": [{"name", "value", "expected", "tol", "pass"}], "all_pass": bool}`.

`reference.json` schema:
```json
{"regression": {
   "water_test": {"cmd": "test_water.py"},
   "pam3_sp": {"xyz": "night/baseline/pam3_opt.xyz",
               "scf_energy": {"value": null, "tol": 1e-6},
               "esp_min": {"value": null, "tol": 1e-4},
               "esp_max": {"value": null, "tol": 1e-4}}},
 "sanity": {}}
```

- [ ] **Step 1: Write `night/test_check.py`.** It runs `check.py` against a temp reference with a correct water-energy entry and expects exit 0. It edits the value by 1e-3 and expects exit 1, with that check showing `"pass": false`. Then it checks that a `null` value counts as a failure with `"expected": null`. Use water (`calc("O", ...)`) as the molecule so the test runs in seconds. `check.py` must accept any `xyz` entry, not just PAM3.
- [ ] **Step 2: Run it.** `wsl -d Ubuntu -u root --cd "/mnt/c/dev/molcule visualizer" -e /root/esp-venv/bin/python night/test_check.py`. Expected: FAIL (no `check.py`).
- [ ] **Step 3: Implement `night/check.py`.** For each `regression` entry: `cmd` entries run as a subprocess (pass = exit 0); `xyz` entries call `calc(<xyz>, name, root=<tempdir>)` (single point, default settings) and read the energy and ESP range back from its `method.txt` lines `SCF energy:` and `ESP range on surface:`. Compare with `abs(value - expected) <= tol`. Write the result JSON, then exit.
- [ ] **Step 4: Run the test.** Same command. Expected: `ok`.
- [ ] **Step 5: Fill in the PAM3 baseline** (after `pam3_opt` finishes). Copy `runs/pam3_opt/mol.xyz` to `night/baseline/pam3_opt.xyz`. Run `check.py` once to get the values, write them into `reference.json` and rerun. Expected: exit 0, all pass. (The baseline is the default-settings single point on that geometry, not the opt run's own numbers.)
- [ ] **Step 6: Commit.** `git add night/reference.json night/check.py night/test_check.py night/baseline/ && git commit -m "night: regression checker and baseline"`

### Task 2: Agent permissions and instructions

**Files:**
- Create: `night/settings.json`, `night/code.md`, `night/review.md`, `night/STATE.md`

**Interfaces:**
- Consumes: `night/check.py` (Task 1) and its result JSON; `night/queue.txt` line format (below).
- Produces: `queue.txt` format, one job per line: `esp_figure.py` arguments, e.g. `calc CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O --name pam3_d3 --opt --d3`; `#` comments and blank lines allowed; `--name` required. `STATE.md` sections: `## Done`, `## Skipped (waiting on you)`, `## Next`, `## Answers` (user writes here).

- [ ] **Step 1: Write `night/settings.json`.**
  - `permissions.allow`: `Read`, `Edit`, `Write`, `Agent`, `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git add:*)`, `Bash(git commit:*)`, `Bash(wsl -d Ubuntu -u root --cd /mnt/c/dev/esp-night -e /root/esp-venv/bin/python esp_figure.py:*)`, `Bash(wsl -d Ubuntu -u root --cd /mnt/c/dev/esp-night -e /root/esp-venv/bin/python test_:*)`, `Bash(wsl -d Ubuntu -u root --cd /mnt/c/dev/esp-night -e /root/esp-venv/bin/python night/check.py:*)`.
  - `permissions.deny`: `Bash(git push:*)`, `Bash(git merge:*)`, `Bash(git rebase:*)`, `Bash(git reset:*)`, `Bash(git checkout:*)`, `Bash(git switch:*)`, `Bash(git branch:*)`, `Bash(pip:*)`, `Bash(apt:*)`, `Bash(curl:*)`, `WebFetch`, `WebSearch`, `Edit(night/*.ps1)`, `Edit(night/code.md)`, `Edit(night/review.md)`, `Edit(night/settings.json)`, `Edit(night/reference.json)`, `Edit(CLAUDE.md)`, `Edit(.claude/**)`, `Edit(test_water.py)`, `Edit(night/test_check.py)`, plus the same paths for `Write`.
  - `"defaultMode": "default"`, so anything not allowed is refused in `-p` mode.
- [ ] **Step 2: Write `night/code.md`** (phase 1 instructions). Contents, in order:
  - Read `night/STATE.md` (including Answers), then the Roadmap in `IMPROVEMENTS.md`.
  - Loop at most 3 times: take the first unchecked item. If it needs a user decision or a package install, add it to STATE "Skipped" with the question and a recommendation, and move on. Otherwise:
    - implement it behind a CLI flag (defaults unchanged)
    - add a fast `test_<feature>.py` where possible, run it and `test_water.py`
    - dispatch one review subagent on `git diff` with the brief "weakened checks, changed defaults, untested science claims"
    - fix the findings, commit `night: <item>`
    - append its validation jobs to `night/queue.txt`
  - A feature with no `sanity` entry in `reference.json` is still built, but marked "unvalidated" in STATE.
  - Never edit protected files; never wait on long jobs (queue them instead).
  - Follow CLAUDE.md working preferences (explain the method; minimal code).
- [ ] **Step 3: Write `night/review.md`** (phase 3 instructions):
  - Run `night/check.py` and read `night/phase2.log` plus each `runs/<name>/method.txt`.
  - Evaluate any `sanity` entries that apply. Render the new runs (`esp_figure.py render <name>`).
  - Write `NIGHT_REPORT.md` with the spec's seven sections, in order. Verdict ❌ if any regression check fails.
  - Update STATE (Done / Skipped / Next) and tick roadmap boxes **only** for items whose checks pass. Commit `night: report`.
- [ ] **Step 4: Write `night/STATE.md`** with the four empty sections. Pre-fill Skipped with the stereo question (isotactic vs. syndiotactic; recommend syndiotactic as closer to free-radical PAM, caption states the choice). If you answer it in Answers before the first night, that night does it.
- [ ] **Step 5: Validate the JSON.** `wsl ... python -c "import json; json.load(open('night/settings.json'))"`. Expected: no error. (Whether the permissions behave is tested in Task 5.)
- [ ] **Step 6: Commit.** `git add night/settings.json night/code.md night/review.md night/STATE.md && git commit -m "night: agent permissions and instructions"`

### Task 3: Orchestrator helpers

**Files:**
- Create: `night/lib.ps1`, `night/test_lib.ps1`

**Interfaces:**
- Produces (all in `night/lib.ps1`, dot-sourced):
  - `Test-Prereqs -RepoDir <string>` → `[string[]]` of failure messages (empty = ok). Checks: `claude` on PATH; `git push --dry-run` with `$env:GIT_TERMINAL_PROMPT='0'` exits 0; WSL Python `-c "import pyscf"` exits 0.
  - `Invoke-Capped -FilePath <string> -ArgumentList <string[]> -WorkingDirectory <string> -TimeoutSec <int> -LogPath <string>` → `[pscustomobject]@{ExitCode=<int|null>; TimedOut=<bool>; Seconds=<int>}`. Start-Process with stdout/stderr redirected to `LogPath`/`LogPath.err`; on timeout `taskkill /T /F /PID`.
  - `Invoke-Queue -QueuePath <string> -WorktreeWsl <string> -JobTimeoutSec <int> -TotalTimeoutSec <int> -LogDir <string>` → `[pscustomobject[]]` with `Line`, `Name`, `ExitCode`, `TimedOut`, `Status` (`ok|failed|timeout|skipped-budget|bad-line`).
  - `Write-Utf8 -Path <string> -Text <string>` (no BOM).
  - `Get-StopTime -StopBy <string 'HH:mm'> -Now <datetime>` → `[datetime]`: today at StopBy if that is later than `Now`, otherwise tomorrow at StopBy.
  - `Get-PhaseBudget -Stop <datetime> -Now <datetime>` → `[pscustomobject]@{Phase1Sec; Phase2Sec; Phase3Sec; TooLate}`. Phase3Sec = 3600; review must start at `Stop - 1h`; Phase1Sec = min(10800, seconds until review start − 900); Phase2Sec = min(28800, seconds until review start − Phase1Sec); `TooLate` when seconds until Stop < 4500.
  - `Set-NoSleep` / `Clear-NoSleep` via `SetThreadExecutionState` (`0x80000001` on, `0x80000000` off).

- [ ] **Step 1: Write `night/test_lib.ps1`** (plain `if (-not ...) { throw }` asserts):
  - `Invoke-Capped` running `powershell -c "Start-Sleep 30"` with `TimeoutSec 2` → `TimedOut` true, `Seconds` < 10, and no leftover child `powershell` with that start time.
  - A job running `powershell -c "exit 3"` → `ExitCode` 3, `TimedOut` false.
  - `Invoke-Queue` on a temp queue with a blank line, a `# comment`, a line without `--name` and one valid line → statuses `bad-line` and one other entry (blank and comment lines skipped). Use a `-Runner` scriptblock parameter on `Invoke-Queue` (default: the WSL call) so the test substitutes a fake runner.
  - `Write-Utf8` output's first 3 bytes are not `EF BB BF`.
  - `Test-Prereqs` with `$env:PATH` stripped of the claude directory → returns a message containing `claude`.
  - `Get-StopTime '08:00'` with Now 23:00 on day D → D+1 08:00; with Now 01:00 → same day 08:00; with Now 09:00 → next day 08:00.
  - `Get-PhaseBudget` with Now 23:00, Stop 08:00 → Phase1Sec 10800, Phase2Sec 18000 (5 h, from 02:00 to 07:00), TooLate false. With Now 06:50 → TooLate true. With Now 05:00 → Phase1Sec 6300 (from 05:00 to 06:45), Phase2Sec 900, TooLate false.
- [ ] **Step 2: Run it.** `powershell -NoProfile -File night\test_lib.ps1`. Expected: FAIL (no `lib.ps1`).
- [ ] **Step 3: Implement `night/lib.ps1`** with the signatures above. `Invoke-Queue` parses `--name <x>` with a regex, stops starting new jobs once `TotalTimeoutSec` is used up (remaining lines → `skipped-budget`), and appends one summary line per job to `<LogDir>/phase2.log`.
- [ ] **Step 4: Run the test.** Same command. Expected: `ok`, exit 0.
- [ ] **Step 5: Commit.** `git add night/lib.ps1 night/test_lib.ps1 && git commit -m "night: orchestrator helpers"`

### Task 4: Orchestrator and merge script

**Files:**
- Create: `night/night.ps1`, `night/merge.ps1`

**Interfaces:**
- Consumes: everything in `night/lib.ps1` (Task 3); `night/code.md`, `night/review.md`, `night/settings.json` (Task 2).
- Produces: `night\night.ps1 [-StopBy 08:00] [-DryRun] [-KillPhase1]`; `night\merge.ps1 <YYYY-MM-DD> [-Dry]`.

- [ ] **Step 1: Implement `night/night.ps1`**, in order:
  0. `Get-StopTime` + `Get-PhaseBudget`; if `TooLate`, print the stop time and how much time is needed, then exit 1. Phase caps below are the **minimum** of the fixed cap and the budget. A final guard: if the clock passes Stop during any phase, kill it (`Invoke-Capped` timeout already covers this, since its timeout is computed from Stop).
  1. `Test-Prereqs`; exit 1 with the messages if any.
  2. Branch name (`-dry` suffix for `-DryRun`); abort if the worktree path or branch exists.
  3. `git worktree add -b <branch> C:\dev\esp-night main`; `Set-NoSleep`.
  4. Phase 1: `Invoke-Capped claude -p "Follow night/code.md exactly." --settings night/settings.json --output-format text` in the worktree, 3 h (`-DryRun`: prompt adds "Do only the item 'Full element colour table'", cap 30 min; `-KillPhase1`: cap 60 s).
  5. Phase 2: `Invoke-Queue` (4 h / 8 h caps; `-DryRun` overwrites the queue with one job `calc O --name dry_water`).
  6. Phase 3: `Invoke-Capped claude -p "Follow night/review.md exactly."`, 1 h cap.
  7. If phase 1 or 3 had `TimedOut` or a nonzero exit, write a fallback `NIGHT_REPORT.md`: phase table (exit, timed out, seconds), last 40 lines of each log, and the queue results. Then `git -C <wt> add -A; git commit -m "night: fallback report"`.
  8. `git -C <wt> push -u origin <branch>`. In `finally`: `Clear-NoSleep`. All phase logs go to `<wt>\night\logs\`.
- [ ] **Step 2: Implement `night/merge.ps1`.**
  - Merge `night/<date>` into `main` in the main repo (`--no-ff`) and push `main`.
  - Run `git worktree remove C:\dev\esp-night` and delete the local branch.
  - `-Dry` prints the commands without running them.
- [ ] **Step 3: Check that both scripts parse.** `powershell -NoProfile -Command "$null = [ScriptBlock]::Create((Get-Content night\night.ps1 -Raw)); $null = [ScriptBlock]::Create((Get-Content night\merge.ps1 -Raw)); 'parsed'"`. Expected: `parsed`.
- [ ] **Step 4: Commit.** `git add night/night.ps1 night/merge.ps1 && git commit -m "night: orchestrator and merge script"`

### Task 5: Dry runs (end-to-end acceptance)

**Files:**
- Modify: whatever the dry runs show to be broken
- Modify: `CLAUDE.md` (add a short "Night runner" section: how to trigger, review, merge)

- [ ] **Step 1: Push `main` with Tasks 1–4.** The worktree branches from local `main`, but the night branch is pushed to `origin`.
- [ ] **Step 2: Kill-test.** Run `night\night.ps1 -DryRun -KillPhase1`. Expected: phase 1 is killed at 60 s; no `claude`/`node` child processes remain (`Get-Process`); `NIGHT_REPORT.md` is the fallback version; branch `night/<date>-dry` is on GitHub. Then clean up with `git worktree remove C:\dev\esp-night --force`, delete the branch locally and on `origin`.
- [ ] **Step 3: Full dry run.** Run `night\night.ps1 -DryRun`. Expected:
  - the colour-table commit is on the branch
  - `phase2.log` shows `dry_water ok`
  - `NIGHT_REPORT.md` has all seven sections and regression checks pass
  - the branch is pushed
  - `powercfg /requests` showed the script during the run and doesn't after it
- [ ] **Step 4: Permission probes.** In the dry-run worktree run `claude -p "Try: (1) git push, (2) edit night/reference.json, (3) run python -c 'print(1)' via the WSL venv. Report which were refused." --settings night/settings.json`. Expected: all three refused. If (2) succeeds, fix the path syntax of the deny rules (Review Focus 2) and repeat.
- [ ] **Step 5: Test the merge script.** Run `night\merge.ps1 <date>-dry -Dry` and check the printed commands. Then remove the dry worktree and branch without merging.
- [ ] **Step 6: Commit.** Add the CLAUDE.md "Night runner" section and any fixes, then `git commit -m "night: dry-run fixes and docs"` and push.
