import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import MetaTrader5 as mt5
from hermes_mt5_guard import initialize_and_assert, terminal_path, expected_account

out = {"terminal": terminal_path(), "expected": expected_account()}
try:
    acc = initialize_and_assert(timeout=15000)
    out.update({"ok": True, "account": int(acc.login), "balance": float(acc.balance)})
    positions = mt5.positions_get()
    out["positions"] = len(positions) if positions is not None else 0
except Exception as e:
    out.update({"ok": False, "error": str(e), "last_error": mt5.last_error()})
finally:
    try:
        mt5.shutdown()
    except Exception:
        pass
print(json.dumps(out, ensure_ascii=False))
