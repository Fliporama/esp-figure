# Helpers for night.ps1 (dot-source). ASCII only: PS 5.1 reads BOM-less scripts as ANSI.

function Write-Utf8([string]$Path, [string]$Text) {
    $full = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    [IO.File]::WriteAllText($full, $Text, (New-Object Text.UTF8Encoding $false))
}

function Invoke-Capped([string]$FilePath, [string[]]$ArgumentList, [string]$WorkingDirectory, [int]$TimeoutSec, [string]$LogPath) {
    # Run a process with a wall-clock cap; on timeout kill the whole process tree.
    $quoted = $ArgumentList | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $FilePath -ArgumentList $quoted -WorkingDirectory $WorkingDirectory -NoNewWindow -PassThru `
        -RedirectStandardOutput $LogPath -RedirectStandardError "$LogPath.err"
    $null = $p.Handle                      # PS 5.1: without this, ExitCode stays empty
    $timedOut = -not $p.WaitForExit([Math]::Max(1, $TimeoutSec) * 1000)
    if ($timedOut) { & taskkill /T /F /PID $p.Id *> $null; $p.WaitForExit(10000) | Out-Null }
    [pscustomobject]@{ ExitCode = $(if ($timedOut) { $null } else { $p.ExitCode }); TimedOut = $timedOut; Seconds = [int]$sw.Elapsed.TotalSeconds }
}

function Invoke-Queue([string]$QueuePath, [string]$WorktreeWsl, [int]$JobTimeoutSec, [int]$TotalTimeoutSec, [string]$LogDir,
                      [scriptblock]$Runner, [int]$MinJobSec = 60) {
    # Run each queue line (esp_figure.py arguments) one at a time; stop starting jobs when the budget is spent.
    if (-not $Runner) {
        $Runner = {
            param($jobArgs, $timeoutSec, $logPath)
            Invoke-Capped -FilePath wsl -ArgumentList (@('-d', 'Ubuntu', '-u', 'root', '--cd', $WorktreeWsl, '-e', '/root/esp-venv/bin/python', 'esp_figure.py') + $jobArgs) `
                -WorkingDirectory $LogDir -TimeoutSec $timeoutSec -LogPath $logPath
        }.GetNewClosure()
    }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $lines = @(Get-Content $QueuePath -ErrorAction SilentlyContinue | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
    foreach ($line in $lines) {
        $name = if ($line -match '--name\s+(\S+)') { $Matches[1] } else { $null }
        $left = $TotalTimeoutSec - [int]$sw.Elapsed.TotalSeconds
        $r = [pscustomobject]@{ Line = $line; Name = $name; ExitCode = $null; TimedOut = $false; Status = '' }
        if (-not $name) { $r.Status = 'bad-line' }
        elseif ($left -lt $MinJobSec) { $r.Status = 'skipped-budget' }
        else {
            $o = & $Runner ($line -split '\s+') ([Math]::Min($JobTimeoutSec, $left)) (Join-Path $LogDir "$name.log")
            $r.ExitCode = $o.ExitCode; $r.TimedOut = $o.TimedOut
            $r.Status = if ($o.TimedOut) { 'timeout' } elseif ($o.ExitCode -eq 0) { 'ok' } else { 'failed' }
        }
        Add-Content -Path (Join-Path $LogDir 'phase2.log') -Value "$($r.Name) $($r.Status) exit=$($r.ExitCode) :: $line"
        $r
    }
}

function Test-Prereqs([string]$RepoDir) {
    $msgs = @()
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { $msgs += 'claude CLI not found on PATH' }
    $tmp = Join-Path $env:TEMP 'night-prereq'
    $env:GIT_TERMINAL_PROMPT = '0'
    $g = Invoke-Capped -FilePath git -ArgumentList @('push', '--dry-run', 'origin', 'HEAD') -WorkingDirectory $RepoDir -TimeoutSec 60 -LogPath "$tmp-git.log"
    if ($g.ExitCode -ne 0) { $msgs += "git push --dry-run failed or asked for credentials (see $tmp-git.log.err)" }
    $w = Invoke-Capped -FilePath wsl -ArgumentList @('-d', 'Ubuntu', '-u', 'root', '-e', '/root/esp-venv/bin/python', '-c', 'import pyscf') `
        -WorkingDirectory $RepoDir -TimeoutSec 120 -LogPath "$tmp-wsl.log"
    if ($w.ExitCode -ne 0) { $msgs += 'WSL Python cannot import pyscf' }
    $msgs
}

function Get-StopTime([string]$StopBy, [datetime]$Now) {
    $t = $Now.Date + [timespan]$StopBy
    if ($t -le $Now) { $t = $t.AddDays(1) }
    $t
}

function Get-PhaseBudget([datetime]$Stop, [datetime]$Now) {
    # Review (phase 3, 1 h cap) must start by Stop - 1 h; phase 1 keeps a 15 min margin for phase 2.
    $untilReview = [int]($Stop.AddHours(-1) - $Now).TotalSeconds
    $p1 = [Math]::Min(10800, $untilReview - 900)
    [pscustomobject]@{
        Phase1Sec = $p1
        Phase2Sec = [Math]::Min(28800, $untilReview - $p1)
        Phase3Sec = 3600
        TooLate   = ($Stop - $Now).TotalSeconds -lt 4500
    }
}

if (-not ('NightPower' -as [type])) {
    Add-Type -Name NightPower -Namespace '' -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
}
function Set-NoSleep { [void][NightPower]::SetThreadExecutionState([uint32]'0x80000001') }   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
function Clear-NoSleep { [void][NightPower]::SetThreadExecutionState([uint32]'0x80000000') } # ES_CONTINUOUS
