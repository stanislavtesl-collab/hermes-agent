#!/usr/bin/env python3
"""Technical indicators calculator — RSI, MACD, EMA, BB, ATR."""
import json
import sys


def ema(data, period):
    if period <= 0 or len(data) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(data[:period]) / period]
    for price in data[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return [None] * (period - 1) + result


def sma(data, period):
    if period <= 0 or len(data) < period:
        return []
    return [None] * (period - 1) + [sum(data[i - period + 1 : i + 1]) / period for i in range(period - 1, len(data))]


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return []
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff > 0 else 0)
        losses.append(-diff if diff < 0 else 0)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result = [None] * period

    if avg_loss == 0:
        result.append(100)
    else:
        result.append(100 - 100 / (1 + avg_gain / avg_loss))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100)
        else:
            result.append(100 - 100 / (1 + avg_gain / avg_loss))
    return result


def macd(closes, fast=12, slow=26, signal=9):
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    if not ema_fast or not ema_slow:
        return [], [], []

    macd_line = []
    for i in range(len(closes)):
        if i < len(ema_fast) and i < len(ema_slow) and ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line.append(ema_fast[i] - ema_slow[i])
        else:
            macd_line.append(None)

    valid_vals = [v for v in macd_line if v is not None]
    signal_line = [None] * len(closes)
    if len(valid_vals) >= signal:
        sig_vals = ema(valid_vals, signal)
        valid_idx = [i for i, v in enumerate(macd_line) if v is not None]
        for j, idx in enumerate(valid_idx):
            if j < len(sig_vals):
                signal_line[idx] = sig_vals[j]

    histogram = [None] * len(closes)
    for i in range(len(closes)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, histogram


def bollinger(closes, period=20, std_dev=2):
    ma = sma(closes, period)
    if not ma:
        return [], [], []

    upper, lower = [None] * len(closes), [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        std = (sum((x - ma[i]) ** 2 for x in window) / period) ** 0.5
        upper[i] = ma[i] + std_dev * std
        lower[i] = ma[i] - std_dev * std
    return ma, upper, lower


def analyze(data):
    if not data:
        return {"error": "no input bars"}

    try:
        closes = [float(b["close"]) for b in data]
        highs = [float(b["high"]) for b in data]
        lows = [float(b["low"]) for b in data]
    except Exception:
        return {"error": "invalid bars format"}

    n = len(closes)
    if n < 20:
        return {"error": "need at least 20 bars"}

    last = closes[-1]
    rsi14 = rsi(closes, 14)
    macd_line, signal_line, histogram = macd(closes)
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    bb_mid, bb_upper, bb_lower = bollinger(closes)

    def _last(arr):
        return arr[-1] if arr and arr[-1] is not None else None

    rsi_last = _last(rsi14)
    macd_last = _last(macd_line)
    macd_sig_last = _last(signal_line)
    macd_hist_last = _last(histogram)
    ema9_last = _last(ema9)
    ema21_last = _last(ema21)
    bb_u_last = _last(bb_upper)
    bb_m_last = _last(bb_mid)
    bb_l_last = _last(bb_lower)

    bb_pos = None
    if bb_u_last is not None and bb_l_last is not None and bb_u_last != bb_l_last:
        bb_pos = round((last - bb_l_last) / (bb_u_last - bb_l_last) * 100, 1)

    return {
        "symbol": data[0].get("symbol", "?"),
        "bars": n,
        "last_price": last,
        "change_5": round((closes[-1] / closes[-6] - 1) * 100, 2) if n >= 6 else None,
        "change_20": round((closes[-1] / closes[-21] - 1) * 100, 2) if n >= 21 else None,
        "rsi_14": round(rsi_last, 1) if rsi_last is not None else None,
        "rsi_signal": "oversold" if (rsi_last if rsi_last is not None else 50) < 30 else "overbought" if (rsi_last if rsi_last is not None else 50) > 70 else "neutral",
        "macd": round(macd_last, 4) if macd_last is not None else None,
        "macd_signal": round(macd_sig_last, 4) if macd_sig_last is not None else None,
        "macd_histogram": round(macd_hist_last, 4) if macd_hist_last is not None else None,
        "macd_trend": "bullish" if (macd_hist_last if macd_hist_last is not None else 0) > 0 else "bearish",
        "ema9": round(ema9_last, 2) if ema9_last is not None else None,
        "ema21": round(ema21_last, 2) if ema21_last is not None else None,
        "trend_short": "up" if (ema9_last if ema9_last is not None else 0) > (ema21_last if ema21_last is not None else 0) else "down",
        "bb_upper": round(bb_u_last, 2) if bb_u_last is not None else None,
        "bb_mid": round(bb_m_last, 2) if bb_m_last is not None else None,
        "bb_lower": round(bb_l_last, 2) if bb_l_last is not None else None,
        "bb_position": bb_pos,
    }


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "empty stdin"}))
        return 1

    try:
        data = json.loads(raw)
    except Exception:
        print(json.dumps({"error": "invalid json input"}))
        return 1

    rows = data.get("bars", data) if isinstance(data, dict) else data
    result = analyze(rows)
    print(json.dumps(result, indent=2))
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
