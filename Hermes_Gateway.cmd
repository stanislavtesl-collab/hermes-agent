@echo off
setlocal EnableExtensions

cd /d C:\Users\Administrator\AppData\Local\hermes\hermes-agent
set "HERMES_HOME=C:\Users\Administrator\AppData\Local\hermes"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "VIRTUAL_ENV=C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv"

REM Prevent duplicate gateway launch (pythonw is dedicated to gateway here)
tasklist /FI "IMAGENAME eq pythonw.exe" 2>NUL | find /I "pythonw.exe" >NUL
if "%ERRORLEVEL%"=="0" exit /b 0

if not defined DEEPSEEK_API_KEY (
  for /f "tokens=2 delims==" %%a in ('findstr "^DEEPSEEK_API_KEY=" "%HERMES_HOME%\.env" 2^>nul') do (
    set "DEEPSEEK_API_KEY=%%a"
  )
)

"%VIRTUAL_ENV%\Scripts\pythonw.exe" -m hermes_cli.main gateway run
exit /b %ERRORLEVEL%
