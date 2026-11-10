# Night runner: design

Status: draft for review (2026-11-11)

## Goal

On nights the user chooses, Claude Code works through the `IMPROVEMENTS.md`
roadmap on its own, on the user's laptop. It implements items, validates them
with DFT runs, and leaves a report for the morning. The user keeps their
daytime sessions for their own work.

Success:
- real roadmap progress on each night run
- nothing reaches `main` without the user's review
- a bad night costs at most a discarded branch and some usage

## Decisions (agreed in chat)

| Topic | Decision |
|---|---|
| Where | This laptop (Windows + WSL Ubuntu, PySCF venv `/root/esp-venv`), left on overnight |
| When | Only on nights the user triggers with one command (`night\night.ps1`) |
| Science decisions | Agent skips the item and asks in the report, with a recommendation; the user answers in `night/STATE.md` |
| Output | Branch `night/<YYYY-MM-DD>`, pushed to GitHub by the script; merged only by the user |
| Architecture | Three phases: code (agent) → compute (plain script) → review (agent) |

Rejected: one long agent session (fragile waiting for 1–3 h DFT jobs, 10 min
shell timeouts, polling burns tokens); interactive `/loop` (fragile, not
triggerable with one command); cloud and hybrid (laptop can stay on; cloud is
weak for long DFT jobs).

## Files

| File | Written by | Purpose |
|---|---|---|
| `night/night.ps1` | user/day session | Entry point: runs the three phases, logging, limits, push |
| `night/merge.ps1` | user/day session | `merge.ps1 <date>`: merge branch into main, push, remove worktree |
| `night/code.md` | user/day session | Phase 1 agent instructions |
| `night/review.md` | user/day session | Phase 3 agent instructions |
| `night/settings.json` | user/day session | Claude Code permissions, copied into the worktree's `.claude/` |
| `night/reference.json` | user/day session | Regression baselines and per-feature sanity checks with tolerances |
| `night/STATE.md` | agent (phase 3) + user (Answers section) | Done / skipped-awaiting-answer / next; user's answers |
| `night/queue.txt` | agent (phase 1) | One `esp_figure.py calc …` argument line per heavy job |
| `NIGHT_REPORT.md` | agent (phase 3), fallback by script | Morning report; overwritten each night |

## Flow

1. **Setup** (`night.ps1`):
   - Abort if a worktree `C:\dev\esp-night` or branch `night/<today>` already exists.
   - Create the worktree from `main` on `night/<today>` and copy `night/settings.json` to its `.claude/settings.json`.
   - Ask Windows not to sleep (`SetThreadExecutionState`, released on exit).
   - Clear `queue.txt`.
2. **Phase 1, code**: `claude -p` with `night/code.md`, `--max-turns` limit, 3 h wall-clock cap (the script kills it after that).
   - Read `night/STATE.md`, then `IMPROVEMENTS.md`.
   - Take the next unchecked roadmap item that needs no user decision and no package install. Items that need one go to STATE "Skipped" with the question and a recommendation.
   - Implement it behind a flag (defaults unchanged). Add a fast test where possible. Run the water test plus the new test.
   - A review subagent checks the diff for weakened checks, changed defaults and untested science claims; fix the findings.
   - Commit, then append heavy validation jobs to `queue.txt`.
   - At most 3 items per night.
3. **Phase 2, compute**: a PowerShell loop runs each `queue.txt` line through WSL Python, one at a time.
   - Each job: 4 h cap. Phase total: 8 h cap.
   - Logs go to `runs/<name>.log`. Every job's exit status is recorded.
   - Uses no tokens.
4. **Phase 3, review**: `claude -p` with `night/review.md` and a small `--max-turns`.
   - Run the regression checks.
   - Compare job results with `reference.json` and render the figures.
   - Write `NIGHT_REPORT.md`, update `STATE.md` (and the roadmap checkboxes for items that pass), commit.
