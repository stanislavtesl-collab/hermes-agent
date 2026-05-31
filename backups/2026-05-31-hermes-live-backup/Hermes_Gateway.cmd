@echo off
setlocal EnableExtensions

cd /d C:\Users\Administrator\AppData\Local\hermes\hermes-agent
set "HERMES_HOME=C:\Users\Administrator\AppData\Local\hermes"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "VIRTUAL_ENV=C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv"
if not exist "%USERPROFILE%\.hermes" mkdir "%USERPROFILE%\.hermes"
copy /Y "%HERMES_HOME%\config.yaml" "%USERPROFILE%\.hermes\config.yaml" >nul 2>&1
copy /Y "%HERMES_HOME%\.env" "%USERPROFILE%\.hermes\.env" >nul 2>&1

REM Hard de-dup: terminate stale Hermes gateway python/pythonw before launch.
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -like '*hermes_cli.main gateway run*' -and ($_.Name -ieq 'python.exe' -or $_.Name -ieq 'pythonw.exe') }; foreach ($p in $procs) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }"

if not defined DEEPSEEK_API_KEY (
  for /f "tokens=2 delims==" %%a in ('findstr "^DEEPSEEK_API_KEY=" "%HERMES_HOME%\.env" 2^>nul') do (
    set "DEEPSEEK_API_KEY=%%a"
  )
)

if not defined NVIDIA_API_KEY (
  for /f "tokens=2 delims==" %%a in ('findstr "^NVIDIA_API_KEY=" "%HERMES_HOME%\.env" 2^>nul') do (
    set "NVIDIA_API_KEY=%%a"
  )
)

if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
  "%VIRTUAL_ENV%\Scripts\python.exe" "%HERMES_HOME%\scripts\ops_state_sync.py" > "%HERMES_HOME%\logs\ops_state_sync.log" 2>&1
)

if not exist "%HERMES_HOME%\logs" mkdir "%HERMES_HOME%\logs"
"%VIRTUAL_ENV%\Scripts\python.exe" -m hermes_cli.main gateway run >> "%HERMES_HOME%\logs\gateway-service.out.log" 2>&1
exit /b %ERRORLEVEL%
