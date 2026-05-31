$ErrorActionPreference = 'Continue'
$fx = 'C:\Users\Administrator\Desktop\FxPro'
$ctl = Join-Path $fx 'gold_daemon_ctl.ps1'
$watchlog = Join-Path $fx '.gold_watchdog.log'

function WLog([string]$m) {
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Add-Content -Path $watchlog -Value "[$ts] $m"
}

if (!(Test-Path $ctl)) { WLog "ERROR: ctl missing at $ctl"; exit 1 }

try {
  $status = & powershell -NoProfile -ExecutionPolicy Bypass -File $ctl -Action status 2>&1
  $statusText = ($status | Out-String)

  $hbAge = $null
  $hbPid = $null
  if ($statusText -match 'heartbeat_age=([0-9.]+)') { $hbAge = [double]$matches[1] }
  if ($statusText -match 'heartbeat_pid=([0-9]+)') { $hbPid = [int]$matches[1] }

  $alive = $false
  if ($hbPid) {
    try { Get-Process -Id $hbPid -ErrorAction Stop | Out-Null; $alive = $true } catch { $alive = $false }
  }

  if ($hbAge -ne $null -and $hbAge -le 90 -and $alive) {
    WLog "OK: daemon alive pid=$hbPid hb_age=$hbAge"
    exit 0
  }

  WLog "WARN: stale or missing daemon (pid=$hbPid alive=$alive hb_age=$hbAge). Starting..."
  $startOut = & powershell -NoProfile -ExecutionPolicy Bypass -File $ctl -Action start 2>&1
  WLog "START_OUT: $($startOut | Out-String)"

  Start-Sleep -Seconds 5
  $verify = & powershell -NoProfile -ExecutionPolicy Bypass -File $ctl -Action status 2>&1
  WLog "VERIFY: $($verify | Out-String)"
  exit 0
} catch {
  WLog "ERROR: $($_.Exception.Message)"
  exit 1
}
