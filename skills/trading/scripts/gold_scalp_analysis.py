"""Full GOLD scalping analysis pipeline — ANALYSIS ONLY, no auto-trades.
Updated 29.05.2026: score filter v3, Candlestick Fatigue, M15 RSI<=55, price-below-EMA20 block.

Usage:
    python C:/Users/Administrator/gold_scalp_analysis.py

Output: machine-parsable prefix-tagged lines for agent consumption.
"""
import MetaTrader5 as mt5
import time
from datetime import datetime

# ===== CONFIG =====
MT5_PATH = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
SYMBOL = "GOLD"

# ===== CONNECT =====
mt5.shutdown()
time.sleep(0.3)
if not mt5.initialize(path=MT5_PATH, timeout=30000):
    print(f"CONNECT_ERROR|{mt5.last_error()}")
    exit()

acc = mt5.account_info()
if not acc:
    print("CONNECT_ERROR|No account_info")
    mt5.shutdown()
    exit()

if not mt5.symbol_select(SYMBOL, True):
    print(f"SYMBOL_ERROR|Cannot select {SYMBOL}")
    mt5.shutdown()
    exit()

si = mt5.symbol_info(SYMBOL)
current_bid = si.bid
current_ask = si.ask
current_price = (current_bid + current_ask) / 2

# ===== DATA FETCH =====
def get_rates(tf, count):
    r = mt5.copy_rates_from_pos(SYMBOL, tf, 0, count)
    if r is None: return None
    return [{"time": datetime.fromtimestamp(c[0]), "open": c[1], "close": c[4], "high": c[2], "low": c[3], "volume": c[5]} for c in r]

m5 = get_rates(mt5.TIMEFRAME_M5, 150)
m15 = get_rates(mt5.TIMEFRAME_M15, 60)
h1 = get_rates(mt5.TIMEFRAME_H1, 48)
h4 = get_rates(mt5.TIMEFRAME_H4, 30)

# ===== INDICATORS =====
def rsi(data, period=14):
    closes = [c['close'] for c in data]
    if len(closes) < period + 1: return 50.0
    gains, losses = [], []
    for i in range(-period, 0):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    rs = ag / al if al else 999
    return round(100 - 100 / (1 + rs), 2)

def ema_series(data, period):
    closes = [c['close'] for c in data]
    if len(closes) < period: return [closes[-1]]
    mult = 2 / (period + 1)
    s = [sum(closes[:period]) / period]
    for p in closes[period:]:
        s.append((p - s[-1]) * mult + s[-1])
    return s

def macd(data, fast=12, slow=26, sig=9):
    ef = ema_series(data, fast)
    es = ema_series(data, slow)
    if len(ef) < 1 or len(es) < 1: return 0, 0, 0
    vals = [ef[i] - es[i] for i in range(min(len(ef), len(es)))]
    m = round(vals[-1], 2)
    s = round(sum(vals[-sig:]) / sig, 2) if len(vals) >= sig else m
    h = round(m - s, 2)
    return m, s, h

def bb(data, period=20, std=2.0):
    closes = [c['close'] for c in data[-period:]]
    sma = sum(closes) / period
    var = sum((c - sma)**2 for c in closes) / period
    d = (var ** 0.5) * std
    return {"upper": round(sma + d, 2), "mid": round(sma, 2), "lower": round(sma - d, 2)}

def sr_levels(data, lookback=50):
    highs, lows = [c['high'] for c in data[-lookback:]], [c['low'] for c in data[-lookback:]]
    res, sup = [], []
    for i in range(2, len(highs)-2):
        if all(highs[i] > highs[i+j] for j in [-2,-1,1,2]): res.append(highs[i])
        if all(lows[i] < lows[i+j] for j in [-2,-1,1,2]): sup.append(lows[i])
    def cluster(vals, tol=0.8):
        if not vals: return []
        g = {}
        for v in sorted(vals):
            k = next((k for k in g if abs(v - k) <= tol), None)
            if k is not None: g[k].append(v)
            else: g[v] = [v]
        return sorted([round(sum(v)/len(v), 2) for v in g.values()])
    return {"sup": cluster(sup)[:5], "res": cluster(res)[-5:]}

def atr(data, period=14):
    trs = []
    for i in range(1, min(period+1, len(data))):
        hl = data[i]['high'] - data[i]['low']
        hc = abs(data[i]['high'] - data[i-1]['close'])
        lc = abs(data[i]['low'] - data[i-1]['close'])
        trs.append(max(hl, hc, lc))
    return round(sum(trs) / len(trs), 2) if trs else None

def candlestick_fatigue(data, lookback=10):
    recent = data[-(lookback+1):-1]
    if len(recent) < lookback: return False
    bull = sum(1 for c in recent if c['close'] > c['open'])
    return bull >= 7

# ===== COMPUTE =====
rsi_m5 = rsi(m5)
rsi_m15 = rsi(m15) if m15 else 50
rsi_h1 = rsi(h1) if h1 else 50
rsi_h4 = rsi(h4) if h4 else 50

macd_m5, sig_m5, hist_m5 = macd(m5)
bb_m5 = bb(m5)
sr = sr_levels(m5)
atr_m5 = atr(m5)

