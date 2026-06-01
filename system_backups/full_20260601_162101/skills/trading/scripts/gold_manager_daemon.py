"""GOLD DAEMON v5 — ФИНАЛЬНАЯ ВЕРСИЯ.
БЕЗ БЕЗУБЫТКА. Только трейлинг.
Проверка каждые 10 сек. Один источник правды — .gold_state.json"""
import MetaTrader5 as mt5
import time, os, json
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(__file__), '.gold_state.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), '.gold_manager.log')
path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

TRAIL_ACTIVATE = 100
TRAIL_OFFSET = 50
TRAIL_STEP = 60
CHECK_EVERY = 10

last_ticket = None
trail_level = 0

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts}] {msg}\n")

def write_state(state_type, data):
    data["_type"] = state_type
    data["_time"] = datetime.now().strftime("%H:%M:%S")
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f)

def modify(ticket, new_sl, tp):
    try: mt5.shutdown()
    except: pass
    time.sleep(0.1)
    if not mt5.initialize(path=path, timeout=8000):
        return False
    r = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl, "tp": tp})
    mt5.shutdown()
    return r and r.retcode == mt5.TRADE_RETCODE_DONE

def check():
    global last_ticket, trail_level
    try: mt5.shutdown()
    except: pass
    time.sleep(0.1)
    if not mt5.initialize(path=path, timeout=8000):
        return
    mt5.symbol_select(symbol, True)
    pos = mt5.positions_get(symbol=symbol)
    acc = mt5.account_info()
    if not acc:
        mt5.shutdown()
        return

    if pos and len(pos) > 0:
        for p in pos:
            t = p.ticket; tp = "B" if p.type == 0 else "S"
            entry = p.price_open; cur = p.price_current
            pf = round(p.profit, 2); sl = p.sl; tp_price = p.tp
            pts = round((cur - entry)/.01, 1) if tp == "B" else round((entry - cur)/.01, 1)
            icon = "🟢" if pf >= 0 else "🔴"

            if t != last_ticket:
                write_state("open", {
                    "title": f"🆕 {tp}UY GOLD #{t}",
                    "body": f"Вход: {entry} | SL: {sl} | TP: {tp_price} | Баланс: ${acc.balance:.2f}"
                })
                log(f"🆕 #{t} {tp}UY @ {entry} SL={sl} TP={tp_price} Bal=${acc.balance:.2f}")
                last_ticket = t; trail_level = 0

            # ТРЕЙЛИНГ — ТОЛЬКО ЭТО, БЕЗ БЕЗУБЫТКА!
            if pts >= TRAIL_ACTIVATE:
                lvl = int(pts // TRAIL_STEP) * TRAIL_STEP
                if lvl > trail_level:
                    nsl = round(cur - TRAIL_OFFSET*.01, 2) if tp == "B" else round(cur + TRAIL_OFFSET*.01, 2)
                    if (tp == "B" and nsl > sl) or (tp == "S" and nsl < sl):
                        if modify(t, nsl, tp_price):
                            fix = round((nsl - entry)/.01, 1) if tp == "B" else round((entry - nsl)/.01, 1)
                            write_state("trail", {
                                "title": f"🏃 TRAIL #{t}: SL={nsl}",
                                "body": f"Зафиксировано +{fix}pts (${fix*10:.2f})"
                            })
                            log(f"🏃 #{t} TRAIL SL={nsl} fix=+{fix}pts")
                            trail_level = lvl

            log(f"{icon} #{t}: {pts}pts ${pf:.2f} SL={sl}")
    else:
        if last_ticket is not None:
            write_state("closed", {
                "title": f"✅ СДЕЛКА ЗАКРЫТА",
                "body": f"Баланс: ${acc.balance:.2f} | Сессия: +${round(acc.balance-1550, 2):.2f}"
            })
            log(f"✅ #{last_ticket} ЗАКРЫТА Bal=${acc.balance:.2f} Sess=+${round(acc.balance-1550, 2):.2f}")
            last_ticket = None; trail_level = 0

    mt5.shutdown()

log(f"🚀 GOLD DAEMON v5 STARTED PID={os.getpid()}")
log(f"   ЧИСТЫЙ ТРЕЙЛИНГ | Activate@{TRAIL_ACTIVATE}pts Step@{TRAIL_STEP} Offset@{TRAIL_OFFSET}")
write_state("ready", {"title": "🟢 Демон v5 запущен", "body": "Чистый трейлинг. Жду сделок."})

while True:
    try: check()
    except Exception as e: log(f"❌ {e}")
    time.sleep(CHECK_EVERY)
