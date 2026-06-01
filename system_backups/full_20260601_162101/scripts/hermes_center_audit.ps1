$ErrorActionPreference = "SilentlyContinue"

$root = "C:\Users\Administrator\AppData\Local\hermes"
$proj = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
$py = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"

Write-Host "===TIME==="
Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host "===CRON_LIST==="
Set-Location $proj
$env:HERMES_HOME = $root
& $py -m hermes_cli.main cron list

Write-Host "===TASKS==="
$tasks = @(
  'Hermes_Gateway',
  'Hermes_Memory_Housekeeper',
  'Hermes_Gold_State_Notify_30s',
  'Gold_Daemon_Watchdog'
)
foreach($t in $tasks){
  Write-Host ("--TASK:"+$t)
  schtasks /query /tn $t /v /fo list | Select-String -Pattern 'TaskName:|Status:|Last Run Time:|Last Result:|Task To Run:|Run As User:'
}

Write-Host "===PYTHON_PROCESSES==="
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match '^python(w)?\.exe$' } |
  Select-Object ProcessId,Name,CommandLine |
  Sort-Object ProcessId |
  Format-List

Write-Host "===MEMORY_FILES==="
Get-Item "$root\memories\MEMORY.md","$root\memories\USER.md" | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize

Write-Host "===MEMORY_HOUSEKEEPER_LOG==="
if(Test-Path "$root\logs\memory_housekeeper.log"){
  Get-Content "$root\logs\memory_housekeeper.log" -Tail 15
}

Write-Host "===NOTIFY_LOG==="
if(Test-Path "$root\logs\gold_state_notify_30s.log"){
  Get-Content "$root\logs\gold_state_notify_30s.log" -Tail 15
}

Write-Host "===ENV_MASKED==="
$envPath = "$root\.env"
if(Test-Path $envPath){
  Get-Content $envPath | ForEach-Object {
    if($_ -match '^(DEEPSEEK_API_KEY|TELEGRAM_BOT_TOKEN|OPENROUTER_API_KEY)='){
      $_ -replace '=(.+)$','=***MASKED***'
    } else {
      $_
    }
  }
}

Write-Host "===CONFIG_KEY_BLOCKS==="
$cfg = "$root\config.yaml"
if(Test-Path $cfg){
  $lines = Get-Content $cfg
  function Show-Block([string]$name){
    $start = ($lines | Select-String ('^'+$name+':') | Select-Object -First 1).LineNumber
    if($start){
      $end = ($lines | Select-String '^[A-Za-z_][A-Za-z0-9_]*:' | Where-Object { $_.LineNumber -gt $start } | Select-Object -First 1).LineNumber
      if(!$end){ $end = $lines.Count + 1 }
      Write-Host ("--"+$name+"--")
      $lines[($start-1)..($end-2)]
    }
  }
  Show-Block 'model'
  Show-Block 'fallback_providers'
  Show-Block 'openrouter'
  Show-Block 'memory'
  Show-Block 'telegram'
  Show-Block 'security'
}

Write-Host "===ORCHESTRATOR_HEAD==="
$orch = "$root\skills\trading-orchestrator\SKILL.md"
if(Test-Path $orch){
  Get-Content $orch -TotalCount 80
}

Write-Host "===AUTH_STATUS==="
& $py -m hermes_cli.main auth status openrouter
& $py -m hermes_cli.main auth status qwen-oauth

Write-Host "===SMOKE_MODELS==="
& $py -m hermes_cli.main -z 'Reply exactly: OK' --provider custom -m deepseek-chat
Write-Host ("deepseek_exit="+$LASTEXITCODE)
& $py -m hermes_cli.main -z 'Reply exactly: OK' --provider openrouter -m 'qwen/qwen3.7-max'
Write-Host ("openrouter_qwen_exit="+$LASTEXITCODE)