last = m5[-1]
vols = [c['volume'] for c in m5[-30:]]
avg_vol = round(sum(vols) / len(vols))
last_vol = last['volume']
fatigued = candlestick_fatigue(m5)

ema20 = ema_series(m5, 20)[-1]
ema50 = ema_series(m5, 50)[-1] if len(m5) >= 50 else 0
price_below_ema20 = current_price < ema20

# ===== SCORING (v3 — updated 29.05) =====
buy_score = 0
sell_score = 0

if rsi_m5 < 30: buy_score += 3
elif rsi_m5 < 40: buy_score += 2
elif rsi_m5 < 50: buy_score += 1
if rsi_m5 > 70: sell_score += 3
elif rsi_m5 > 60: sell_score += 2
elif rsi_m5 > 50: sell_score += 1

if hist_m5 > 0: buy_score += 2 if hist_m5 > 0.5 else 1
if hist_m5 < 0: sell_score += 2 if hist_m5 < -0.5 else 1

# Trend: M5 + M15 agreement
if ema20 > ema50 and current_price > ema20: buy_score += 2
elif ema20 < ema50 and current_price < ema20: sell_score += 2

if current_price < bb_m5['lower']: buy_score += 2
elif current_price < bb_m5['mid']: buy_score += 1
if current_price > bb_m5['upper']: sell_score += 2
elif current_price > bb_m5['mid']: sell_score += 1

if last_vol > avg_vol * 1.5:
    if last['close'] > last['open']: buy_score += 1
    else: sell_score += 1

spread_points = current_ask - current_bid

# ===== FILTER CHECKS =====
m15_filter_pass = rsi_m15 <= 55
fatigue_pass = not fatigued
price_filter_pass = not price_below_ema20  # BUY only if price >= EMA20

# ===== OUTPUT =====
print(f"ACCOUNT|Login:{acc.login}|Balance:${acc.balance:.2f}")
print(f"SYMBOL|{SYMBOL}|Bid:{current_bid}|Ask:{current_ask}|Spread:{spread_points:.2f}")
print(f"CANDLE|O:{last['open']}|H:{last['high']}|L:{last['low']}|C:{last['close']}|Dir:{'BULL' if last['close']>last['open'] else 'BEAR'}|Vol:{last_vol}")
print(f"RSI|M5:{rsi_m5}|M15:{rsi_m15}|H1:{rsi_h1}|H4:{rsi_h4}")
print(f"MACD|M5:{macd_m5}|Signal:{sig_m5}|Hist:{hist_m5}")
print(f"BB|U:{bb_m5['upper']}|M:{bb_m5['mid']}|L:{bb_m5['lower']}")
print(f"ATR|M5:{atr_m5}")
print(f"SR|Sup:{sr['sup']}|Res:{sr['res']}")
print(f"VOL|Avg:{avg_vol}|Last:{last_vol}|Ratio:{round(last_vol/avg_vol,2)}x")
print(f"SCORE|Buy:{buy_score}|Sell:{sell_score}")
print(f"FILTERS|M15_55:{'PASS' if m15_filter_pass else f'BLOCKED({rsi_m15})'}|Fatigue:{'OK' if fatigue_pass else 'BLOCKED'}|PriceAboveE20:{'OK' if not price_below_ema20 else 'BLOCKED'}")

# ENTRY DECISION (analysis only — NO auto-trade)
can_buy = (buy_score >= sell_score + 3 and m15_filter_pass and fatigue_pass and not price_below_ema20)
can_sell = (sell_score >= buy_score + 3)

if can_buy and not can_sell:
    sl = round(current_price - atr_m5 * 1.5, 2) if atr_m5 else round(current_price - 3.0, 2)
    tp = round(current_price + atr_m5 * 2.0, 2) if atr_m5 else round(current_price + 4.0, 2)
    print(f"VERDICT|BUY")
    print(f"ENTRY|{current_ask}")
    print(f"SL|{sl}|Risk:${round(abs(current_ask-sl)*10*0.03, 2)}")
    print(f"TP|{tp}|Reward:${round(abs(tp-current_bid)*10*0.03, 2)}")
elif can_sell and not can_buy:
    sl = round(current_price + atr_m5 * 1.5, 2) if atr_m5 else round(current_price + 3.0, 2)
    tp = round(current_price - atr_m5 * 2.0, 2) if atr_m5 else round(current_price - 4.0, 2)
    print(f"VERDICT|SELL")
    print(f"ENTRY|{current_bid}")
    print(f"SL|{sl}|Risk:${round(abs(sl-current_bid)*10*0.03, 2)}")
    print(f"TP|{tp}|Reward:${round(abs(current_bid-tp)*10*0.03, 2)}")
else:
    reasons = []
    if not can_buy:
        if buy_score < sell_score + 3: reasons.append(f"buy_gap({buy_score-vs{sell_score}+3})")
        if not m15_filter_pass: reasons.append(f"m15_>55({rsi_m15})")
        if fatigued: reasons.append("fatigue")
        if price_below_ema20: reasons.append("price_below_ema20")
    if not can_sell:
        if sell_score < buy_score + 3: reasons.append(f"sell_gap({sell_score-vs{buy_score}+3})")
    print(f"VERDICT|HOLD")
    print(f"REASONS|{'|'.join(reasons)}")

print(f"TIME|{datetime.now().strftime('%H:%M:%S')}")
mt5.shutdown()
