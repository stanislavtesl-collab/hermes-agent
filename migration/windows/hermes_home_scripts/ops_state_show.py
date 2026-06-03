from pathlib import Path
import subprocess

HERMES_HOME = Path(r"C:\Users\Administrator\AppData\Local\hermes")
AGENT_HOME = HERMES_HOME / "hermes-agent"
PY = AGENT_HOME / ".venv" / "Scripts" / "python.exe"
SYNC = HERMES_HOME / "scripts" / "ops_state_sync.py"

if PY.exists() and SYNC.exists():
    out = subprocess.check_output(f'"{PY}" "{SYNC}"', shell=True, text=True)
    print(out.strip())
else:
    print("STATE_SYNC_FAIL")
    print("PRIMARY=FAIL")
    print("FALLBACKS=FAIL")
    print("CONFIG_HASH=FAIL")
    print("DAEMONS=FAIL")
    print("MONITORS=FAIL")
    print("WATCHDOGS=FAIL")
    print("MT5_LINK=FAIL")
    print("HEARTBEAT=FAIL")
    print("OPEN_ISSUES=SHOW_SCRIPT_MISSING")
