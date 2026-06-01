$ErrorActionPreference = "SilentlyContinue"
$python = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
$proj = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
$env:HERMES_HOME = "C:\Users\Administrator\AppData\Local\hermes"
$log = "C:\Users\Administrator\AppData\Local\hermes\logs\cron_tick_30s.log"

Set-Location $proj
"[$(Get-Date -Format s)] cron_tick_30s started" | Out-File -FilePath $log -Append -Encoding utf8

while ($true) {
  try {
    & $python -m hermes_cli.main cron tick | Out-Null
  } catch {
    "[$(Get-Date -Format s)] tick error: $($_.Exception.Message)" | Out-File -FilePath $log -Append -Encoding utf8
  }
  Start-Sleep -Seconds 30
}
