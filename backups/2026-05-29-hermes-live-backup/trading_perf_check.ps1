$ErrorActionPreference = 'Continue'
$py = 'C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe'

function Run-Case($name, $cmd) {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $output = cmd /c $cmd 2>&1
  $sw.Stop()
  $ok = $LASTEXITCODE -eq 0
  [pscustomobject]@{
    name=$name
    ok=$ok
    ms=[int]$sw.ElapsedMilliseconds
    preview=($output | Select-Object -First 2) -join ' '
  }
}

$cases = @()
$cases += Run-Case 'twelvedata_quote_xauusd' "$py C:\Users\Administrator\twelvedata_query.py quote XAU/USD"
$cases += Run-Case 'twelvedata_bars_120' "$py C:\Users\Administrator\twelvedata_query.py bars XAU/USD 5min 120"
$cases += Run-Case 'analyze_pipe_twelvedata_120' "$py C:\Users\Administrator\analyze_pipe.py XAU/USD 5min 120 twelvedata"
$cases += Run-Case 'mt5_account' "$py C:\Users\Administrator\mt5_query.py account"
$cases += Run-Case 'mt5_price_xauusd' "$py C:\Users\Administrator\mt5_query.py price XAUUSD"
$cases += Run-Case 'analyze_pipe_mt5_120' "$py C:\Users\Administrator\analyze_pipe.py XAUUSD M5 120 mt5"

$cases | ConvertTo-Json -Depth 4
