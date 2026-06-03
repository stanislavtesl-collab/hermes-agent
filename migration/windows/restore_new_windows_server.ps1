param(
  [string]$HermesHome = "C:\Users\Administrator\AppData\Local\hermes",
  [string]$AgentRepo = "https://github.com/stanislavtesl-collab/hermes-agent.git",
  [string]$SkillsRepo = "https://github.com/stanislavtesl-collab/hermes-codex-skills.git"
)
$ErrorActionPreference = "Stop"
$AgentDir = Join-Path $HermesHome "hermes-agent"
$SkillsDir = Join-Path $HermesHome "skills"
$FxProDir = "C:\Users\Administrator\Desktop\FxPro"

New-Item -ItemType Directory -Path $HermesHome -Force | Out-Null
New-Item -ItemType Directory -Path $FxProDir -Force | Out-Null

if (!(Test-Path $AgentDir)) {
  git clone $AgentRepo $AgentDir
} else {
  Push-Location $AgentDir; git pull --ff-only; Pop-Location
}

$tmpSkills = Join-Path $HermesHome "hermes-codex-skills-sync"
if (!(Test-Path $tmpSkills)) {
  git clone $SkillsRepo $tmpSkills
} else {
  Push-Location $tmpSkills; git pull --ff-only; Pop-Location
}

if (Test-Path (Join-Path $tmpSkills "skills")) {
  robocopy (Join-Path $tmpSkills "skills") $SkillsDir /MIR /XD .git __pycache__ /XF .DS_Store | Out-Null
} else {
  robocopy $tmpSkills $SkillsDir /MIR /XD .git __pycache__ /XF .DS_Store | Out-Null
}

Copy-Item (Join-Path $AgentDir "migration\windows\config.current.yaml") (Join-Path $HermesHome "config.yaml") -Force
Copy-Item (Join-Path $AgentDir "migration\windows\_hermes_constants.example.json") (Join-Path $FxProDir "_hermes_constants.json") -Force

if (!(Test-Path (Join-Path $AgentDir ".venv"))) {
  py -3.11 -m venv (Join-Path $AgentDir ".venv")
}
& (Join-Path $AgentDir ".venv\Scripts\python.exe") -m pip install -U pip
if (Test-Path (Join-Path $AgentDir "requirements.txt")) {
  & (Join-Path $AgentDir ".venv\Scripts\python.exe") -m pip install -r (Join-Path $AgentDir "requirements.txt")
}


# Copy Hermes runtime helper scripts that are intentionally stored outside the git repo on the old server.
$MigDir = Join-Path $AgentDir "migration\windows"
if (Test-Path (Join-Path $MigDir "fxpro_runtime")) {
  robocopy (Join-Path $MigDir "fxpro_runtime") $FxProDir /E /XF .DS_Store | Out-Null
}
if (Test-Path (Join-Path $MigDir "user_scripts")) {
  robocopy (Join-Path $MigDir "user_scripts") "C:\Users\Administrator" /E /XF .DS_Store | Out-Null
}
if (Test-Path (Join-Path $MigDir "hermes_home_scripts")) {
  New-Item -ItemType Directory -Path (Join-Path $HermesHome "scripts") -Force | Out-Null
  robocopy (Join-Path $MigDir "hermes_home_scripts") (Join-Path $HermesHome "scripts") /E /XF .DS_Store | Out-Null
}
if (Test-Path (Join-Path $MigDir "gateway-service")) {
  New-Item -ItemType Directory -Path (Join-Path $HermesHome "gateway-service") -Force | Out-Null
  robocopy (Join-Path $MigDir "gateway-service") (Join-Path $HermesHome "gateway-service") /E /XF .DS_Store | Out-Null
}
Write-Host "RESTORE_BASE_OK"
Write-Host "NEXT: create $AgentDir\.env from migration\windows\env.example with real keys"
Write-Host "NEXT: install/copy FxPro MT5 terminal and login account 591712391"
Write-Host "NEXT: run migration\windows\preflight_new_server.ps1"

