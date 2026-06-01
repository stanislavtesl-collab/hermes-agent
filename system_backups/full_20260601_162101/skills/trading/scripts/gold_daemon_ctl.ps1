param(
  [ValidateSet("status","start","stop","dedupe")]
  [string]$Action = "status"
)

$fx='C:\Users\Administrator\Desktop\FxPro'
$py='C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe'
$daemon=Join-Path $fx 'gold_manager_daemon.py'
$hb=Join-Path $fx '.gold_heartbeat.json'
$pidf=Join-Path $fx '.gold_daemon.pid'

function Get-DaemonProcs {
  Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'gold_manager_daemon\.py' }
}


function Is-PidAlive([int]$Pid) {
  try {
    Get-Process -Id $Pid -ErrorAction Stop | Out-Null
    return $true
  } catch {
    return $false
  }
}

function HeartbeatInfo {
  if(!(Test-Path $hb)){ return $null }
  try {
    $h=Get-Content $hb -Raw | ConvertFrom-Json
    $now=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $age=[math]::Round(($now - [double]$h.ts),1)
    return [pscustomobject]@{ pid=[int]$h.pid; age=$age; ticket=$h.ticket; time=$h.time }
  } catch { return $null }
}

if($Action -eq 'status'){
  $p=Get-DaemonProcs
  $h=HeartbeatInfo
  "daemon_proc_count=$($p.Count)"
  if($h){ "heartbeat_pid=$($h.pid)"; "heartbeat_age=$($h.age)"; "heartbeat_ticket=$($h.ticket)" }
  if(Test-Path $pidf){ "pid_file=$(Get-Content $pidf -Raw)" }
  $p | Select-Object ProcessId,CommandLine | Format-List
  exit 0
}

if($Action -eq 'dedupe'){
  $h=HeartbeatInfo
  $keep=$null
  if($h -and $h.age -le 120){ $keep=$h.pid }
  $procs=Get-DaemonProcs
  if(-not $keep -and $procs){ $keep=[int]($procs | Sort-Object CreationDate -Descending | Select-Object -First 1).ProcessId }
  "keep_pid=$keep"
  foreach($p in $procs){
    $id=[int]$p.ProcessId
    if($keep -and $id -eq $keep){ continue }
    try{ Stop-Process -Id $id -Force } catch{}
  }
  & $PSCommandPath -Action status
  exit 0
}

if($Action -eq 'stop'){
  foreach($p in (Get-DaemonProcs)){ try{ Stop-Process -Id ([int]$p.ProcessId) -Force } catch{} }
  'stopped'
  exit 0
}

if($Action -eq 'start'){
  if(!(Test-Path $daemon)){ throw "daemon script not found: $daemon" }
  if(!(Test-Path $py)){ throw "python not found: $py" }

  # If alive heartbeat exists, do nothing
  $h=HeartbeatInfo
  if($h -and $h.age -le 60 -and (Is-PidAlive -Pid $h.pid)){
    "already_alive_pid=$($h.pid) age=$($h.age)"
    & $PSCommandPath -Action dedupe
    exit 0
  }

  Start-Process -FilePath $py -ArgumentList @($daemon) -WorkingDirectory $fx -WindowStyle Hidden | Out-Null
  Start-Sleep -Seconds 3
  & $PSCommandPath -Action status
  exit 0
}
