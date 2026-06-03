"""
GOLD Monitor M15 — Position Swing
Следит за H4→H1→M15, даёт сигнал при входе по тренду
Цель: 200-300pts движения
Пишет .gold_trade_signal_m15.json — Executor забирает
Не использует Twelve Data, только MT5
"""
import MetaTrader5 as mt5, time, os, sys, json
from datetime import datetime, timezone
from hermes_mt5_guard import initialize_and_assert, terminal_path, expected_account

sys.path.insert(0, "/c/Program Files/Python312/Lib/site-packages")

MT5_PATH = terminal_path()
MT5_ACCOUNT = expected_account()
SIGNAL_FILE = "C:/Users/Administrator/Desktop/FxPro/.gold_trade_signal_m15.json"
HEARTBEAT_FILE = "C:/Users/Administrator/Desktop/FxPro/.monitor_m15_heartbeat.json"
SYMBOL = "GOLD"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def get_data():
    """Загружаем M15, H1, H4 данные"""
    r15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 120)
    r1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 60)
    r4 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H4, 0, 60)
    
    # numpy array: проверка через size вместо is None
    def is_bad(rates, min_len):
        return rates is None or (hasattr(rates, 'size') and rates.size == 0) or len(rates) < min_len
    
    if is_bad(r15, 60):
        return None, None, None
    if is_bad(r1, 30):
        return None, None, None
    if is_bad(r4, 30):
        return None, None, None
    
    return r15, r1, r4

def calc_trend(rates, sma_periods=(20, 50)):
    """Определяем тренд по SMA"""
    c = [r[4] for r in rates]
    if len(c) < max(sma_periods):
        return None
    sma_fast = sum(c[-sma_periods[0]:]) / sma_periods[0]
    sma_slow = sum(c[-sma_periods[1]:]) / sma_periods[1]
    last_c = c[-1]
    
    if sma_fast > sma_slow:
        return "BULLISH"
    elif sma_fast < sma_slow:
        return "BEARISH"
    return "SIDEWAYS"

def calc_rsi(rates, period=14):
    c = [r[4] for r in rates]
    if len(c) < period + 1:
        return 50
    g = l = 0
    for i in range(1, period + 1):
        d = c[-i] - c[-i-1]
        if d > 0: g += d
        else: l -= d
    if l == 0:
        return 100
    rs = (g / period) / (l / period)
    return 100 - 100 / (1 + rs)

def calc_atr(rates, period=14):
    if len(rates) < period + 1:
        return 5.0
    tr_s = 0
    for i in range(1, period + 1):
        r = rates[-i]
        pc = rates[-i-1][4]
        tr = max(r[2] - r[3], abs(r[2] - pc), abs(r[3] - pc))
        tr_s += tr
    return tr_s / period

def find_swing_low(rates, lookback=20):
    return min(r[3] for r in rates[-lookback:])

def find_swing_high(rates, lookback=20):
    return max(r[2] for r in rates[-lookback:])

