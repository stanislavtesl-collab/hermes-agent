#!/usr/bin/env python3
"""Twelve Data query tool."""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_KEY = os.getenv("TWELVEDATA_API_KEY", "57351334adf946248a3644438424e3b5").strip()
BASE = "https://api.twelvedata.com"
_ALLOWED_INTERVALS = {
    "1min", "5min", "15min", "30min", "45min",
    "1h", "2h", "4h", "8h", "1day", "1week", "1month",
}


def _json_err(message, **extra):
    payload = {"error": message}
    payload.update(extra)
    return payload


def _safe_int(value, default=None):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def api(path, params, retries=2):
    if not API_KEY:
        return _json_err("TWELVEDATA_API_KEY is empty")

    qs = dict(params)
    qs["apikey"] = API_KEY
    url = f"{BASE}/{path}?{urllib.parse.urlencode(qs)}"
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-trader/1.0"})

    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if data.get("status") == "error":
                code = _safe_int(data.get("code"), 0) or 0
                if code == 429 and attempt < retries:
                    time.sleep(1.2 * (attempt + 1))
                    continue
            return data
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.reason}"
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.2 * (attempt + 1))
                continue
            return _json_err("Twelve Data request failed", details=last_err)
        except Exception as e:
            last_err = str(e)
            if attempt < retries:
                time.sleep(1.2 * (attempt + 1))
                continue

    return _json_err("Twelve Data request failed", details=last_err or "unknown error")


def get_quote(symbol):
    symbol = (symbol or "").strip()
    if not symbol:
        return _json_err("symbol is required")

    data = api("quote", {"symbol": symbol})
    # Twelve Data quote often returns a direct payload without status="ok".
    if data.get("status") == "ok" or ("close" in data and not data.get("error")):
        return {
            "symbol": data.get("symbol", symbol),
            "name": data.get("name", ""),
            "price": data.get("close"),
            "change": data.get("change"),
            "change_pct": data.get("percent_change"),
            "high": data.get("high"),
            "low": data.get("low"),
            "time": data.get("datetime"),
        }
    return data


def get_bars(symbol, interval, count):
    symbol = (symbol or "").strip()
    interval = (interval or "").strip()
    count_i = _safe_int(count, -1)

    if not symbol:
        return _json_err("symbol is required")
    if interval not in _ALLOWED_INTERVALS:
        return _json_err("invalid interval", allowed=sorted(_ALLOWED_INTERVALS))
    if count_i < 1 or count_i > 5000:
        return _json_err("count must be between 1 and 5000")

    data = api("time_series", {"symbol": symbol, "interval": interval, "outputsize": str(count_i)})
    if data.get("status") == "ok":
        bars = []
        for v in data.get("values", []):
            try:
                bars.append({
                    "time": v["datetime"],
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                    "volume": v.get("volume", "0"),
                })
            except Exception:
                continue
        return {
            "symbol": data.get("meta", {}).get("symbol", symbol),
            "interval": data.get("meta", {}).get("interval", interval),
            "type": data.get("meta", {}).get("type", ""),
            "bars": list(reversed(bars)),
        }
    return data


def main(argv):
    if len(argv) < 2:
        print(json.dumps({"error": "Usage", "commands": ["quote SYM", "bars SYM INTERVAL COUNT"]}))
        return 1

    cmd = argv[1].lower()
    if cmd == "quote" and len(argv) >= 3:
        payload = get_quote(argv[2])
        print(json.dumps(payload))
        return 0 if not payload.get("error") else 1

    if cmd == "bars" and len(argv) >= 5:
        payload = get_bars(argv[2], argv[3], argv[4])
        print(json.dumps(payload))
        return 0 if not payload.get("error") else 1

    print(json.dumps({"error": f"Unknown: {cmd}"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
