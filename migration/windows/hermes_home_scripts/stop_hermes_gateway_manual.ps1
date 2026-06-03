$ErrorActionPreference = 'SilentlyContinue'
$HermesHome = 'C:\Users\Administrator\AppData\Local\hermes'
$Flag = Join-Path $HermesHome 'gateway_manual_stop.flag'
Set-Content -Path $Flag -Value ((Get-Date).ToString('o') + ' manual stop requested') -Encoding UTF8
schtasks /end /tn Hermes_Gateway | Out-Null
Start-Sleep -Seconds 3
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hermes_cli.main gateway run*' -and $_.Name -like 'python*' } | ForEach-Object {
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hermes_cli.main gateway run*' -and $_.Name -like 'python*' }
if($p){ 'HERMES_GATEWAY_STOP=FAIL' } else { 'HERMES_GATEWAY_STOP=OK manual_flag=' + $Flag }
