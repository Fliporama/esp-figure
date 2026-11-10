# Merge a reviewed night branch into main, keep its run results, remove the worktree.
#   powershell -ExecutionPolicy Bypass -File night\merge.ps1 2026-11-12 [-Dry]
# To reject a night instead: git worktree remove --force C:\dev\esp-night; git branch -D night/<date>
param([Parameter(Mandatory = $true)][string]$Date, [switch]$Dry)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot
$wt = 'C:\dev\esp-night'; $branch = "night/$Date"

$dirty = & git -C $repo status --porcelain --untracked-files=no
if ($dirty) { Write-Host "Main checkout has uncommitted changes; commit or stash them first."; exit 1 }

$steps = @(
    { & git -C $repo switch main },
    { & git -C $repo merge --no-ff $branch -m "Merge $branch" },
    { & git -C $repo push origin main },
    { if (Test-Path "$wt\runs") { Copy-Item "$wt\runs\*" "$repo\runs\" -Recurse -Force } },   # full results stay local
    { & git -C $repo worktree remove --force $wt },
    { & git -C $repo branch -d $branch }
)
foreach ($s in $steps) {
    if ($Dry) { Write-Host ('would run: ' + $s.ToString().Trim()) }
    else { & $s; if ($LASTEXITCODE) { Write-Host "Stopped: step failed: $($s.ToString().Trim())"; exit 1 } }
}
