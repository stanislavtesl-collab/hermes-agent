$ErrorActionPreference = 'Stop'

$HermesHome = 'C:\Users\Administrator\AppData\Local\hermes'
$LogDir = Join-Path $HermesHome 'logs'
$HealthLog = Join-Path $LogDir 'gateway_health.log'
$ResLog = Join-Path $LogDir 'resource_monitor.log'
$GatewayLog = Join-Path $LogDir 'gateway.log'

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Write-Log([string]$path, [string]$msg) {
  $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Add-Content -Path $path -Value ("[$ts] $msg")
}

# 1) Gateway liveness (non-invasive)
$gw = Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and $_.CommandLine -like '*hermes_cli.main gateway run*' -and
  (($_.Name -ieq 'python.exe') -or ($_.Name -ieq 'pythonw.exe'))
}

if (-not $gw -or $gw.Count -eq 0) {
  Write-Log $HealthLog 'Gateway process missing -> starting Scheduled Task Hermes_Gateway'
  schtasks /run /tn Hermes_Gateway | Out-Null
} else {
  Write-Log $HealthLog ("Gateway processes detected: {0}" -f $gw.Count)
}

# 2) Resource snapshot (Python + MT5)
$procs = Get-Process | Where-Object { $_.Name -match '^(python|pythonw|terminal64)$' }
if ($procs) {
  foreach ($p in $procs) {
    $cpu = if ($null -ne $p.CPU) { [math]::Round($p.CPU, 2) } else { 0 }
    $rssMb = [math]::Round($p.WorkingSet64 / 1MB, 1)
    Write-Log $ResLog ("PID={0} Name={1} CPU={2}s RSS={3}MB" -f $p.Id, $p.Name, $cpu, $rssMb)
  }
}
