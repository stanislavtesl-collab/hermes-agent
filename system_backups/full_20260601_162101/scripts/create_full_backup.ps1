$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$repo = 'C:\Users\Administrator\AppData\Local\hermes\hermes-agent'
$dst = Join-Path $repo ("system_backups\full_" + $ts)
New-Item -ItemType Directory -Path $dst -Force | Out-Null

Copy-Item 'C:\Users\Administrator\AppData\Local\hermes\config.yaml' (Join-Path $dst 'config.yaml') -Force
Copy-Item 'C:\Users\Administrator\AppData\Local\hermes\.env' (Join-Path $dst '.env') -Force
Copy-Item 'C:\Users\Administrator\.hermes\config.yaml' (Join-Path $dst 'dot_hermes_config.yaml') -Force
Copy-Item 'C:\Users\Administrator\.hermes\.env' (Join-Path $dst 'dot_hermes_env') -Force

$map = @{
  'skills' = 'C:\Users\Administrator\AppData\Local\hermes\skills'
  'memories' = 'C:\Users\Administrator\AppData\Local\hermes\memories'
  'sessions' = 'C:\Users\Administrator\AppData\Local\hermes\sessions'
  'scripts' = 'C:\Users\Administrator\AppData\Local\hermes\scripts'
  'state-snapshots' = 'C:\Users\Administrator\AppData\Local\hermes\state-snapshots'
  'reports' = 'C:\Users\Administrator\AppData\Local\hermes\reports'
  'logs' = 'C:\Users\Administrator\AppData\Local\hermes\logs'
}

foreach($k in $map.Keys){
  $s = $map[$k]
  if(Test-Path $s){
    Copy-Item $s (Join-Path $dst $k) -Recurse -Force
  }
}

Write-Output ("BACKUP_DIR=" + $dst)
