#!/usr/bin/env python3
"""Check all running terminal64.exe processes for account info.

Usage:  python scripts/check_mt5_pids.py

Uses PowerShell to enumerate actual running processes (WMIC via MSYS returns 0),
then attempts mt5.initialize() on each unique installation path to read account info.

NOTE: Only one MT5 can hold the IPC pipe at a time. If one installation is already
connected (e.g. via mt5_query.py running in the same Python process tree), later
initializes will timeout. Run this script fresh, kill lingering terminal64 instances
first if needed.
"""
import subprocess
import time
import sys
import os

# ---- Phase 1: get running PIDs and paths via PowerShell ----
ps_script = 'Get-Process terminal64 | Select-Object Id, Path, SessionId | ConvertTo-Csv -NoTypeInformation'
result = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True, timeout=10)

entries = []
for line in result.stdout.strip().split('\n')[1:]:
    parts = line.strip().strip('"').split('","')
    if len(parts) >= 3:
        pid = parts[0].strip('"')
        path = parts[1].strip('"')
        sid = parts[2].strip('"')
        if pid and path:
            entries.append({'pid': pid, 'path': path, 'session': sid})

if not entries:
    print("No terminal64.exe processes found.")
    sys.exit(0)

print(f"Found {len(entries)} terminal64.exe processes:\n")
seen = {}
for e in entries:
    key = e['path'].lower()
    if key not in seen:
        seen[key] = {'pids': [], 'sessions': set()}
    seen[key]['pids'].append(e['pid'])
    seen[key]['sessions'].add(e['session'])

for path, info in seen.items():
    pids = ', '.join(info['pids'])
    sessions = ', '.join(sorted(info['sessions']))
    print(f"  [{pids}]  session(s): {sessions}")
    print(f"         {path}")

# ---- Phase 2: probe each unique installation ----
print("\n" + "=" * 60)
print("Probing each installation for account info...")
print("=" * 60)

import MetaTrader5 as mt5

# ---- Phase 2.5: offline fallback for any install that failed ----

for path in seen:
    print(f"\n  >>> {path}")
    try:
        mt5.shutdown()
    except:
        pass
    time.sleep(0.5)

    if mt5.initialize(path=path, timeout=20000):
        acc = mt5.account_info()
        if acc:
            print(f"      ✅ Login: {acc.login}")
            print(f"         Server: {acc.server}")
            print(f"         Balance: ${acc.balance:.2f}")
            print(f"         Equity:  ${acc.equity:.2f}")
            print(f"         Currency: {acc.currency}")
        else:
            print(f"      ⚠️  No account (terminal opened but not logged in)")
        mt5.shutdown()
    else:
        err = mt5.last_error()
        ❌ Ошибка инициализации: IPC timeout

roaming = os.path.join(os.environ.get('USERPROFILE', 'C:\\\\Users\\\\Administrator'),
                       'AppData', 'Roaming', 'MetaQuotes', 'Terminal')

if os.path.isdir(roaming):
    for h in sorted(os.listdir(roaming)):
        bases_dir = os.path.join(roaming, h, "bases")
        if not os.path.isdir(bases_dir):
            continue
        for server in sorted(os.listdir(bases_dir)):
            sym_dir = os.path.join(bases_dir, server, "symbols")
            if not os.path.isdir(sym_dir):
                continue
            for f in sorted(os.listdir(sym_dir)):
                if f.startswith("symbols-") and f.endswith(".dat"):
                    login = f.replace("symbols-", "").replace(".dat", "")
                    print(f"  Terminal {h[:8]}... / {server} → login {login}")
else:
    print("  No terminal profile directory found.")

print("\nAll done.")
