"""Quick GOLD check + open trade if signal. LOT=0.03
Updated 29.05.2026: score gap 3, M15 RSI <= 55, Candlestick Fatigue, price-below-EMA20 filter, two-direction.
"""
import MetaTrader5 as mt5
import time, json
from datetime import datetime

path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

def init():
    try: mt5.shutdown()
    except: pass
    time.sleep(0.3)
    return mt5.initialize(path=path, timeout=30000)

def get_rates(tf, count):
    r = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if r is None: return None
    return [{"time": datetime.fromtimestamp(c[0]), "open": c[1], "close": c[4], "high": c[2], "low": c[3], "volume": c[5]} for c in r]

def calc_rsi(data, period=14):
    closes = [c['close'] for c in data]
    if len(closes) < period + 1: return 50
    gains, losses = [], []
    for i in range(1, period+1):
        d = closes[-i] - closes[-i-1]
        gains.append(max(d,0))
        losses.append(max(-d,0))
    avg_g = sum(gains)/period
    avg_l = sum(losses)/period or 0.001
    return round(100 - 100/(1+avg_g/avg_l), 2)

def calc_ema(data, period):
    closes = [c['close'] for c in data]
    mult = 2/(period+1)
    ema = sum(closes[:period])/period
    for p in closes[period:]:
        ema = (p-ema)*mult+ema
    return round(ema, 2)

def calc_atr(data, period=14):
    trs = []
    for i in range(1, min(period+1, len(data))):
        hl = data[i]['high']-data[i]['low']
        hc = abs(data[i]['high']-data[i-1]['close'])
        lc = abs(data[i]['low']-data[i-1]['close'])
        trs.append(max(hl,hc,lc))
    return round(sum(trs)/len(trs), 2) if trs else 2.5

def candlestick_fatigue(data, lookback=10):
    """Count bull candles out of last N. >=7 = fatigued = block BUY"""
    recent = data[-(lookback+1):-1]  # exclude current forming candle
    if len(recent) < lookback:
        return False
    bull = sum(1 for c in recent if c['close'] > c['open'])
    return bull >= 7

if not init():
    print(json.dumps({"error": str(mt5.last_error())}))
    exit()

mt5.symbol_select(symbol, True)
acc = mt5.account_info()
si = mt5.symbol_info(symbol)
print(f"Balance: ${acc.balance:.2f} | Bid: {si.bid} Ask: {si.ask} Spread: {(si.ask-si.bid)/0.01:.0f}pts")

m5 = get_rates(mt5.TIMEFRAME_M5, 100)
m15 = get_rates(mt5.TIMEFRAME_M15, 40)

rsi = calc_rsi(m5)
atr = calc_atr(m5)
ema20 = calc_ema(m5, 20)
ema50 = calc_ema(m5, 50) if len(m5) >= 50 else ema20
rsi_m15 = calc_rsi(m15) if m15 else 50

last = m5[-1]
bid = si.bid
ask = si.ask
price = (bid+ask)/2

trend_up = price > ema20 and ema20 > ema50
trend_down = price < ema20 and ema20 < ema50
candle_bull = last['close'] > last['open']
vol = last['volume']
avg_vol = sum(c['volume'] for c in m5[-20:])/20
vol_high = vol > avg_vol * 1.3
fatigued = candlestick_fatigue(m5)

print(f"Price: {round(price,2)} | RSI: {rsi} | ATR: {atr}")
print(f"EMA20: {ema20} | EMA50: {ema50}")
print(f"Trend: {'UP' if trend_up else 'DOWN' if trend_down else 'RANGING'}")
print(f"Candle: {'Bull' if candle_bull else 'Bear'} | Vol: {vol} (avg {avg_vol:.0f})")
print(f"M15 RSI: {rsi_m15}")
print(f"Fatigue: {'YES ❌' if fatigued else 'OK ✅'} ({sum(1 for c in m5[-11:-1] if c['close']>c['open'])}/10 bull candles)")

buy_score = 0
sell_score = 0

if rsi < 30: buy_score += 3
elif rsi < 40: buy_score += 2
elif rsi < 50: buy_score += 1
if rsi > 70: sell_score += 3
elif rsi > 60: sell_score += 2
elif rsi > 50: sell_score += 1

if trend_up: buy_score += 2
if trend_down: sell_score += 2

if candle_bull and vol_high: buy_score += 2
elif candle_bull: buy_score += 1
if not candle_bull and vol_high: sell_score += 2
elif not candle_bull: sell_score += 1

if rsi_m15 > 50: buy_score += 1
if rsi_m15 < 50: sell_score += 1

if price > ema20: buy_score += 1
if price < ema20: sell_score += 1

local_high = max(c['high'] for c in m5[-10:])
local_low = min(c['low'] for c in m5[-10:])
if price > local_high - atr: sell_score += 1
if price < local_low + atr: buy_score += 1

print(f"Buy Score: {buy_score} | Sell Score: {sell_score}")

# ENTRY FILTERS (current as of 29.05.2026)
can_buy = (buy_score >= sell_score + 3 and
           rsi_m15 <= 55 and
           not fatigued and
           price >= ema20)  # price below EMA20 = no BUY

can_sell = (sell_score >= buy_score + 3)

action = "HOLD"
entry, sl, tp = 0, 0, 0

if can_buy and not can_sell:
    action = "BUY"
    entry = ask
    sl = round(entry - atr * 1.5, 2)
    tp = round(entry + atr * 2, 2)
elif can_sell and not can_buy:
    action = "SELL"
    entry = bid
    sl = round(entry + atr * 1.5, 2)
    tp = round(entry - atr * 2, 2)
elif can_buy and can_sell:
    action = "HOLD"
    print("Both signals — skipping (conflict)")
else:
    print(f"HOLD reasons: buy_gap={buy_score >= sell_score + 3} m15_filter={rsi_m15 <= 55} fatigue={not fatigued} price_above_ema20={price >= ema20} sell_gap={sell_score >= buy_score + 3}")

print(f"Decision: {action}")
if action in ("BUY", "SELL"):
    print(f"Entry: {entry} | SL: {sl} | TP: {tp} | Risk: {round(abs(entry-sl)*10*0.03, 2)}$")

    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.03,
        "type": order_type,
        "price": entry,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123001,
        "comment": f"Scalp {action} {datetime.now().strftime('%H%M')}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(req)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"OPENED! Ticket: {result.order} @ {result.price}")
    else:
        comment = result.comment if result else str(mt5.last_error())
        print(f"Failed: {comment}")
elif action == "HOLD":
    print(f"BUY zone: {round(local_low,2)}-{round(local_low+atr,2)} | M15 RSI must be ≤55")
    print(f"SELL zone: {round(local_high-atr,2)}-{round(local_high,2)}")

mt5.shutdown()
