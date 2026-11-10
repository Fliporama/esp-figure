# Overnight run: phase 1 code (claude) -> phase 2 compute (queue) -> phase 3 review (claude) -> push night branch.
#   powershell -ExecutionPolicy Bypass -File night\night.ps1 [-StopBy 08:00] [-DryRun] [-KillPhase1]
# Nothing runs after -StopBy. ASCII only (PS 5.1 reads BOM-less scripts as ANSI).
param([string]$StopBy = '08:00', [switch]$DryRun, [switch]$KillPhase1, [string]$Base = 'main')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib.ps1"
$repo = Split-Path $PSScriptRoot
$wt = 'C:\dev\esp-night'; $wtWsl = '/mnt/c/dev/esp-night'

$now = Get-Date
$stop = Get-StopTime $StopBy $now
$budget = Get-PhaseBudget $stop $now
if ($budget.TooLate) { Write-Host "Too late: stop time is $stop; a night needs at least 1 h 15 min (review alone needs 1 h)."; exit 1 }
$msgs = @(Test-Prereqs $repo)
if ($msgs.Count) { $msgs | ForEach-Object { Write-Host "Prerequisite failed: $_" }; exit 1 }

$branch = 'night/' + $now.ToString('yyyy-MM-dd') + $(if ($DryRun) { '-dry' } else { '' })
if (Test-Path $wt) { Write-Host "$wt already exists (an earlier night not merged/removed?). Run night\merge.ps1 or remove it."; exit 1 }
& git -C $repo rev-parse --verify --quiet "refs/heads/$branch" | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Host "Branch $branch already exists."; exit 1 }

& git -C $repo worktree add -b $branch $wt $Base
$logs = "$wt\night\logs"; New-Item -ItemType Directory -Force $logs | Out-Null
$settings = "$wt\night\settings.json"
Write-Host "Night $branch : stop at $stop"
$env:MSYS_NO_PATHCONV = '1'   # claude's Bash is Git Bash: stop it rewriting /root and /mnt paths for wsl
Set-NoSleep
try {
    Clear-NightLeftovers $wt
    Write-Utf8 "$wt\night\queue.txt" ''

    # Phase 1: code
    $p1 = 'Follow night/code.md exactly.'
    if ($DryRun) { $p1 += ' DRY RUN: do only the roadmap item "Full element colour table" (it needs no decision), then stop.' }
    $cap1 = $budget.Phase1Sec
    if ($DryRun) { $cap1 = [Math]::Min($cap1, 1800) }
    if ($KillPhase1) { $cap1 = 60 }
    $r1 = Invoke-Capped -FilePath claude -ArgumentList @('-p', $p1, '--settings', $settings, '--output-format', 'text') `
        -WorkingDirectory $wt -TimeoutSec $cap1 -LogPath "$logs\phase1.log"

    # Phase 2: compute (no tokens). Review must start by stop - 1 h.
    if ($DryRun) { Write-Utf8 "$wt\night\queue.txt" "calc O --name dry_water`n" }
    $cap2 = [Math]::Min(28800, [int]($stop.AddHours(-1) - (Get-Date)).TotalSeconds)
    $jobs = @(Invoke-Queue -QueuePath "$wt\night\queue.txt" -WorktreeWsl $wtWsl -JobTimeoutSec 14400 -TotalTimeoutSec $cap2 -LogDir $logs)

    # Phase 3: review, never past the stop time
    $cap3 = [Math]::Min(3600, [int]($stop - (Get-Date)).TotalSeconds - 120)
    $r3 = if ($cap3 -ge 300) {
        Invoke-Capped -FilePath claude -ArgumentList @('-p', 'Follow night/review.md exactly.', '--settings', $settings, '--output-format', 'text') `
            -WorkingDirectory $wt -TimeoutSec $cap3 -LogPath "$logs\phase3.log"
    } else { [pscustomobject]@{ ExitCode = $null; TimedOut = $true; Seconds = 0 } }

    # Figures: runs/ is git-ignored, so copy what the report links to
    foreach ($j in $jobs | Where-Object { $_.Status -eq 'ok' }) {
        $dst = "$wt\night\figures\$($j.Name)"; New-Item -ItemType Directory -Force $dst | Out-Null
        Copy-Item "$wt\runs\$($j.Name)\*.png", "$wt\runs\$($j.Name)\method.txt" $dst -ErrorAction SilentlyContinue
    }

    $bad = { param($r) $r.TimedOut -or $r.ExitCode -ne 0 }
    if ((& $bad $r1) -or (& $bad $r3)) {
        $tail = { param($f) if (Test-Path $f) { (Get-Content $f -Tail 40 -Encoding UTF8) -join "`n" } else { '(no log)' } }
        $summary = @(
            "# Night $branch : a phase failed (note added by night.ps1)", '',
            'A Claude phase failed, timed out or ran out of usage. Do not merge without a look.', '',
            '| Phase | Exit | Timed out | Seconds |', '|---|---|---|---|',
            "| 1 code | $($r1.ExitCode) | $($r1.TimedOut) | $($r1.Seconds) |",
            "| 3 review | $($r3.ExitCode) | $($r3.TimedOut) | $($r3.Seconds) |", '',
            '## Jobs', ($jobs | ForEach-Object { "- $($_.Name): $($_.Status) (exit $($_.ExitCode))" })) -join "`n"
        $body = @('## Phase 1 log (tail)', '```', (& $tail "$logs\phase1.log"), '```',
            '## Phase 3 log (tail)', '```', (& $tail "$logs\phase3.log"), '```') -join "`n"
        Write-FallbackReport -Path "$wt\NIGHT_REPORT.md" -Summary $summary -Body $body -Phase3Ok (-not (& $bad $r3))
    }
    & git -C $wt add -A
    & git -C $wt commit -q -m "night: logs and figures ($branch)"
    $push = Invoke-Push -RepoDir $wt -Remote origin -Branch $branch -TimeoutSec 300
    if ($push.Ok) { Write-Host "Pushed $branch. Read NIGHT_REPORT.md on that branch." }
    else { Write-Host "PUSH FAILED or timed out (see $env:TEMP\night-push.log.err). The work is local on $branch in $wt." }
} finally {
    Clear-NoSleep
}