5. **Finish** (`night.ps1`):
   - If phase 1 or 3 failed (crash, usage exhausted, timeout), the script writes a fallback `NIGHT_REPORT.md`: phases run, exit codes, log tails. Then it commits.
   - Push `night/<today>` to `origin`. Never any other branch.

## Permissions (`night/settings.json`)

Allow:
- Read, Edit and Write inside the worktree.
- Bash: `wsl -d Ubuntu -u root … /root/esp-venv/bin/python` (scripts in the repo).
- `git status|diff|log|add|commit`.
- Agent (review subagent).

Deny:
- `git push|merge|rebase|reset|checkout|switch|branch -d|-D`.
- `pip`, `apt`, network tools, WebFetch and WebSearch.
- Editing `night/*.ps1`, `night/*.md` except `STATE.md`, `night/settings.json`, `night/reference.json`, `CLAUDE.md`, `.claude/**`, and existing `test_*.py`.
- `rm` outside `runs/`.

The prompts repeat these rules, but the settings file is what enforces them.

## Validation

1. **Regression** (each night, phase 3):
   - `test_water.py` passes.
   - PAM3 single point on the stored `pam3_opt` geometry with default settings matches `reference.json`: SCF energy ±1e-6 Eh, ESP min/max ±1e-4 a.u.
   - A mismatch is reported first as a bug.
2. **Sanity per feature**: checks in `reference.json`, written in a day session and approved by the user before the night that builds the feature.
   - D3: correction < 0, |ΔE| 1–20 kcal/mol for PAM3.
   - Solvent: |ESP extrema| increase.
   - Freq: 0 imaginary modes at an optimised minimum; water frequencies within ±50 cm⁻¹ of the B3LYP/6-31G(d) reference.
   - HOMO < LUMO.
   - Charges sum to the total charge; O < 0 and amide H > 0.
   - ESP min nearest a carbonyl O, max nearest an N–H H.
   - A feature with no sanity entry yet is implemented, but reported "unvalidated", and its roadmap box stays unchecked.
3. **Candidate references**: new numbers are proposed in the report. Only the user adds them to `reference.json`.

## Morning report (`NIGHT_REPORT.md`), in order

1. **Needs you:** questions with recommendations; package installs to approve.
2. **Verdict:** ✅ merge / ⚠️ look first / ❌ don't merge, with a one-line reason.
3. **Checks table:** value, limit, pass/fail.
4. **Done tonight:** one teaching-style line per item, plus the commit.
5. **Figures:** links to the PNGs on the branch.
6. **Candidate references.**
7. **Turns, wall time per phase, anything cut short;** list of changed files.

User routine:
1. Read the report.
2. Run `night\merge.ps1 <date>`, or ignore the branch to reject it.
3. Answer questions under "Answers" in `night/STATE.md` on `main`.

## Testing the runner

`night.ps1 -DryRun`, run while the user is awake (~15 min):
- Phase 1 limited to one small item (full element colour table).
- Queue contains only the water test.
- Phase 3 as normal.
- Branch `night/<date>-dry`.

It must show:
- denied actions are blocked (attempt one `git push` and one protected edit, expect refusal)
- the push works with no password prompt
- the sleep block is set and released
- the fallback report appears when phase 1 is killed (`-DryRun -KillPhase1`)

Prerequisite checks at the top of `night.ps1`:
- `claude` is on PATH.
- `git push --dry-run` works non-interactively.
- WSL Python imports pyscf.
- Fail fast with a clear message if any check fails.

## Out of scope

- Automatic scheduling.
- Auto-merge.
- Running jobs in parallel (on 14 cores, two DFT jobs at once each take about twice as long).
- More than one review subagent per item.
- Notifications beyond the pushed branch.

## Prerequisites before the first real night

- The current conformer comparison is finished, committed and pushed.
- `pam3_opt` geometry exists for the regression baseline.
- The user has answered the stereo question (isotactic vs. syndiotactic), the first roadmap item.
- Sanity entries for the week-1 items are written and approved.
