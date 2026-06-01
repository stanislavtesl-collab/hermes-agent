$ErrorActionPreference = 'Continue'
$root = 'C:\Users\Administrator\AppData\Local\hermes'
$proj = 'C:\Users\Administrator\AppData\Local\hermes\hermes-agent'
$py = 'C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe'
$env:HERMES_HOME = $root
Set-Location $proj

$logDir = Join-Path $root 'logs'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path $logDir "multiagent_3tests_$stamp.log"

function Run-Test([string]$name, [string]$prompt) {
  "`n=== $name ===" | Tee-Object -FilePath $out -Append
  "PROMPT: $prompt" | Tee-Object -FilePath $out -Append
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $py -m hermes_cli.main -z $prompt 2>&1 | Tee-Object -FilePath $out -Append
  $sw.Stop()
  "DURATION_SEC=$([Math]::Round($sw.Elapsed.TotalSeconds,2))" | Tee-Object -FilePath $out -Append
}

"START_TS=$(Get-Date -Format s)" | Tee-Object -FilePath $out -Append
Run-Test 'T1_SIMPLE' 'Коротко объясни RSI в 3 пунктах без торговли и без кода.'
Run-Test 'T2_COMPLEX_MTF' 'Сделай multi-timeframe анализ XAUUSD (M5/M15/H1/H4), сравни RSI/MACD/EMA/BB, оцени риск и предложи 2 сценария входа с инвалидацией и RR.'
Run-Test 'T3_COMPLEX_POSTMORTEM' 'Сделай пост-трейд разбор: если long XAUUSD дал -0.8R, разложи причины по технике/риску/данным и дай corrective actions на следующий вход.'
"END_TS=$(Get-Date -Format s)" | Tee-Object -FilePath $out -Append
"LOG_FILE=$out"
