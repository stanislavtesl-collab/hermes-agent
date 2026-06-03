function Invoke-HermesMemoryHousekeeper {
  try {
    $HermesHome = 'C:\Users\Administrator\AppData\Local\hermes'
    $Py = Join-Path $HermesHome 'hermes-agent\.venv\Scripts\python.exe'
    $Health = Join-Path $HermesHome 'scripts\agentmemory_healthcheck.py'
    $Housekeeper = Join-Path $HermesHome 'scripts\memory_housekeeper.py'
    if ((Test-Path $Py) -and (Test-Path $Health)) {
      & $Py $Health >> (Join-Path $HermesHome 'logs\agentmemory_health_task.out.log') 2>&1
    }
    if ((Test-Path $Py) -and (Test-Path $Housekeeper)) {
      & $Py $Housekeeper >> (Join-Path $HermesHome 'logs\memory_housekeeper_task.out.log') 2>&1
    }
  } catch {}
}
$ErrorActionPreference = "Stop"
$LogDir = "C:\Users\Administrator\AppData\Local\hermes\logs"
$UserHome = "C:\Users\Administrator"
$LocalBin = "C:\Users\Administrator\.local\bin"
$NodeExe = "C:\Users\Administrator\AppData\Local\hermes\node\node.exe"
$CliMjs = "C:\Users\Administrator\AppData\Local\hermes\node\node_modules\@agentmemory\agentmemory\dist\cli.mjs"
$env:USERPROFILE = $UserHome
$env:AGENT_ID = "hermes-trader"
$env:AGENTMEMORY_AGENT_SCOPE = "isolated"
$env:AGENTMEMORY_AUTO_COMPRESS = "false"
$env:AGENTMEMORY_SLOTS = "true"
$env:AGENTMEMORY_SUPPRESS_COST_WARNING = "1"
$env:PATH = "$LocalBin;C:\Users\Administrator\AppData\Local\hermes\node;$env:PATH"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Listening = netstat -ano | Select-String "127.0.0.1:3111|0.0.0.0:3111|\[::\]:3111"
if ($Listening) {
  "ALREADY_RUNNING " + (Get-Date).ToString("s") | Add-Content (Join-Path $LogDir "agentmemory-watchdog.log")
  Invoke-HermesMemoryHousekeeper
  exit 0
}
$Out = Join-Path $LogDir "agentmemory.out.log"
$Err = Join-Path $LogDir "agentmemory.err.log"
$p = Start-Process -FilePath $NodeExe -ArgumentList "`"$CliMjs`"" -WindowStyle Hidden -RedirectStandardOutput $Out -RedirectStandardError $Err -PassThru
try { $p.PriorityClass = "BelowNormal" } catch {}
"STARTED_NODE pid=$($p.Id) " + (Get-Date).ToString("s") | Add-Content (Join-Path $LogDir "agentmemory-watchdog.log")
Invoke-HermesMemoryHousekeeper

# Hermes OPS: also refresh memory housekeeper/health while AgentMemory watchdog is alive.
try {
  $HermesHome = 'C:\Users\Administrator\AppData\Local\hermes'
  $Py = Join-Path $HermesHome 'hermes-agent\.venv\Scripts\python.exe'
  $Housekeeper = Join-Path $HermesHome 'scripts\memory_housekeeper.py'
  if ((Test-Path $Py) -and (Test-Path $Housekeeper)) {
    & $Py $Housekeeper >> (Join-Path $HermesHome 'logs\memory_housekeeper_task.out.log') 2>&1
  }
} catch {}

