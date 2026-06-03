"""
Boot script for V4.2 executor — pre-checks MT5 connectivity then starts executor.
Run this from a bat/cmd window (not from Git-Bash subprocess).
"""
import MetaTrader5 as mt5
import os, sys, time

WORKDIR = r"C:\Users\Administrator\Desktop\FxPro"
os.chdir(WORKDIR)

path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"

# Clean old locks/signals
for f in [".gold_executor_v42.lock", ".v42_trail.json", ".gold_trade_signal.json"]:
    try: os.remove(os.path.join(WORKDIR, f))
    except: pass

print("=== GOLD Executor v4.2 ===")
print("")
print("Connecting to MT5...", end=" ", flush=True)

ok = mt5.initialize(path=path, timeout=30000)
print(ok)

if ok:
    acct = mt5.account_info()
    print(f"Connected! Account: {acct.login}, Balance: ${acct.balance:.2f}")
    mt5.shutdown()
    time.sleep(1)
    print("Starting executor...")
    exec(open(os.path.join(WORKDIR, "_gold_executor_v42.py")).read())
else:
    print(f"ERROR: {mt5.last_error()}")
    print("\nTroubleshooting:")
    print("  1. Is MT5 terminal running?")
    print("  2. Is the path correct?")
    print("  3. Are you running from cmd.exe, not Git-Bash?")
    input("\nPress Enter to close...")
