import json
import os

paths = [
    r"C:\\Program Files\\FxPro - MetaTrader 5\\terminal64.exe",
    r"C:\\Program Files\\Capital Point Trading MT5 Terminal\\terminal64.exe",
    r"C:\\Users\\Administrator\\Desktop\\FxPro\\terminal64.exe",
    r"C:\\Users\\Administrator\\Desktop\\FxPro (Atman Gibrid)\\terminal64.exe",
]

results = []
try:
    import MetaTrader5 as mt5
except Exception as e:
    print(json.dumps({"error": f"MetaTrader5 import failed: {e}"}, ensure_ascii=False))
    raise SystemExit(1)

for p in paths:
    row = {"path": p}
    if not os.path.exists(p):
        row["exists"] = False
        results.append(row)
        continue
    row["exists"] = True
    tried = []
    # try both normal and portable attach modes
    for portable in (False, True):
        item = {"portable": portable}
        ok = False
        try:
            if portable:
                ok = mt5.initialize(path=p, portable=True)
            else:
                ok = mt5.initialize(path=p)
            item["init_ok"] = bool(ok)
            if ok:
                ai = mt5.account_info()
                ti = mt5.terminal_info()
                if ai is not None:
                    item["login"] = int(ai.login)
                    item["server"] = str(ai.server)
                    item["name"] = str(ai.name)
                else:
                    item["login"] = None
                if ti is not None:
                    item["connected"] = bool(ti.connected)
                    item["trade_allowed"] = bool(getattr(ti, "trade_allowed", False))
                last_err = mt5.last_error()
                item["last_error"] = last_err
            else:
                item["last_error"] = mt5.last_error()
        except Exception as e:
            item["exception"] = str(e)
        finally:
            try:
                mt5.shutdown()
            except Exception:
                pass
        tried.append(item)
    row["tries"] = tried
    results.append(row)

print(json.dumps(results, ensure_ascii=False, indent=2))
