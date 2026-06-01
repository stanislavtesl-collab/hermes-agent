"""GOLD trade MANAGER v2 - fixed trailing logic, works correctly."""
import MetaTrader5 as mt5
import time, os, json
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(__file__), '.gold_manager_history.json')
path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

# === CONFIG ===
BE_OFFSET_PTS = 15       # Безубыток: SL = entry + 15pts
TRAIL_OFFSET_PTS = 40    # Трейлинг: SL = price - 40pts
TRAIL_STEP_PTS = 50      # Шаг подтяжки: каждые +50pts цены

def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"last_ticket": None, "profit": 0, "be_done": False, "last_trail_price": 0}

def save_history(h):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(h, f)
    except:
        pass

def modify_position(ticket, new_sl, tp):
    req = {"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl, "tp": tp}
    return mt5.order_send(req)

def check():
    try: mt5.shutdown()
    except: pass
    time.sleep(0.3)
    
    if not mt5.initialize(path=path, timeout=15000):
        return {"error": str(mt5.last_error())}
    
    mt5.symbol_select(symbol, True)
    positions = mt5.positions_get(symbol=symbol)
    si = mt5.symbol_info_tick(symbol)
    now = datetime.now().strftime("%H:%M:%S")
    
    history = load_history()
    msgs = []
    
    if positions and len(positions) > 0:
        for pos in positions:
            ticket = pos.ticket
            ptype = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            entry = pos.price_open
            current = pos.price_current
            profit = round(pos.profit, 2)
            sl = pos.sl
            tp = pos.tp
            
            points = round((current - entry) / 0.01, 1) if ptype == "BUY" else round((entry - current) / 0.01, 1)
            
            # NEW POSITION
            if history["last_ticket"] != ticket:
                msgs.append(f"🆕 НОВАЯ {ptype} #{ticket} @ {entry} | SL={sl} TP={tp}")
                history = {"last_ticket": ticket, "profit": profit, "be_done": False, "last_trail_price": 0}
            
            # === BREAKEVEN (30+ pts) ===
            if points >= 30 and not history.get("be_done", False):
                be_sl = round(entry + BE_OFFSET_PTS * 0.01, 2)
                if sl < be_sl:
                    r = modify_position(ticket, be_sl, tp)
                    if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                        msgs.append(f"🔒 BREAKEVEN! SL={be_sl} (+{BE_OFFSET_PTS}pts)")
                        history["be_done"] = True
                    else:
                        msgs.append(f"⚠️ BE failed")
            
            # === TRAILING (100+ pts, then every 50 pts) ===
            if points >= 100:
                trail_price = int(points // TRAIL_STEP_PTS) * TRAIL_STEP_PTS  # 100, 150, 200...
                
                if trail_price > history.get("last_trail_price", 0):
                    trail_sl = round(current - TRAIL_OFFSET_PTS * 0.01, 2)
                    if trail_sl > sl:
                        r = modify_position(ticket, trail_sl, tp)
                        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
                            fixed_pts = round((trail_sl - entry) / 0.01, 1)
                            msgs.append(f"🏃 TRAIL! SL={trail_sl} | фикс +{fixed_pts}pts (${fixed_pts*10:.2f})")
                            history["last_trail_price"] = trail_price
            else:
                history["last_trail_price"] = 0
            
            # Summary
            status = "🟢" if profit >= 0 else "🔴"
            trail_note = f" (TRAIL)" if points >= 100 else ""
            msgs.append(f"  {status} #{ticket}: {ptype} +{points}pts | P&L=${profit:.2f} | SL={sl}{trail_note} | TP={tp}")
            history["profit"] = profit
    
    else:
        # No position
        if history["last_ticket"] is not None:
            fin_prof = history.get("profit", 0)
            balance = mt5.account_info().balance if mt5.account_info() else 0
            msgs.append(f"✅✅✅ ПОЗИЦИЯ #{history['last_ticket']} ЗАКРЫТА! P&L: ${fin_prof:.2f} | Баланс: ${balance:.2f}")
            history = {"last_ticket": None, "profit": 0, "be_done": False, "last_trail_price": 0}
    
    save_history(history)
    mt5.shutdown()
    
    if not msgs:
        return None
    return {"time": now, "bid": si.bid if si else 0, "ask": si.ask if si else 0, "messages": msgs}

result = check()
if result:
    print(json.dumps(result, indent=2, ensure_ascii=False))
