#!/usr/bin/env python3
"""
GOLD Executor v5.0 — для стратегии EMA10 M5 Crossover
- SL=80pts, TP=600pts
- Time Exit = 12 M5 свечей (1 час)
- Никакого reversal, scalp, partial close, ATR-адаптации
- Чистое исполнение: открыть → держать до SL/TP/TIME
"""
import MetaTrader5 as mt5
import json, time, os, sys
from datetime import datetime, timezone
from hermes_mt5_guard import initialize_and_assert, terminal_path, expected_account

# === CONFIG ===
SYMBOL = "GOLD"
MAGIC = 123464
LOT = 0.03
CHECK_INTERVAL = 3  # сек

# === Параметры стратегии ===
SL_PTS = 80
TP_PTS = 600
TIME_EXIT_SEC = 3600  # 1 час (12 M5 × 300сек)

# === HARD-CODED MT5 FXPRO ===
MT5_TERMINAL_PATH = terminal_path()
MT5_ACCOUNT = expected_account()

# === FILES ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIGNAL_FILE = os.path.join(BASE_DIR, ".gold_trade_signal.json")
TRAIL_FILE = os.path.join(BASE_DIR, ".universal_trail.json")
HEARTBEAT_FILE = os.path.join(BASE_DIR, ".gold_executor_heartbeat.json")
LOG_FILE = os.path.join(BASE_DIR, ".gold_executor_events.log")


def safe_val(val, default=0.0):
    if isinstance(val, np.ndarray):
        return float(val.item()) if val.size > 0 else default
    return float(val) if val is not None else default


def write_heartbeat():
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "pid": os.getpid(), "status": "running"}, f)
    except:
        pass


def log_event(event, data=None):
    try:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"{ts}|{event}"
        if data:
            entry += f"|{json.dumps(data)}"
        entry += "\n"
        with open(LOG_FILE, "a") as f:
            f.write(entry)
    except:
        pass


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# === MT5 INIT ===
def init_mt5():
    if not mt5.initialize(path=MT5_TERMINAL_PATH):
        log(f"MT5 init failed: {mt5.last_error()}")
        return False
    acc = mt5.account_info()
    if acc is None:
        log(f"No account info: {mt5.last_error()}")
        return False
    if int(acc.login) == MT5_ACCOUNT:
        log(f"MT5 connected. Login: {acc.login}, Balance: {acc.balance}")
        log_event("MT5_INIT", {"login": acc.login, "balance": acc.balance})
        return True
    log(f"Wrong account: {acc.login}; expected={MT5_ACCOUNT}. Refusing passwordless login/fallback.")
    log_event("MT5_ACCOUNT_MISMATCH", {"login": acc.login, "expected": MT5_ACCOUNT, "terminal": MT5_TERMINAL_PATH})
    return False


# === POSITION ===
def get_position(ticket):
    pos = mt5.positions_get(ticket=ticket)
    return pos[0] if pos else None


def get_our_positions():
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return []
    return [p for p in positions if p.magic == MAGIC]


# === OPEN ===
def open_trade(signal):
    action = signal.get("action", "").upper()
    if action not in ("BUY", "SELL"):
        return False
    
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        return False
    
    current_price = tick.bid if action == "SELL" else tick.ask
    
    sl_dist = SL_PTS * 0.01
    tp_dist = TP_PTS * 0.01
    
    if action == "BUY":
        sl = round(current_price - sl_dist, 2)
        tp = round(current_price + tp_dist, 2)
    else:
        sl = round(current_price + sl_dist, 2)
        tp = round(current_price - tp_dist, 2)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": current_price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": MAGIC,
        "comment": "v5.0",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == 10009:
        log(f"OPEN {action} #{result.order} @ {current_price:.2f} SL={sl} TP={tp}")
        log_event("OPEN", {"ticket": result.order, "action": action, "price": round(current_price, 2), "sl": sl, "tp": tp})
        
        # Сохраняем для time exit
        trail_data = {
            "ticket": result.order,
            "action": action,
            "entry_price": current_price,
            "entry_time": time.time(),
            "sl": sl,
            "tp": tp,
        }
        with open(TRAIL_FILE, "w") as f:
            json.dump(trail_data, f)
        return True
    else:
        log(f"OPEN failed: {result}")
        return False


# === CLOSE ===
def close_position(ticket, reason=""):
    pos = get_position(ticket)
    if not pos:
        return False
    
    try:
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick:
            # ИСПРАВЛЕНО: правильная цена для close
            current_price = tick.bid if pos.type == 0 else tick.ask
            profit_pts = (current_price - pos.price_open) / 0.01 if pos.type == 0 else (pos.price_open - current_price) / 0.01
            profit_pts = round(profit_pts, 1)
        else:
            profit_pts = 0
        
        icon = "🔴" if profit_pts < 0 else "🟢"
        log(f"{icon} #{ticket} CLOSE: {profit_pts:.0f}pts (${pos.profit:.2f}) | {reason}")
        log_event("CLOSE", {"ticket": ticket, "reason": reason, "profit_pts": profit_pts, "profit_usd": round(pos.profit, 2) if pos.profit else 0})
    except:
        pass
    
    close_type = mt5.ORDER_TYPE_BUY if pos.type == 1 else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(pos.symbol).ask if pos.type == 1 else mt5.symbol_info_tick(pos.symbol).bid
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": close_type,
        "position": pos.ticket,
        "price": price,
        "deviation": 20,
        "magic": pos.magic,
        "comment": reason or "CLOSE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == 10009:
        log(f"#{ticket} closed ({reason})")
        try:
            if os.path.exists(TRAIL_FILE):
                os.remove(TRAIL_FILE)
        except:
            pass
        return True
    return False


# === TIME EXIT CHECK ===
def check_time_exit():
    """Закрывает сделки которые держатся больше TIME_EXIT_SEC."""
    try:
        if not os.path.exists(TRAIL_FILE):
            return
        
        with open(TRAIL_FILE) as f:
            trail = json.load(f)
        
        ticket = trail.get("ticket")
        entry_time = trail.get("entry_time", 0)
        
        if time.time() - entry_time > TIME_EXIT_SEC:
            pos = get_position(ticket)
            if pos:
                close_position(ticket, f"TIME_EXIT_{TIME_EXIT_SEC//60}min")
    except:
        pass


# === SIGNAL HANDLER ===
def read_signal():
    try:
        if os.path.exists(SIGNAL_FILE):
            with open(SIGNAL_FILE) as f:
                return json.load(f)
    except:
        pass
    return None


def delete_signal():
    try:
        if os.path.exists(SIGNAL_FILE):
            os.remove(SIGNAL_FILE)
    except:
        pass


# === MAIN ===
def main():
    log("=" * 55)
    log("GOLD Executor v5.0 — EMA10 M5 Crossover")
    log(f"  SL={SL_PTS}pts TP={TP_PTS}pts TIME_EXIT={TIME_EXIT_SEC//60}min")
    log("  No reversal / no scalp / no partial")
    log("=" * 55)
    
    if not init_mt5():
        return
    
    write_heartbeat()
    
    while True:
        try:
            write_heartbeat()
            
            positions = get_our_positions()
            
            # Time exit check
            if positions:
                check_time_exit()
                positions = get_our_positions()  # refresh
            
            # Если нет позиций — проверяем сигнал
            if not positions:
                signal = read_signal()
                if signal:
                    action = signal.get("action", "")
                    log(f"Signal: {action} @ {signal.get('price', 0)}")
                    if open_trade(signal):
                        delete_signal()
                    else:
                        delete_signal()
        
        except Exception as e:
            log(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
