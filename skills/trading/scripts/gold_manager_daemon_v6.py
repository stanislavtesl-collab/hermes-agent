"""GOLD DAEMON v6 — СТАБИЛЬНАЯ ВЕРСИЯ
- Авто-реконнект при падении MT5
- Retry до 3х раз при ошибках
- PID-файл для обнаружения
- Только трейлинг, без безубытка
- Проверка каждые 10 сек"""

import MetaTrader5 as mt5
import time, os, json, sys
from datetime import datetime

WORKDIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(WORKDIR, '.gold_state.json')
LOG_FILE = os.path.join(WORKDIR, '.gold_manager.log')
PID_FILE = os.path.join(WORKDIR, '.gold_daemon.pid')
path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

TRAIL_ACTIVATE = 100
TRAIL_OFFSET = 50
TRAIL_STEP = 60
CHECK_EVERY = 10
MAX_RETRIES = 3

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

def safe_mt5_init():
    """Инициализация MT5 с retry"""
    for attempt in range(MAX_RETRIES):
        try:
            mt5.shutdown()
        except:
            pass
        time.sleep(0.5)
        if mt5.initialize(path=path, timeout=15000):
            return True
        log(f"⚠️ MT5 init attempt {attempt+1}/{MAX_RETRIES} failed")
        time.sleep(2)
    return False

def modify(ticket, new_sl, tp):
    """Изменить SL/TP с retry"""
    for attempt in range(MAX_RETRIES):
        if not safe_mt5_init():
            continue
        r = mt5.order_send({
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": tp
        })
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            mt5.shutdown()
            return True
        log(f"⚠️ Modify attempt {attempt+1} retcode={r.retcode if r else 'None'}")
        mt5.shutdown()
        time.sleep(1)
    return False

def check():
    global last_ticket, trail_level
    
    if not safe_mt5_init():
        log("❌ MT5 init failed after all retries")
        return
    
    mt5.symbol_select(symbol, True)
    pos = mt5.positions_get(symbol=symbol)
    acc = mt5.account_info()
    
    if not acc:
        mt5.shutdown()
        return
    
    if pos and len(pos) > 0:
        for p in pos:
            t = p.ticket
            tp_dir = "B" if p.type == 0 else "S"
            entry = p.price_open
            cur = p.price_current
            pf = round(p.profit, 2)
            sl = p.sl
            tp_price = p.tp
            pts = round((cur - entry) / 0.01, 1) if tp_dir == "B" else round((entry - cur) / 0.01, 1)
            icon = "🟢" if pf >= 0 else "🔴"

            if t != last_ticket:
                write_state("open", {
                    "title": f"🆕 {tp_dir}UY GOLD #{t}",
                    "body": f"Вход: {entry} | SL: {sl} | TP: {tp_price} | Баланс: ${acc.balance:.2f}"
                })
                log(f"🆕 #{t} {tp_dir}UY @ {entry} SL={sl} TP={tp_price} Bal=${acc.balance:.2f}")
                last_ticket = t
                trail_level = 0

            # Трейлинг — только это, без безубытка
            if pts >= TRAIL_ACTIVATE:
                lvl = int(pts // TRAIL_STEP) * TRAIL_STEP
                if lvl > trail_level:
                    nsl = round(cur - TRAIL_OFFSET * 0.01, 2) if tp_dir == "B" else round(cur + TRAIL_OFFSET * 0.01, 2)
                    if (tp_dir == "B" and nsl > sl) or (tp_dir == "S" and nsl < sl):
                        if modify(t, nsl, tp_price):
                            fix = round((nsl - entry) / 0.01, 1) if tp_dir == "B" else round((entry - nsl) / 0.01, 1)
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
                "body": f"Баланс: ${acc.balance:.2f} | Сессия: +${round(acc.balance - 1550, 2):.2f}"
            })
            log(f"✅ #{last_ticket} ЗАКРЫТА Bal=${acc.balance:.2f} Sess=+${round(acc.balance - 1550, 2):.2f}")
            last_ticket = None
            trail_level = 0

    mt5.shutdown()

# Register PID
with open(PID_FILE, 'w') as f:
    f.write(str(os.getpid()))

log(f"🚀 GOLD DAEMON v6 STARTED PID={os.getpid()}")
log(f"   ЧИСТЫЙ ТРЕЙЛИНГ | Activate@{TRAIL_ACTIVATE}pts Step@{TRAIL_STEP} Offset@{TRAIL_OFFSET}")
write_state("ready", {"title": "🟢 Демон v6 запущен", "body": "Чистый трейлинг. Жду сделок."})

# Main loop
while True:
    try:
        check()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        time.sleep(5)  # Пауза перед перезапуском цикла
    time.sleep(CHECK_EVERY)
