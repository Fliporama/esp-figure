# Plain-assert tests for night/lib.ps1.  Run: powershell -NoProfile -File night\test_lib.ps1
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib.ps1"
function Assert($cond, $msg) { if (-not $cond) { throw "FAIL: $msg" } }
$tmp = Join-Path $env:TEMP ("night-test-" + [guid]::NewGuid()); New-Item -ItemType Directory $tmp | Out-Null

# Invoke-Capped: timeout kills the whole tree (child spawns a grandchild)
$t0 = Get-Date
$r = Invoke-Capped -FilePath powershell -ArgumentList @('-NoProfile', '-c', 'Start-Process powershell -ArgumentList ''-NoProfile'',''-c'',''Start-Sleep 60'' -NoNewWindow -Wait') `
    -WorkingDirectory $tmp -TimeoutSec 3 -LogPath "$tmp\cap.log"
Assert $r.TimedOut 'timeout flagged'
Assert ($r.Seconds -lt 10) "returned quickly ($($r.Seconds) s)"
Start-Sleep 1
$left = @(Get-Process powershell -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $PID -and $_.StartTime -gt $t0 })
Assert ($left.Count -eq 0) "no leftover child processes ($($left.Count))"

# Invoke-Capped: exit code passes through
$r = Invoke-Capped -FilePath powershell -ArgumentList @('-NoProfile', '-c', 'exit 3') -WorkingDirectory $tmp -TimeoutSec 30 -LogPath "$tmp\exit.log"
Assert ((-not $r.TimedOut) -and $r.ExitCode -eq 3) "exit code 3 (got $($r.ExitCode))"

# Invoke-Queue: blank/comment lines skipped, missing --name is bad-line, budget respected
Write-Utf8 "$tmp\queue.txt" "`n# comment`ncalc O --opt`ncalc O --name w1`ncalc O --name w2`n"
$fake = { param($jobArgs, $timeoutSec, $logPath) Start-Sleep 2; [pscustomobject]@{ ExitCode = 0; TimedOut = $false; Seconds = 2 } }
$res = @(Invoke-Queue -QueuePath "$tmp\queue.txt" -WorktreeWsl /x -JobTimeoutSec 100 -TotalTimeoutSec 3 -LogDir $tmp -Runner $fake -MinJobSec 2)
Assert ($res.Count -eq 3) "3 job lines (got $($res.Count))"
Assert ($res[0].Status -eq 'bad-line') "line without --name is bad-line (got $($res[0].Status))"
Assert ($res[1].Status -eq 'ok' -and $res[1].Name -eq 'w1') 'first valid job ok'
Assert ($res[2].Status -eq 'skipped-budget') "second job skipped once budget is used (got $($res[2].Status))"
Assert ((Get-Content "$tmp\phase2.log").Count -eq 3) 'one phase2.log line per job'

# Write-Utf8: no BOM
Write-Utf8 "$tmp\b.txt" 'Å'
$bytes = [IO.File]::ReadAllBytes("$tmp\b.txt")
Assert (-not ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB)) 'no BOM'

# Get-StopTime
$d = [datetime]'2026-11-12'
Assert ((Get-StopTime '08:00' $d.AddHours(-1)) -eq $d.AddHours(8)) '23:00 -> next day 08:00'
Assert ((Get-StopTime '08:00' $d.AddHours(1)) -eq $d.AddHours(8)) '01:00 -> same day 08:00'
Assert ((Get-StopTime '08:00' $d.AddHours(9)) -eq $d.AddDays(1).AddHours(8)) '09:00 -> next day 08:00'

# Get-PhaseBudget
$stop = $d.AddHours(8)
$b = Get-PhaseBudget $stop $d.AddHours(-1)
Assert ($b.Phase1Sec -eq 10800 -and $b.Phase2Sec -eq 18000 -and -not $b.TooLate) "23:00 budget ($($b.Phase1Sec)/$($b.Phase2Sec))"
$b = Get-PhaseBudget $stop $d.AddHours(5)
Assert ($b.Phase1Sec -eq 6300 -and $b.Phase2Sec -eq 900 -and -not $b.TooLate) "05:00 budget ($($b.Phase1Sec)/$($b.Phase2Sec))"
Assert (Get-PhaseBudget $stop $d.AddHours(6).AddMinutes(50)).TooLate '06:50 too late'

# Test-Prereqs: claude missing from PATH is reported
$savedPath = $env:PATH
$env:PATH = ($env:PATH -split ';' | Where-Object { -not (Test-Path (Join-Path $_ 'claude.exe')) }) -join ';'
$msgs = @(Test-Prereqs -RepoDir (Split-Path $PSScriptRoot))
$env:PATH = $savedPath
Assert (@($msgs | Where-Object { $_ -match 'claude' }).Count -ge 1) "claude missing reported ($msgs)"

