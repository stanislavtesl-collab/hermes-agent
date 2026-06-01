"""GOLD trade continuous monitor. Run once every tick via cron.
Checks open positions and outputs ONLY when something interesting happens.
Silent = nothing to report = all good."""
import MetaTrader5 as mt5
import time, os, json
from datetime import datetime

# History tracker - last reported state
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '.gold_monitor_history.json')

path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"last_profit": 0, "last_ticket": None, "last_sl": None, "breakeven_done": False, "trail_done": False}

def save_history(h):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(h, f)
    except:
        pass

def check():
    try:
        mt5.shutdown()
    except:
        pass
    time.sleep(0.3)
    
    if not mt5.initialize(path=path, timeout=15000):
        return {"error": str(mt5.last_error())}
    
    mt5.symbol_select(symbol, True)
    positions = mt5.positions_get(symbol=symbol)
    
    now = datetime.now().strftime("%H:%M:%S")
    si = mt5.symbol_info_tick(symbol)
    bid = si.bid if si else 0
    ask = si.ask if si else 0
    
    history = load_history()
    alerts = []
    actions = []
    
    if positions and len(positions) > 0:
        for pos in positions:
            ticket = pos.ticket
            ptype = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            entry = pos.price_open
            current = pos.price_current
            profit = round(pos.profit, 2)
            sl = pos.sl
            tp = pos.tp
            
            if ptype == "BUY":
                points = round((current - entry) / 0.01, 1)
            else:
                points = round((entry - current) / 0.01, 1)
            
            # Detect new position
            if history.get("last_ticket") != ticket:
                alerts.append(f"🆕 Новая позиция {ptype} #{ticket} @ {entry}")
                history["last_ticket"] = ticket
                history["breakeven_done"] = False
                history["trail_done"] = False
            
            # BREAKEVEN at +20 points
            if points >= 20 and not history.get("breakeven_done"):
                if ptype == "BUY":
                    new_sl = round(entry + 0.10, 2)  # entry + 10 points
                    if sl < new_sl:
                        actions.append(f"🔒 BREAKEVEN: подними SL до {new_sl}")
                        history["breakeven_done"] = True
            
            # TRAIL at +50 points
            if points >= 50 and not history.get("trail_done"):
                if ptype == "BUY":
                    trail_sl = round(current - 2.50, 2)  # trail by 250 points
                    if sl < trail_sl:
                        actions.append(f"🏃 TRAIL: подними SL до {trail_sl}")
                        history["trail_done"] = True
            
            # Profit change alert
            prev_profit = history.get("last_profit", 0)
            profit_change = profit - prev_profit
            
            # TP close alert
            if tp and abs(current - tp) / 0.01 < 10:
                alerts.append(f"🎯 TP РЯДОМ! Текущая: {current}, TP: {tp}")
            
            # SL danger
            if ptype == "BUY":
                dist_to_sl = abs(current - sl) / 0.01 if sl else 999
            else:
                dist_to_sl = abs(current - sl) / 0.01 if sl else 999
            
            if dist_to_sl < 10:
                alerts.append(f"⚠️ SL В ОПАСНОСТИ! Всего {dist_to_sl:.0f} pts до SL")
            
            # Position closed detection
            history["last_profit"] = profit
            history["last_sl"] = sl
            
            # Summary line
            alerts.append(f"{'🟢' if profit >= 0 else '🔴'} {ptype} GOLD #{ticket}: +{points}pts | P&L=${profit:.2f} | SL={sl} | TP={tp}")
    else:
        # No positions
        if history.get("last_ticket") is not None:
            # Position was closed between checks
            final_profit = history.get("last_profit", 0)
            alerts.append(f"✅ ✅ ✅ ПОЗИЦИЯ ЗАКРЫТА! Финальный P&L: ${final_profit:.2f}")
            # Reset history
            history = {"last_profit": 0, "last_ticket": None, "last_sl": None, "breakeven_done": False, "trail_done": False}
        # Silent if no positions and nothing changed
    
    save_history(history)
    mt5.shutdown()
    
    if not alerts and not actions:
        return None  # Silent - nothing to report
    
    result = {"time": now, "bid": bid, "ask": ask}
    if alerts:
        result["alerts"] = alerts
    if actions:
        result["actions"] = actions
    return result

result = check()
if result:
    print(json.dumps(result, indent=2, ensure_ascii=False))
# If result is None, output nothing -> silent mode
