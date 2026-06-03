$ErrorActionPreference = 'SilentlyContinue'
$HermesHome = 'C:\Users\Administrator\AppData\Local\hermes'
$Flag = Join-Path $HermesHome 'gateway_manual_stop.flag'
Remove-Item $Flag -Force -ErrorAction SilentlyContinue
schtasks /run /tn Hermes_Gateway | Out-Null
Start-Sleep -Seconds 8
$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hermes_cli.main gateway run*' -and $_.Name -like 'python*' }
if($p){ 'HERMES_GATEWAY_START=OK pid_count=' + @($p).Count } else { 'HERMES_GATEWAY_START=FAIL' }
