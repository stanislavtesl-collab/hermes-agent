#!/usr/bin/env python3
"""Multi-timeframe XAUUSD analysis — fetch + compute RSI/MACD/EMA/BB"""

import json, sys, os
from datetime import datetime
import urllib.request

# Read API key from .env
env_path = "C:/Users/Administrator/AppData/Local/hermes/.env"
api_key = None
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("TWELVEDATA_API_KEY="):
            api_key = line.split("=", 1)[1].strip()
            break

if not api_key:
    print("ERROR: No TWELVEDATA_API_KEY found")
    sys.exit(1)

SYMBOL = "XAU/USD"

def fetch_ohlcv(interval, outputsize):
    url = (f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={interval}"
           f"&outputsize={outputsize}&apikey={api_key}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())

# Helper: compute EMA
def ema(values, period):
    if len(values) < period:
        return [None]*len(values)
    k = 2/(period+1)
    result = [None]*(period-1)
    result.append(sum(values[:period])/period)
    for v in values[period:]:
        result.append(v*k + result[-1]*(1-k))
    return result

def rsi(values, period=14):
    if len(values) < period+1:
        return [None]*len(values)
    gains, losses = [], []
    for i in range(1, period+1):
        d = values[i]-values[i-1]
        gains.append(max(d,0))
        losses.append(max(-d,0))
    ag = sum(gains)/period; al = sum(losses)/period
    rsi_vals = [None]*period
    if al == 0: rsi_vals.append(100)
    else: rsi_vals.append(100-100/(1+ag/al))
    for i in range(period+1, len(values)):
        d = values[i]-values[i-1]
        g = max(d,0); l = max(-d,0)
        ag = (ag*(period-1)+g)/period
        al = (al*(period-1)+l)/period
        if al == 0: rsi_vals.append(100)
        else: rsi_vals.append(100-100/(1+ag/al))
    return rsi_vals

def macd(values, fast=12, slow=26, signal=9):
    ef = ema(values, fast)
    es = ema(values, slow)
    macd_line = []
    for fv, sv in zip(ef, es):
        if fv is None or sv is None:
            macd_line.append(None)
        else:
            macd_line.append(fv-sv)
    clean = [x for x in macd_line if x is not None]
    sig = ema(clean, signal) if len(clean) >= signal else []
    pad = [None]*(len(macd_line)-len(sig)) + sig
    hist = []
    for m,s in zip(macd_line, pad):
        if m is None or s is None:
            hist.append(None)
        else:
            hist.append(m-s)
    return macd_line, pad, hist

def bb(values, period=20, std=2):
    if len(values) < period:
        return [None]*len(values), [None]*len(values), [None]*len(values)
    mid = [None]*(period-1); upper=[]; lower=[]
    for i in range(period-1, len(values)):
        w = values[i-period+1:i+1]
        avg = sum(w)/period
        var = sum((x-avg)**2 for x in w)/period
        sd = var**0.5
        mid.append(avg)
        upper.append(avg+std*sd)
        lower.append(avg-std*sd)
    return mid, upper, lower

def analyze(interval, size):
    raw = fetch_ohlcv(interval, size)
    vals = raw.get("values", [])
    vals.sort(key=lambda v: v["datetime"])
    closes = [float(v["close"]) for v in vals]
    highs = [float(v["high"]) for v in vals]
    lows = [float(v["low"]) for v in vals]
    last = closes[-1]
    prev = closes[-2] if len(closes)>=2 else last

    rsi_vals = rsi(closes, 14)
    rsi_v = rsi_vals[-1] if rsi_vals[-1] is not None else 50
    rsi_p = rsi_vals[-2] if len(rsi_vals)>=2 and rsi_vals[-2] is not None else rsi_v

    macd_l, macd_s, hist = macd(closes)
    macd_v = macd_l[-1] if macd_l[-1] is not None else 0
    sig_v = macd_s[-1] if macd_s[-1] is not None else 0
    hist_v = hist[-1] if hist[-1] is not None else 0
    recent_h = [h for h in hist[-12:] if h is not None]
    green = sum(1 for h in recent_h if h>0)
    red = sum(1 for h in recent_h if h<=0)

    e20 = ema(closes,20)[-1] if len(closes)>=20 else None
    e50 = ema(closes,50)[-1] if len(closes)>=50 else None

    b_mid, b_up, b_lo = bb(closes)
    bb_pos = "above_upper" if last > b_up[-1] else \
             "below_lower" if last < b_lo[-1] else \
             "above_mid" if last > b_mid[-1] else \
             "below_mid"
    bb_w = ((b_up[-1]-b_lo[-1])/b_mid[-1]*100) if b_mid[-1] else 0

    sh = max(highs[-20:])
    sl = min(lows[-20:])
    nr_h = (sh-last)/(sh-sl)*100 if (sh-sl)>0 else 50

    bullish = sum([
        1 if e20 and last>e20 else 0,
        1 if e50 and last>e50 else 0,
        1 if macd_v > sig_v else 0,
        1 if rsi_v > 50 else 0,
        1 if nr_h > 60 else 0,
    ])
    bearish = 5-bullish
    bias = "BULLISH" if bullish>=4 else "BEARISH" if bearish>=4 else "NEUTRAL"

    return {
        "timeframe": interval,
        "last_close": round(last,2),
        "change": round(last-prev,2),
        "change_pct": round((last-prev)/prev*100,2) if prev else 0,
        "rsi": round(rsi_v,1),
        "rsi_trend": "up" if rsi_v>rsi_p else "down",
        "rsi_zone": "overbought" if rsi_v>70 else "oversold" if rsi_v<30 else "neutral",
        "macd_line": round(macd_v,2),
        "macd_signal": round(sig_v,2),
        "macd_hist": round(hist_v,2),
        "macd_bars_green": green,
        "macd_bars_red": red,
        "macd_cross": "above_signal" if macd_v>sig_v else "below_signal",
        "ema20": round(e20,2) if e20 else None,
        "ema50": round(e50,2) if e50 else None,
        "price_vs_ema20": "above" if e20 and last>e20 else "below" if e20 else "unknown",
        "price_vs_ema50": "above" if e50 and last>e50 else "below" if e50 else "unknown",
        "bb_position": bb_pos,
        "bb_width_pct": round(bb_w,2),
        "swing_high_20": round(sh,2),
        "swing_low_20": round(sl,2),
        "near_high_pct": round(nr_h,1),
        "bias": bias,
    }

INTERVALS = [("5min",200), ("15min",200), ("1h",150), ("4h",120)]
results = []
for iv, sz in INTERVALS:
    sys.stdout.write(f"Fetching {iv}... ")
    sys.stdout.flush()
    try:
        r = analyze(iv, sz)
        results.append(r)
        print(f"{r['last_close']} ✓")
    except Exception as e:
        print(f"FAILED: {e}")

print("\n" + "="*75)
print("  XAUUSD MULTI-TIMEFRAME ANALYSIS")
print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print("="*75)

# Table
hdr = f"{'TF':<6} {'Close':>8} {'Chg%':>7} {'RSI':>6} {'Zone':>12} {'Hist':>7} {'xSig':>8} {'vsE20':>6} {'vsE50':>6} {'BB':>12}"
print(f"\n{hdr}")
print("-"*len(hdr))
for r in results:
    bb_lbl = r["bb_position"].replace("_"," ")
    print(f"{r['timeframe']:<6} {r['last_close']:>8.2f} {r['change_pct']:>7.2f} "
          f"{r['rsi']:>6.1f} {r['rsi_zone']:>12} {r['macd_hist']:>7.2f} {r['macd_cross']:>8} "
          f"{r['price_vs_ema20']:>6} {r['price_vs_ema50']:>6} {bb_lbl:>12}")

print(f"\n{'='*75}")
print("\n  MTF SYNTHESIS")
print("  " + "-"*45)
for r in results:
    arr = "↑" if r['price_vs_ema20']=='above' else "↓"
    arr50 = "↑" if r['price_vs_ema50']=='above' else "↓"
    cross = "▲" if r['macd_cross']=='above_signal' else "▼"
    bb_lbl = r['bb_position'].replace("_"," ")
    print(f"  {r['timeframe']:6s} | {r['bias']:<8s} | RSI={r['rsi']:<5.1f} | "
          f"EMA20{arr} EMA50{arr50} | MACD{cross} | {bb_lbl}")

bull_c = sum(1 for r in results if r['bias']=='BULLISH')
bear_c = sum(1 for r in results if r['bias']=='BEARISH')
neutral_c = sum(1 for r in results if r['bias']=='NEUTRAL')
htf_bias = "BULLISH" if bull_c>=3 else "BEARISH" if bear_c>=3 else "MIXED"
print(f"\n  DOMINANT: {htf_bias} (Bull={bull_c} Bear={bear_c} Neut={neutral_c})")

# Key levels from H4+H1
h4 = [r for r in results if r['timeframe']=='4h']
h1 = [r for r in results if r['timeframe']=='1h']
h4_r = h4[0] if h4 else results[-1]
h1_r = h1[0] if h1 else results[-1]

s1 = h4_r["swing_low_20"]
s2 = round(s1 - (h1_r["swing_high_20"]-h1_r["swing_low_20"])*0.5, 2)
r1 = h4_r["swing_high_20"]
r2 = round(r1 + (h1_r["swing_high_20"]-h1_r["swing_low_20"])*0.5, 2)

print(f"\n  KEY LEVELS")
print(f"  Resistance: R2={r2}  R1={r1}")
print(f"  Support:    S1={s1}  S2={s2}")
print(f"  Last: {h4_r['last_close']}")

# Risk assessment
print(f"\n  RISK ASSESSMENT")
print("  " + "-"*45)
m5 = [r for r in results if r['timeframe']=='5min'][0]
m15 = [r for r in results if r['timeframe']=='15min'][0]
print(f"  H4 RSI={h4_r['rsi']:.1f} — {'extended' if h4_r['rsi']>65 else 'room to run' if h4_r['rsi']<45 else 'mid-range'}")
print(f"  H1 RSI={h1_r['rsi']:.1f} — {'extended' if h1_r['rsi']>65 else 'room to run' if h1_r['rsi']<45 else 'mid-range'}")
print(f"  M5 RSI={m5['rsi']:.1f} — {'hot' if m5['rsi']>70 else 'cold' if m5['rsi']<30 else 'neutral'}")
for r in results:
    note = "compressed" if r['bb_width_pct']<0.5 else "normal" if r['bb_width_pct']<1.5 else "expanded"
    print(f"  {r['timeframe']} BB width: {r['bb_width_pct']:.2f}% — {note}")
print(f"  Market: {'choppy' if neutral_c>=2 else 'trending'}")

# Scenarios
print(f"\n{'='*75}")
print("  TRADING SCENARIOS")
print(f"{'='*75}\n")

if htf_bias in ("BULLISH", "MIXED"):
    pull_lo = round(s1 + (h4_r['last_close']-s1)*0.382, 2)
    pull_hi = round(s1 + (h4_r['last_close']-s1)*0.618, 2)
    tp1 = r1
    tp2 = round(r1 + (r1-s1)*0.5, 2)
    sl = round(s1 - 3, 2)
    rr1 = round((tp1 - pull_hi) / (pull_hi - sl), 1) if (pull_hi-sl)>0 else 0
    rr2 = round((tp2 - pull_hi) / (pull_hi - sl), 1) if (pull_hi-sl)>0 else 0

    print(f"  SCENARIO A — BUY ON PULLBACK (aligned with HTF)")
    print(f"  {'─'*55}")
    print(f"  Entry:     {pull_lo}–{pull_hi} (38.2–61.8% retrace of H4 swing)")
    print(f"  Stop:      {sl} (below S1)")
    print(f"  Target 1:  {tp1} (H4 swing high)")
    print(f"  Target 2:  {tp2} (extended)")
    print(f"  R:R:       ~1:{rr1} to 1:{rr2}")
    print(f"  Invalidation: H1 close below {s1}")
    print(f"  Confirmation: M5 RSI<40 + M15 bullish engulfing + MACD crossover")

    print(f"\n  SCENARIO B — BREAKOUT BUY (momentum)")
    print(f"  {'─'*55}")
    break_lo = round(r1 + 2, 2)
    sl_b = round(s1 - 2, 2)
    tp1_b = round(r1 + (r1-s1)*0.382, 2)
    tp2_b = round(r1 + (r1-s1)*0.618, 2)
    rr_b1 = round((tp1_b - break_lo)/(break_lo-sl_b), 1) if (break_lo-sl_b)>0 else 0
    rr_b2 = round((tp2_b - break_lo)/(break_lo-sl_b), 1) if (break_lo-sl_b)>0 else 0
    print(f"  Entry:     On break above {break_lo} with M15 close")
    print(f"  Stop:      {sl_b} (below S1)")
    print(f"  Target 1:  {tp1_b} (R:R ~1:{rr_b1})")
    print(f"  Target 2:  {tp2_b} (R:R ~1:{rr_b2})")
    print(f"  Invalidation: Price rejected at R1 → fakeout")

if htf_bias in ("BEARISH", "MIXED") and htf_bias != "BULLISH":
    sell_lo = round(h4_r['last_close'] - (h4_r['last_close']-s1)*0.382, 2)
    sell_hi = round(h4_r['last_close'] - (h4_r['last_close']-s1)*0.618, 2)
    sl_s = round(r1 + 3, 2)
    tp1_s = s1
    tp2_s = round(s1 - (r1-s1)*0.5, 2)
    rr_s1 = round((sell_lo - s1)/(r1-sell_lo), 1) if (r1-sell_lo)>0 else 0
    print(f"\n  SCENARIO B — SELL ON RALLY")
    print(f"  {'─'*55}")
    print(f"  Entry:     {sell_lo}–{sell_hi}")
    print(f"  Stop:      {sl_s} (above R1)")
    print(f"  Target 1:  {tp1_s} (S1)")
    print(f"  Target 2:  {tp2_s} (extended)")
    print(f"  R:R:       ~1:{rr_s1}")
    print(f"  Invalidation: H1 close above {r1}")

print(f"\n{'='*75}")
print(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"{'='*75}")

# Save JSON for reference
out = {"results": results, "htf_bias": htf_bias, "price": h4_r['last_close'],
       "R1": r1, "R2": r2, "S1": s1, "S2": s2,
       "timestamp": datetime.utcnow().isoformat()}
print(f"\n<!-- JSON: {json.dumps(out, indent=2)} -->")
