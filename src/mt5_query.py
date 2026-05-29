#!/usr/bin/env python3
"""MT5 query tool."""
import json
import sys
from datetime import datetime


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False))


def _safe_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def init():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        _print({"error": f"MT5 init failed: {mt5.last_error()}"})
        sys.exit(1)
    return mt5


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