# Clear-NightLeftovers: last night's logs/report/check result must not be read as tonight's
New-Item -ItemType Directory -Force "$tmp\wt\night\logs" | Out-Null
'x' | Set-Content "$tmp\wt\night\logs\phase2.log"; 'x' | Set-Content "$tmp\wt\NIGHT_REPORT.md"; 'x' | Set-Content "$tmp\wt\night\check_result.json"; 'x' | Set-Content "$tmp\wt\night\sanity_result.json"
Clear-NightLeftovers "$tmp\wt"
Assert (-not (Test-Path "$tmp\wt\night\logs\phase2.log") -and -not (Test-Path "$tmp\wt\NIGHT_REPORT.md") -and -not (Test-Path "$tmp\wt\night\check_result.json") -and -not (Test-Path "$tmp\wt\night\sanity_result.json")) 'leftovers cleared'
Assert (Test-Path "$tmp\wt\night\logs") 'logs dir kept'

# Write-FallbackReport: keeps the agent's report when only phase 1 failed, replaces it when phase 3 failed
Write-Utf8 "$tmp\r.md" "# agent report`nverdict"
Write-FallbackReport -Path "$tmp\r.md" -Summary 'PHASE TABLE' -Body 'LOGS' -Phase3Ok $true
$t = Get-Content "$tmp\r.md" -Raw -Encoding UTF8
Assert ($t -match 'PHASE TABLE' -and $t -match 'agent report' -and $t -notmatch 'LOGS') "agent report kept ($t)"
Write-FallbackReport -Path "$tmp\r.md" -Summary 'PHASE TABLE' -Body 'LOGS' -Phase3Ok $false
$t = Get-Content "$tmp\r.md" -Raw -Encoding UTF8
Assert ($t -match 'LOGS' -and $t -notmatch 'agent report') 'replaced when phase 3 failed'

# Invoke-Push: fails fast and reports failure (bad remote), never hangs; retries the given number of times
$p = Invoke-Push -RepoDir (Split-Path $PSScriptRoot) -Remote 'https://invalid.invalid/x.git' -Branch 'nope' -TimeoutSec 60 -Tries 1
Assert (-not $p.Ok) 'push to a bad remote reported as failed'
$p = Invoke-Push -RepoDir (Split-Path $PSScriptRoot) -Remote 'https://invalid.invalid/x.git' -Branch 'nope' -TimeoutSec 60 -Tries 2 -WaitSec 1
Assert ((-not $p.Ok) -and $p.Tries -eq 2) "failed push retried twice (tries $($p.Tries))"

# Save-NightWork: commits only the runner's outputs; half-written code (phase cut off) stays uncommitted, listed in the report
$g = "$tmp\g"; New-Item -ItemType Directory -Force "$g\night\logs" | Out-Null
& git -C $g init -q; & git -C $g config user.email 'test@example.invalid'; & git -C $g config user.name 'test'
Write-Utf8 "$g\code.py" "x = 1`n"; & git -C $g add code.py; & git -C $g commit -q -m init
Write-Utf8 "$g\code.py" "x = (`n"; Write-Utf8 "$g\new.py" "y`n"
Write-Utf8 "$g\night\logs\phase1.log" "log`n"; Write-Utf8 "$g\NIGHT_REPORT.md" "# report`n"
$left = @(Save-NightWork $g 'night: logs')
$files = @(& git -C $g show --name-only --format= HEAD)
Assert (($files -contains 'night/logs/phase1.log') -and ($files -contains 'NIGHT_REPORT.md') -and -not ($files -contains 'code.py') -and -not ($files -contains 'new.py')) "only runner files committed ($files)"
Assert ($left.Count -eq 2) "2 leftovers returned ($left)"
Assert (((& git -C $g show HEAD:NIGHT_REPORT.md) -join "`n") -match 'code\.py') 'committed report lists the leftover code'
Assert ((Get-Content "$g\code.py" -Raw) -match '\(') 'half-written code kept in the worktree, not reverted'
$left = @(Save-NightWork $g 'night: again')
Assert ($left.Count -eq 2) 'second call: nothing new to commit, no error'

# Default WSL runner: a job over its cap is killed inside WSL too (no orphan python), status timeout
Write-Utf8 "$tmp\q2.txt" "calc CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC --name slowjob --opt`n"
$res = @(Invoke-Queue -QueuePath "$tmp\q2.txt" -WorktreeWsl (Get-WslPath (Split-Path $PSScriptRoot)) -JobTimeoutSec 20 -TotalTimeoutSec 600 -LogDir $tmp -MinJobSec 1)
Assert ($res[0].Status -eq 'timeout') "slow job status timeout (got $($res[0].Status))"
$orphans = & wsl -d Ubuntu -u root -e pgrep -fc esp_figure.py   # no shell quoting: PS 5.1 mangles nested quotes
Assert ([int]$orphans -eq 0) "no orphan python in WSL ($orphans)"

Remove-Item -Recurse -Force $tmp
'ok'
