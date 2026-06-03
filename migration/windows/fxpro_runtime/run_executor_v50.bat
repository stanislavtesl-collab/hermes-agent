@echo off
cd /d C:\Users\Administrator\Desktop\FxPro
set "HERMES_MT5_ACCOUNT=591712391"
set "HERMES_MT5_TERMINAL_PATH=C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
chcp 65001 >nul
title GOLD Executor V5.0
cd /d C:\Users\Administrator\Desktop\FxPro
echo === GOLD EXECUTOR V5.0 ===
echo Account: 591712391
echo.
del /f .gold_executor_v50.lock 2>nul
"C:\Program Files\Python312\python.exe" -u _gold_executor_v50.py
pause
