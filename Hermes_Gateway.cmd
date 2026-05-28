@echo off
REM =============================================================================
REM Hermes Gateway — Windows Startup Script
REM Launched via Scheduled Task (Hermes_Gateway) at system boot
REM =============================================================================

cd /d C:\Users\Administrator\AppData\Local\hermes\hermes-agent

REM --- Environment ---
set "HERMES_HOME=C:\Users\Administrator\AppData\Local\hermes"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "VIRTUAL_ENV=C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv"

REM --- API Key (loaded from system env or .env fallback) ---
REM Prefer system-level env var; script-level is fallback for Scheduled Tasks
if not defined DEEPSEEK_API_KEY (
    for /f "tokens=2 delims==" %%a in ('findstr "^DEEPSEEK_API_KEY=" "%~dp0.env" 2^>nul') do (
        set "DEEPSEEK_API_KEY=%%a"
    )
)

REM --- Launch Gateway (uses pythonw.exe — no console window) ---
C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\pythonw.exe -m hermes_cli.main gateway run

exit /b 0
