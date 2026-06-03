$ErrorActionPreference = "SilentlyContinue"
$HermesHome = "C:\Users\Administrator\AppData\Local\hermes"
$AgentDir = Join-Path $HermesHome "hermes-agent"
$FxProDir = "C:\Users\Administrator\Desktop\FxPro"
$Py = Join-Path $AgentDir ".venv\Scripts\python.exe"
Write-Host "=== HERMES_PREFLIGHT ==="
"HermesHome exists=" + (Test-Path $HermesHome)
"AgentDir exists=" + (Test-Path $AgentDir)
"Skills count=" + @((Get-ChildItem (Join-Path $HermesHome "skills") -Recurse -Filter SKILL.md -ErrorAction SilentlyContinue)).Count
"Config exists=" + (Test-Path (Join-Path $HermesHome "config.yaml"))
"Env exists=" + (Test-Path (Join-Path $AgentDir ".env"))
"Constants exists=" + (Test-Path (Join-Path $FxProDir "_hermes_constants.json"))
"MT5 terminal exists=" + (Test-Path (Join-Path $FxProDir "terminal64.exe"))
if(Test-Path $Py){ & $Py --version }
if(Test-Path (Join-Path $FxProDir "mt5_pinned_probe.py")){ & $Py (Join-Path $FxProDir "mt5_pinned_probe.py") }
Write-Host "=== DO NOT START TRADING UNTIL MT5_LINK=OK account=591712391 ==="
