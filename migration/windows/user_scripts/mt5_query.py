#!/usr/bin/env python3
"""MT5 query tool."""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False))


def _safe_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _read_env_key_from_file(path, key):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip("'\"")
    except Exception:
        return ""
    return ""


def _resolve_env_key(name):
    val = os.getenv(name, "").strip()
    if val:
        return val
    candidates = [
        r"C:\Users\Administrator\AppData\Local\hermes\.env",
        os.path.join(os.path.dirname(__file__), ".env"),
    ]
    for path in candidates:
        v = _read_env_key_from_file(path, name)
        if v:
            return v
    return ""


def _running_terminal_paths():
    # Query running terminal64.exe instances; prefer explicitly running terminals
    # over auto-discovery because multiple installs can cause IPC ambiguity.
    cmd = (
        "wmic process where \"name='terminal64.exe'\" "
        "get ExecutablePath /value"
    )
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=5, stderr=subprocess.DEVNULL)
    except Exception:
        return []
    paths = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("ExecutablePath="):
            continue
        p = line.split("=", 1)[1].strip()
        if p and os.path.exists(p):
            paths.append(p)
    # De-duplicate while preserving order.
    seen = set()
    result = []
    for p in paths:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def _candidate_terminal_paths():
    """Return only the Hermes-owned pinned FxPro terminal.

    This intentionally ignores other running terminal64.exe instances, including
    Atman Gibrid. Runtime/trading tools must fail closed instead of probing the
    wrong MT5 terminal and hanging on IPC/login.
    """
    pinned = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
    preferred = _resolve_env_key("MT5_TERMINAL_PATH") or pinned
    candidates = [preferred]
    if preferred.lower() != pinned.lower():
        candidates.append(pinned)

    resolved = []
    seen = set()
    for path in candidates:
        key = str(path).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        # Hard block Atman/foreign terminal paths even if env is wrong.
        if "atman" in key or "gibrid" in key:
            continue
        if key != pinned.lower():
            continue
        if os.path.exists(path):
            resolved.append(path)
    return resolved


