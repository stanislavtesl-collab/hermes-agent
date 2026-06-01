$ErrorActionPreference = "Continue"
$root = "C:\Users\Administrator\AppData\Local\hermes"
$proj = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
$py = "C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
$env:HERMES_HOME = $root

Write-Host "[CHECK] Hermes Brain Fallback Hard Check (DeepSeek + OpenRouter/Qwen)"
Set-Location $proj

Write-Host "`n[1/4] Fallback chain"
& $py -m hermes_cli.main fallback list

Write-Host "`n[2/4] Env key presence"
$envFile = Join-Path $root ".env"
$hasDeepseek = $false
$hasOpenrouter = $false
if (Test-Path $envFile) {
  $hasDeepseek = [bool](Select-String -Path $envFile -Pattern '^DEEPSEEK_API_KEY=' -Quiet)
  $hasOpenrouter = [bool](Select-String -Path $envFile -Pattern '^OPENROUTER_API_KEY=' -Quiet)
}
if ($hasDeepseek) { Write-Host "PASS: DEEPSEEK_API_KEY is set" } else { Write-Host "FAIL: DEEPSEEK_API_KEY missing" }
if ($hasOpenrouter) { Write-Host "PASS: OPENROUTER_API_KEY is set" } else { Write-Host "FAIL: OPENROUTER_API_KEY missing" }

Write-Host "`n[3/4] Runtime smoke: DeepSeek"
& $py -m hermes_cli.main -z 'Reply exactly: OK' --provider custom -m deepseek-chat
$deepseekOk = $LASTEXITCODE -eq 0
if ($deepseekOk) { Write-Host "PASS: DeepSeek runtime" } else { Write-Host "FAIL: DeepSeek runtime" }

Write-Host "`n[4/4] Runtime smoke: OpenRouter Qwen"
& $py -m hermes_cli.main -z 'Reply exactly: OK' --provider openrouter -m 'qwen/qwen3.7-max'
$openrouterQwenOk = $LASTEXITCODE -eq 0
if ($openrouterQwenOk) { Write-Host "PASS: OpenRouter/Qwen runtime" } else { Write-Host "FAIL: OpenRouter/Qwen runtime" }

Write-Host "`n[RESULT]"
if ($hasDeepseek -and $hasOpenrouter -and $deepseekOk -and $openrouterQwenOk) {
  Write-Host "PASS: Dual-brain path operational (DeepSeek + Qwen via OpenRouter)"
  exit 0
}
Write-Host "FAIL: Dual-brain path not fully operational"
exit 2
