#!/usr/bin/env python3
"""Get data from MT5/Twelve Data + calculate indicators."""
import json
import subprocess
import sys


def _safe_int(v, default=50):
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _run_json(cmd, timeout=30):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        # If child returned structured JSON with an error, surface that first.
        try:
            payload = json.loads((result.stdout or "").strip() or "{}")
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(str(payload.get("error")))
        except Exception:
            pass
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)} | {result.stderr[:200]}")
    try:
        return json.loads(result.stdout)
    except Exception:
        raise RuntimeError(f"Invalid JSON from command: {' '.join(cmd)} | {result.stderr[:200]}")


def fetch_bars(source, symbol, interval, count):
    py = sys.executable
    if source == "mt5":
        tf_map = {
            "1min": "M1",
            "5min": "M5",
            "15min": "M15",
            "30min": "M30",
            "1h": "H1",
            "4h": "H4",
            "1day": "D1",
            "1week": "W1",
            "1month": "MN1",
        }
        interval = tf_map.get((interval or "").strip().lower(), interval)
        symbol = (symbol or "").replace("/", "")
        cmd = [py, r"C:\Users\Administrator\mt5_query.py", "bars", symbol, interval, str(count)]
    else:
        td_tf_map = {
            "M1": "1min",
            "M5": "5min",
            "M15": "15min",
            "M30": "30min",
            "H1": "1h",
            "H4": "4h",
            "D1": "1day",
            "W1": "1week",
            "MN1": "1month",
        }
        interval = td_tf_map.get((interval or "").strip().upper(), interval)
        cmd = [py, r"C:\Users\Administrator\twelvedata_query.py", "bars", symbol, interval, str(count)]
    data = _run_json(cmd, timeout=35)
    bars = data.get("bars", [])
    if not bars:
        raise RuntimeError(data.get("error", "No bars returned"))
    return bars


def main(argv):
    if len(argv) < 3:
        print(json.dumps({"error": "Usage: analyze_pipe.py SYMBOL INTERVAL [BARS] [SOURCE(mt5|twelvedata)]"}))
        return 1

    symbol = (argv[1] or "").strip()
    interval = (argv[2] or "").strip()
    count = _safe_int(argv[3], 50) if len(argv) > 3 else 50
    source = (argv[4] if len(argv) > 4 else "twelvedata").strip().lower()

    if not symbol:
        print(json.dumps({"error": "symbol is required"}))
        return 1
    if count < 20 or count > 5000:
        print(json.dumps({"error": "bars must be between 20 and 5000"}))
        return 1
    if source not in {"mt5", "twelvedata"}:
        print(json.dumps({"error": "source must be mt5 or twelvedata"}))
        return 1

    try:
        bars = fetch_bars(source, symbol, interval, count)

        r2 = subprocess.run(
            [sys.executable, r"C:\Users\Administrator\indicators.py"],
            input=json.dumps(bars),
            capture_output=True,
            text=True,
            timeout=20,
        )
        if r2.returncode != 0:
            print(json.dumps({"error": "Indicator calc failed", "raw": r2.stderr[:200]}))
            return 1

        indicators = json.loads(r2.stdout)
        if indicators.get("error"):
            print(json.dumps(indicators))
            return 1

        rsi_val = indicators.get("rsi_14")
        macd_trend = indicators.get("macd_trend", "neutral")
        ema_trend = indicators.get("trend_short", "neutral")
        bb_pos = indicators.get("bb_position")

        signals = []
        if rsi_val is not None and rsi_val < 30:
            signals.append("RSI oversold")
        elif rsi_val is not None and rsi_val > 70:
            signals.append("RSI overbought")

        if macd_trend == "bullish":
            signals.append("MACD bullish")
        elif macd_trend == "bearish":
            signals.append("MACD bearish")

        if ema_trend == "up":
            signals.append("EMA up")
        elif ema_trend == "down":
            signals.append("EMA down")

        if bb_pos is not None and bb_pos < 5:
            signals.append("At lower BB")
        elif bb_pos is not None and bb_pos > 95:
            signals.append("At upper BB")

        bullish = sum(1 for s in signals if ("up" in s.lower() or "bullish" in s.lower() or "oversold" in s.lower()))
        bearish = sum(1 for s in signals if ("down" in s.lower() or "bearish" in s.lower() or "overbought" in s.lower()))

        overall = "NEUTRAL"
        if bullish > bearish:
            overall = "BULLISH"
        elif bearish > bullish:
            overall = "BEARISH"

        indicators["source"] = source
        indicators["symbol"] = symbol
        indicators["interval"] = interval
        indicators["overall_signal"] = overall
        indicators["signals"] = signals

        print(json.dumps(indicators, indent=2))
        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
