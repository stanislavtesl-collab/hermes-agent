@echo off
chcp 65001 >nul
title GOLD Executor v4.2
cd /d C:\Users\Administrator\Desktop\FxPro
echo === GOLD EXECUTOR v4.2 ===
echo.
del /f .gold_executor_v42.lock 2>nul
"C:\Program Files\Python312\python.exe" -c "
import MetaTrader5 as mt5
import sys
path = r'C:\Users\Administrator\Desktop\FxPro\terminal64.exe'
print('MT5 init...', end=' ')
ok = mt5.initialize(path=path, timeout=30000)
print(ok)
if ok:
    print('Connected! Account:', mt5.account_info().login)
    mt5.shutdown()
    exec(open('_gold_executor_v42.py').read())
else:
    print('Error:', mt5.last_error())
    input('Press Enter to exit...')
"
pause