def check_entry():
    """Проверяем все ТФ на точку входа"""
    r15, r1, r4 = get_data()
    if r15 is None:
        return None
    
    c15 = [r[4] for r in r15]
    h15 = [r[2] for r in r15]
    l15 = [r[3] for r in r15]
    o15 = [r[1] for r in r15]
    last_c = c15[-1]
    prev_c = c15[-2]
    last_o = o15[-1]
    
    # Тренды
    trend_h4 = calc_trend(r4)
    trend_h1 = calc_trend(r1)
    trend_m15 = calc_trend(r15)
    
    # RSI M15
    rsi_m15 = calc_rsi(r15)
    
    # ATR M15 для SL
    atr_m15 = calc_atr(r15)
    
    # Swing уровни M15
    swing_l = find_swing_low(r15)
    swing_h = find_swing_high(r15)
    
    # H1 поддержка/сопротивление
    c_h1 = [r[4] for r in r1]
    h_h1 = [r[2] for r in r1]
    l_h1 = [r[3] for r in r1]
    h1_swing_l = min(l_h1[-30:])
    h1_swing_h = max(h_h1[-30:])
    h1_sma20 = sum(c_h1[-20:]) / 20
    h1_sma50 = sum(c_h1[-min(50, len(c_h1)):]) / min(50, len(c_h1))
    
    action = None
    reason = ""
    tp_pts = 250  # цель по умолчанию
    sl_pts = 0
    
    # === BUY сетап ===
    if trend_h4 == "BULLISH":
        # H4 бычий — ищем BUY
        # H1 подтверждает: цена откатила к SMA50 или поддержке
        h1_bull_ok = (last_c <= h1_sma50 + 5.0) or (last_c <= h1_swing_l + 8.0)
        # M15: разворот от поддержки
        m15_bull = last_c > prev_c and (last_c - l15[-1]) > (h15[-1] - last_c)
        m15_oversold = rsi_m15 < 35
        
        if trend_h1 in ("BULLISH", "SIDEWAYS") and (m15_bull or m15_oversold):
            action = "BUY"
            # SL за swing low M15 минус 10pts
            sl_price = round(swing_l - 0.10, 2)
            sl_pts = round((last_c - sl_price) * 100)
            # TP = 200-250pts
            tp_price = round(last_c + 2.50, 2)
            reason = f"H4={trend_h4} H1={trend_h1} RSI={rsi_m15:.0f} M15 разворот от {swing_l:.2f}"
    
    # === SELL сетап ===
    if action is None and trend_h4 == "BEARISH":
        # H4 медвежий — ищем SELL
        h1_bear_ok = (last_c >= h1_sma50 - 5.0) or (last_c >= h1_swing_h - 8.0)
        m15_bear = last_c < prev_c and (h15[-1] - last_c) > (last_c - l15[-1])
        m15_overbought = rsi_m15 > 65
        
        if trend_h1 in ("BEARISH", "SIDEWAYS") and (m15_bear or m15_overbought):
            action = "SELL"
            sl_price = round(swing_h + 0.10, 2)
            sl_pts = round((sl_price - last_c) * 100)
            tp_price = round(last_c - 2.50, 2)
            reason = f"H4={trend_h4} H1={trend_h1} RSI={rsi_m15:.0f} M15 разворот от {swing_h:.2f}"
    
    if action:
        sl_risk = sl_pts * 0.03  # risk for 0.03 lot
        signal = {
            "action": action,
            "symbol": SYMBOL,
            "price": round(last_c, 2),
            "lot": 0.03,
            "sl": round(sl_price, 2),
            "tp": round(tp_price, 2),
            "sl_pts": sl_pts,
            "tp_pts": tp_pts,
            "trailing_offset": 30,
            "trailing_step": 10,
            "partial_close_pts": None,
            "partial_close_fraction": None,
            "reason": reason,
            "trend_h4": trend_h4,
            "trend_h1": trend_h1,
            "rsi_m15": round(rsi_m15, 1),
            "swing_low_m15": round(swing_l, 2),
            "swing_high_m15": round(swing_h, 2),
            "atr_m15": round(atr_m15, 2),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "source": "monitor_m15",
        }
        return signal
    return None

def heartbeat():
    hb = {"last_check": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()}
    with open(HEARTBEAT_FILE, "w") as f:
        json.dump(hb, f)

if __name__ == "__main__":
    log("🚀 Monitor M15 Position Swing STARTED")
    log("H4→H1→M15 trend filter, TP=200-250pts, no partial close")
    log(f"Signal file: {SIGNAL_FILE}")
    log("-" * 50)
    
    try:
        acc = initialize_and_assert(timeout=15000)
    except Exception as e:
        log(f"MT5 pinned init failed: {e}")
        sys.exit(1)
    mt5.symbol_select(SYMBOL, True)
    log(f"MT5 connected, account: {acc.login}")
    
    while True:
        heartbeat()
        try:
            tick = mt5.symbol_info_tick(SYMBOL)
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            
            # Не шлём сигнал если уже есть позиция M15
            positions = mt5.positions_get(symbol=SYMBOL) or []
            # Ищем позицию с magic M15
            has_m15_pos = any(p.magic == 123463 for p in positions)
            
            if not has_m15_pos:
                signal = check_entry()
                if signal:
                    log(f">>> SIGNAL {signal['action']} @ {signal['price']} | {signal['reason']}")
                    log(f"    SL={signal['sl']} ({signal['sl_pts']}pts) TP={signal['tp']} ({signal['tp_pts']}pts)")
                    with open(SIGNAL_FILE, "w") as f:
                        json.dump(signal, f)
                else:
                    r15, r1, r4 = get_data()
                    if r15:
                        trend_h4 = calc_trend(r4)
                        trend_h1 = calc_trend(r1)
                        rsi = calc_rsi(r15)
                        c15 = [r[4] for r in r15]
                        log(f"No signal | {trend_h4}/{trend_h1} | ${c15[-1]:.2f} | RSI={rsi:.0f}")
                    else:
                        log(f"No signal | ${tick.bid:.2f}")
            else:
                log(f"Position active | skip signal check")
            
        except Exception as e:
            log(f"Error: {e}")
        
        time.sleep(10)