def _initialize_bounded(mt5, kwargs, timeout_s):
    result = {"ok": False, "exc": None}

    def _worker():
        try:
            result["ok"] = bool(mt5.initialize(**kwargs))
        except Exception as e:
            result["exc"] = str(e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        return False, (-10005, f"IPC timeout (init>{timeout_s}s)")
    if result["exc"]:
        return False, (-1, result["exc"])
    if result["ok"]:
        return True, None
    return False, mt5.last_error()


def _expected_mt5_login():
    return _safe_int(_resolve_env_key("MT5_EXPECTED_LOGIN"), 591712391)

def _accept_expected_account(mt5):
    expected = _expected_mt5_login()
    info = mt5.account_info()
    if info is None:
        return False, "NO_ACCOUNT_INFO"
    if int(info.login) != expected:
        return False, f"ACCOUNT_MISMATCH got={info.login} expected={expected}"
    return True, None

def init(retries=3):
    import MetaTrader5 as mt5
    tries = max(1, retries)
    timeout_ms = max(2000, _safe_int(_resolve_env_key("MT5_IPC_TIMEOUT_MS"), 7000))
    wait_s = max(3.0, (timeout_ms / 1000.0) + 1.0)
    terminals = _candidate_terminal_paths()
    last_err = None
    attempt_log = []

    for attempt in range(1, tries + 1):
        # Try explicit terminal paths first.
        for term_path in terminals:
            kwargs = {"path": term_path, "timeout": timeout_ms}
            ok, err = _initialize_bounded(mt5, kwargs, wait_s)
            if ok:
                accepted, account_err = _accept_expected_account(mt5)
                if accepted:
                    return mt5
                last_err = account_err
                attempt_log.append({"attempt": attempt, "path": term_path, "error": account_err})
                try:
                    mt5.shutdown()
                except Exception:
                    pass
                continue
            last_err = err
            attempt_log.append({"attempt": attempt, "path": term_path, "error": str(err)})
            try:
                mt5.shutdown()
            except Exception:
                pass

        # Fallback: auto-discovery as last resort.
        ok, err = _initialize_bounded(mt5, {"timeout": timeout_ms}, wait_s)
        if ok:
            accepted, account_err = _accept_expected_account(mt5)
            if accepted:
                return mt5
            last_err = account_err
            attempt_log.append({"attempt": attempt, "path": "auto", "error": account_err})
            try:
                mt5.shutdown()
            except Exception:
                pass
        else:
            last_err = err
        attempt_log.append({"attempt": attempt, "path": "auto", "error": str(err)})
        try:
            mt5.shutdown()
        except Exception:
            pass

        if attempt < tries:
            time.sleep(min(3.0, 0.8 * attempt))

    _print({
        "error": f"MT5 init failed: {last_err}",
        "attempts": tries,
        "timeout_ms": timeout_ms,
        "terminal_candidates": terminals,
        "attempt_log": attempt_log[-8:],
    })
    sys.exit(1)


def _normalize_symbol_name(value):
    return "".join(ch for ch in (value or "").upper() if ch.isalnum())


def _resolve_symbol(mt5, symbol):
    requested = (symbol or "").strip()
    if not requested:
        return None, {"error": "symbol is required"}

    # Fast path: exact symbol is available.
    try:
        if mt5.symbol_info(requested) is not None:
            mt5.symbol_select(requested, True)
            return requested, None
    except Exception:
        pass

    wanted = _normalize_symbol_name(requested)
    alias_map = {
        "XAUUSD": ("GOLD", "XAUUSD", "XAUUSDm", "XAUUSD.a"),
        "XAGUSD": ("SILVER", "XAGUSD", "XAGUSDm", "XAGUSD.a"),
    }
    for alias in alias_map.get(wanted, ()):
        try:
            if mt5.symbol_info(alias) is not None:
                mt5.symbol_select(alias, True)
                return alias, None
        except Exception:
            pass

    # Fallback: search by normalized prefix/contains (handles broker suffixes).
    all_symbols = mt5.symbols_get()
    if not all_symbols:
        # Last fallback: derive symbol from open positions aliases.
        try:
            positions = mt5.positions_get() or []
            pos_symbols = sorted({str(p.symbol).strip() for p in positions if getattr(p, "symbol", None)})
            for s in pos_symbols:
                n = _normalize_symbol_name(s)
                if n == wanted or n.startswith(wanted):
                    mt5.symbol_select(s, True)
                    return s, None
                if wanted == "XAUUSD" and n == "GOLD":
                    mt5.symbol_select(s, True)
                    return s, None
                if wanted == "XAGUSD" and n == "SILVER":
                    mt5.symbol_select(s, True)
                    return s, None
        except Exception:
            pass
        return None, {"error": f"Symbol {requested} not found", "mt5_error": mt5.last_error()}

    if not wanted:
        return None, {"error": f"Symbol {requested} not found", "mt5_error": mt5.last_error()}

    def score(name):
        n = _normalize_symbol_name(name)
        if n == wanted:
            return (0, len(name))
        if n.startswith(wanted):
            return (1, len(name))
        if wanted in n:
            return (2, len(name))
        return (9, len(name))

    ranked = sorted((s.name for s in all_symbols), key=score)
    candidates = [n for n in ranked if score(n)[0] < 9]
    if not candidates:
        return None, {"error": f"Symbol {requested} not found", "mt5_error": mt5.last_error()}

    selected = candidates[0]
    try:
        mt5.symbol_select(selected, True)
    except Exception:
        pass
    return selected, None


def cmd_price(mt5, symbol):
    symbol, err = _resolve_symbol(mt5, symbol)
    if err is not None:
        _print(err)
        return False

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        _print({"error": f"Symbol {symbol} not found", "mt5_error": mt5.last_error()})
        return False

    spread = round(float(tick.ask) - float(tick.bid), 5)
    _print({
        "symbol": symbol,
        "bid": float(tick.bid),
        "ask": float(tick.ask),
        "spread": spread,
        "time": int(tick.time),
    })
    return True


def cmd_bars(mt5, symbol, tf, count):
    symbol, err = _resolve_symbol(mt5, symbol)
    if err is not None:
        _print(err)
        return False

    count_i = _safe_int(count, -1)
    if count_i < 1 or count_i > 5000:
        _print({"error": "count must be between 1 and 5000"})
        return False

    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    tf_val = tf_map.get((tf or "").upper())
    if tf_val is None:
        _print({"error": f"Unknown timeframe: {tf}", "allowed": list(tf_map.keys())})
        return False

    rates = mt5.copy_rates_from_pos(symbol, tf_val, 0, count_i)
    if rates is None or len(rates) == 0:
        _print({"error": f"No data for {symbol} {tf}", "mt5_error": mt5.last_error()})
        return False

    bars = [
        {
            "time": datetime.fromtimestamp(int(r[0])).isoformat(),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": int(r[5]),
        }
        for r in rates
    ]
    _print({"symbol": symbol, "timeframe": tf.upper(), "bars": bars})
    return True


def cmd_account(mt5):
    info = mt5.account_info()
    if info is None:
        _print({"error": "Cannot get account info", "mt5_error": mt5.last_error()})
        return False

    _print({
        "login": info.login,
        "server": info.server,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "currency": info.currency,
    })
    return True


def cmd_positions(mt5):
    positions = mt5.positions_get()
    if positions is None:
        _print({"error": "positions_get failed", "mt5_error": mt5.last_error()})
        return False
    if len(positions) == 0:
        _print({"positions": [], "count": 0})
        return True

    result = [
        {
            "symbol": p.symbol,
            "type": "buy" if p.type == 0 else "sell",
            "volume": p.volume,
            "price_open": p.price_open,
            "price_current": p.price_current,
            "profit": p.profit,
            "swap": p.swap,
        }
        for p in positions
    ]
    _print({"count": len(positions), "positions": result})
    return True


def main(argv):
    if len(argv) < 2:
        _print({"error": "Usage: mt5_query.py <cmd> [args]", "commands": ["price", "bars", "account", "positions"]})
        return 1

    mt5 = init()
    cmd = argv[1].lower()
    try:
        ok = False
        if cmd == "price" and len(argv) >= 3:
            ok = cmd_price(mt5, argv[2])
        elif cmd == "bars" and len(argv) >= 5:
            ok = cmd_bars(mt5, argv[2], argv[3], argv[4])
        elif cmd == "account":
            ok = cmd_account(mt5)
        elif cmd == "positions":
            ok = cmd_positions(mt5)
        else:
            _print({"error": f"Unknown: {cmd}"})
            return 1
        return 0 if ok else 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
