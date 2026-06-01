$ErrorActionPreference = "SilentlyContinue"
$python = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
$proj = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
$reader = "C:\Users\Administrator\AppData\Local\hermes\scripts\gold_state_reader.py"
$env:HERMES_HOME = "C:\Users\Administrator\AppData\Local\hermes"
$target = "telegram:534151570"
$log = "C:\Users\Administrator\AppData\Local\hermes\logs\gold_state_notify_30s.log"

Set-Location $proj
"[$(Get-Date -Format s)] gold_state_notify_30s started" | Out-File -FilePath $log -Append -Encoding utf8

while ($true) {
  try {
    $msg = & $python $reader
    $out = ($msg -join "`n").Trim()

    if ($out -and $out -ne "SAME" -and $out -ne "NO_STATE_FILE") {
      & $python -m hermes_cli.main send --to $target $out | Out-Null
      "[$(Get-Date -Format s)] sent: $($out.Split("`n")[0])" | Out-File -FilePath $log -Append -Encoding utf8
    }
  } catch {
    "[$(Get-Date -Format s)] error: $($_.Exception.Message)" | Out-File -FilePath $log -Append -Encoding utf8
  }

  Start-Sleep -Seconds 30
}
