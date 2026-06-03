@echo off
cd /d C:\Users\Administrator\AppData\Local\hermes\hermes-agent
set "HERMES_HOME=C:\Users\Administrator\AppData\Local\hermes"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "VIRTUAL_ENV=C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv"
REM Load real secrets from .env on the new server, do not hard-code them here.
C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe -m hermes_cli.main gateway run
exit /b 0
