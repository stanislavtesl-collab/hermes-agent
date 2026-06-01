$ErrorActionPreference = 'Stop'

$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$base = "C:\Users\Administrator\AppData\Local\hermes\backups"
$target = Join-Path $base ("live-backup-" + $stamp)
New-Item -ItemType Directory -Path $target -Force | Out-Null

function Copy-IfExists {
  param([string]$Src, [string]$DstName)
  if (Test-Path $Src) {
    Copy-Item -Path $Src -Destination (Join-Path $target $DstName) -Force
  }
}

# Core Hermes config/runtime
Copy-IfExists "C:\Users\Administrator\AppData\Local\hermes\config.yaml" "config_live_current.yaml"
Copy-IfExists "C:\Users\Administrator\AppData\Local\hermes\.env" "env_live_current.txt"
Copy-IfExists "C:\Users\Administrator\AppData\Local\hermes\gateway-service\Hermes_Gateway.cmd" "Hermes_Gateway.cmd"
Copy-IfExists "C:\Users\Administrator\AppData\Local\hermes\scripts\gateway_healthcheck.ps1" "gateway_healthcheck.ps1"
Copy-IfExists "C:\Users\Administrator\AppData\Local\hermes\scripts\gold_daemon_watchdog.ps1" "gold_daemon_watchdog.ps1"

# Trading scripts and libs
Copy-IfExists "C:\Users\Administrator\mt5_query.py" "mt5_query.py"
Copy-IfExists "C:\Users\Administrator\twelvedata_query.py" "twelvedata_query.py"
Copy-IfExists "C:\Users\Administrator\analyze_pipe.py" "analyze_pipe.py"
Copy-IfExists "C:\Users\Administrator\indicators.py" "indicators.py"

# Active GOLD daemon stack
Copy-IfExists "C:\Users\Administrator\Desktop\FxPro\gold_manager_daemon.py" "gold_manager_daemon.py"
Copy-IfExists "C:\Users\Administrator\Desktop\FxPro\gold_daemon_ctl.ps1" "gold_daemon_ctl.ps1"
Copy-IfExists "C:\Users\Administrator\Desktop\FxPro\.gold_heartbeat.json" "gold_heartbeat.json"
Copy-IfExists "C:\Users\Administrator\Desktop\_hermes_constants.json" "_hermes_constants.json"

# Skills + cron snapshots
if (Test-Path "C:\Users\Administrator\AppData\Local\hermes\skills") {
  Compress-Archive -Path "C:\Users\Administrator\AppData\Local\hermes\skills\*" -DestinationPath (Join-Path $target "skills_snapshot.zip") -Force
}
if (Test-Path "C:\Users\Administrator\AppData\Local\hermes\cron\jobs.json") {
  Copy-Item "C:\Users\Administrator\AppData\Local\hermes\cron\jobs.json" (Join-Path $target "cron_jobs.json") -Force
}

# Operational state dumps
cmd /c "tasklist /v" > (Join-Path $target "tasklist_full.txt")
cmd /c "tasklist /svc" > (Join-Path $target "tasklist_svc.txt")
cmd /c "netstat -ano" > (Join-Path $target "netstat_ano.txt")
cmd /c "netstat -ano | findstr LISTENING" > (Join-Path $target "netstat_listening.txt")
cmd /c "wmic process get ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine /format:list" > (Join-Path $target "wmic_process_full.txt")
cmd /c "schtasks /query /fo list /v" > (Join-Path $target "scheduled_tasks_full.txt")

# Focused state checks
$focus = @()
$focus += "Backup stamp: $stamp"
$focus += ""
$focus += "MT5 account check:"
try {
  $out = cmd /c "\"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe\" C:\Users\Administrator\mt5_query.py account"
  $focus += $out
} catch {
  $focus += "mt5_query.py account failed: $($_.Exception.Message)"
}
$focus += ""
$focus += "Gold daemon ctl status:"
try {
  $out2 = powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Administrator\Desktop\FxPro\gold_daemon_ctl.ps1" -Action status | Out-String
  $focus += $out2
} catch {
  $focus += "gold_daemon_ctl status failed: $($_.Exception.Message)"
}
$focus += ""
$focus += "GoldEWS task:"
try {
  $out3 = cmd /c "schtasks /query /tn GoldEWS /v /fo list"
  $focus += $out3
} catch {
  $focus += "GoldEWS query failed: $($_.Exception.Message)"
}
$focus | Set-Content -Path (Join-Path $target "focus_state.txt") -Encoding UTF8

# README
$readme = @()
$readme += "# Hermes Live Backup"
$readme += ""
$readme += "Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
$readme += "Host: MAIN (38.255.46.12)"
$readme += ""
$readme += "Includes:"
$readme += "- Live config/env + gateway scripts"
$readme += "- Trading scripts (mt5_query/twelvedata/analyze_pipe/indicators)"
$readme += "- Active GOLD daemon files"
$readme += "- Skills zip snapshot"
$readme += "- Cron/jobs/processes/tasks/network state dumps"
$readme += ""
$readme += "Note: contains operational secrets as-is by owner request."
$readme | Set-Content -Path (Join-Path $target "README.md") -Encoding UTF8

# Pack full backup folder
$zipPath = "$target.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "$target\*" -DestinationPath $zipPath -Force

Write-Output "BACKUP_DIR=$target"
Write-Output "BACKUP_ZIP=$zipPath"
