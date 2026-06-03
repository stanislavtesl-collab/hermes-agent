import yfinance as yf, pandas as pd
from datetime import datetime, timezone

# Get gold futures data via yfinance
gold = yf.download("GC=F", interval="15m", period="2d", progress=False)
if gold.empty:
    gold = yf.download("XAUUSD=X", interval="15m", period="2d", progress=False)

if gold.empty:
    print("NO DATA")
    exit()

if isinstance(gold.columns, pd.MultiIndex):
    gold.columns = [c[0] for c in gold.columns]

c = gold["Close"].values.astype(float)
h = gold["High"].values.astype(float)
l = gold["Low"].values.astype(float)
o = gold["Open"].values.astype(float)

print("=== CURRENT (GC=F futures) ===")
print("Price: %.2f" % c[-1])

# M15 analysis
sma20 = sum(c[-20:]) / 20
sma50 = sum(c[-50:]) / 50
sma100 = sum(c[-100:]) / 100 if len(c) >= 100 else 0

gains = losses = 0
for i in range(1, 15):
    d = c[-i] - c[-i-1]
    if d > 0: gains += d
    else: losses -= d
rs = (gains/14)/(losses/14) if losses else 999
rsi = 100 - 100/(1+rs)

tr_s = 0
for i in range(1, 15):
    tr = max(h[-i]-l[-i], abs(h[-i]-c[-i-1]), abs(l[-i]-c[-i-1]))
    tr_s += tr
atr = tr_s / 14

sw_h = max(h[-20:])
sw_l = min(l[-20:])
range_ = sw_h - sw_l

print("\n=== M15 ===")
print("SMA20: %.2f  SMA50: %.2f" % (sma20, sma50))
if sma100: print("SMA100: %.2f" % sma100)
print("RSI14: %.1f  ATR14: %.2f" % (rsi, atr))
trend = "BULLISH" if sma20 > sma50 else "BEARISH" if sma20 < sma50 else "SIDEWAYS"
print("Trend: %s" % trend)
print("Swing(20): H=%.2f L=%.2f  Range=%.2f (%.0f pts)" % (sw_h, sw_l, range_, range_*100))

print("\nLast 8 M15:")
for i in range(-8, 0):
    t = str(gold.index[i])[11:16]
    body = c[i] - o[i]
    col = "GREEN" if body > 0 else "RED"
    print("  %s O:%.2f H:%.2f L:%.2f C:%.2f %s" % (t, o[i], h[i], l[i], c[i], col))

# H1
gold_h1 = yf.download("GC=F", interval="1h", period="3d", progress=False)
if not gold_h1.empty:
    if isinstance(gold_h1.columns, pd.MultiIndex):
        gold_h1.columns = [c[0] for c in gold_h1.columns]
    c_h1 = gold_h1["Close"].values.astype(float)
    h_h1 = gold_h1["High"].values.astype(float)
    l_h1 = gold_h1["Low"].values.astype(float)
    
    s20_h1 = sum(c_h1[-20:]) / 20
    s50_h1 = sum(c_h1[-min(30, len(c_h1)):]) / min(30, len(c_h1))
    
    print("\n=== H1 ===")
    print("SMA20: %.2f SMA50: %.2f" % (s20_h1, s50_h1))
    trend_h1 = "BULLISH" if s20_h1 > s50_h1 else "BEARISH" if s20_h1 < s50_h1 else "SIDEWAYS"
    print("Trend: %s" % trend_h1)
    print("Swing(20): H=%.2f L=%.2f" % (max(h_h1[-20:]), min(l_h1[-20:])))
    print("Price: %.2f" % c_h1[-1])
    
# H4
gold_h4 = yf.download("GC=F", interval="1h", period="5d", progress=False)
if not gold_h4.empty:
    if isinstance(gold_h4.columns, pd.MultiIndex):
        gold_h4.columns = [c[0] for c in gold_h4.columns]
    c_h4 = gold_h4["Close"].values.astype(float)
    h_h4 = gold_h4["High"].values.astype(float)
    l_h4 = gold_h4["Low"].values.astype(float)
    
    print("\n=== H4 ===")
    s20_h4 = sum(c_h4[-20:]) / 20
    s50_h4 = sum(c_h4[-min(50, len(c_h4)):]) / min(50, len(c_h4))
    print("SMA20: %.2f SMA50: %.2f" % (s20_h4, s50_h4))
    trend_h4 = "BULLISH" if s20_h4 > s50_h4 else "BEARISH" if s20_h4 < s50_h4 else "SIDEWAYS"
    print("Trend: %s" % trend_h4)
    print("Swing(20): H=%.2f L=%.2f" % (max(h_h4[-20:]), min(l_h4[-20:])))

# Profit calc
print("\n=== PROFIT (GOLD 1pt=$1 per 1.0 lot on MT5) ===")
for lot, name in [(0.03, "current"), (0.1, "step1"), (0.3, "step2"), (0.5, "target"), (1.0, "goal")]:
    for pts in [100, 200, 300]:
        print("  %dpts x %.2f (%s) = \$%.0f" % (pts, lot, name, pts * lot))

# RISK
print("\n=== RISK MANAGEMENT ===")
print("Balance: ~$1550")
print("Max risk per trade: 2%% = $31")
for lot in [0.03, 0.1, 0.3, 0.5]:
    for sl_pts in [50, 80, 100, 150]:
        risk = sl_pts * lot
        if risk <= 35:
            print("  SL=%dpts x %.2f = \$%.0f (%.1f%%) ✅" % (sl_pts, lot, risk, risk/1550*100))
