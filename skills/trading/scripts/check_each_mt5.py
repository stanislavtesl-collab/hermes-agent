"""Check each running MT5 terminal by PID. Probes each unique install path."""
import MetaTrader5 as mt5
import time, os

pids_paths = [
    (3708, r"C:\Users\Administrator\Desktop\FxPro - MetaTrader 5\terminal64.exe"),
    (6348, r"C:\Program Files\Capital Point Trading MT5 Terminal\terminal64.exe"),
    (6920, r"C:\Program Files\FxPro - MetaTrader 5\terminal64.exe"),
    (7228, r"C:\Program Files\FxPro - MetaTrader 5\terminal64.exe"),
]

# First discover all running terminals dynamically
import subprocess
proc = subprocess.run(
    ['powershell', '-Command', 'Get-Process terminal64 | Select-Object Id, Path | Format-Table -AutoSize'],
    capture_output=True, text=True, timeout=10
)
print("=== Running terminals ===")
print(proc.stdout)

for pid, path in pids_paths:
    print(f"\n--- PID {pid} ---")
    print(f"    Path: {path}")
    
    if not os.path.isfile(path):
        print(f"    ❌ File not found!")
        continue
    
    try: mt5.shutdown()
    except: pass
    time.sleep(0.3)
    
    ok = mt5.initialize(path=path, timeout=20000)
    if ok:
        acc = mt5.account_info()
        if acc:
            print(f"    ✅ Login: {acc.login}")
            print(f"       Server: {acc.server}")
            print(f"       Balance: ${acc.balance:.2f}")
            print(f"       Equity: ${acc.equity:.2f}")
            print(f"       Currency: {acc.currency}")
            print(f"       Company: {acc.company}")
            print(f"       Name: {acc.name}")
        else:
            print(f"    ⚠️ No account_info")
        mt5.shutdown()
    else:
        err = mt5.last_error()
        print(f"    ❌ Error: {err}")
    time.sleep(1)
