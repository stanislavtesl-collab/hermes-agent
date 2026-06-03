"""GOLD DAEMON v7 — НАДЁЖНАЯ ВЕРСИЯ
- Авто-реконнект MT5 (3 retry)
- Heartbeat каждые 30 сек (.gold_heartbeat.json)
- PID-файл + watchdog
- Только трейлинг (100/50/60), без безубытка
- Пишет в logfile каждую итерацию для отслеживания живости"""

import MetaTrader5 as mt5
import time, os, json, sys
import atexit
from datetime import datetime

WORKDIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(WORKDIR, '.gold_state.json')
LOG_FILE = os.path.join(WORKDIR, '.gold_manager.log')
PID_FILE = os.path.join(WORKDIR, '.gold_daemon.pid')
HEARTBEAT_FILE = os.path.join(WORKDIR, '.gold_heartbeat.json')
LOCK_FILE = os.path.join(WORKDIR, '.gold_daemon.lock')
path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

TRAIL_ACTIVATE = 100
TRAIL_OFFSET = 50
TRAIL_STEP = 60
CHECK_EVERY = 10
MAX_RETRIES = 3
HEARTBEAT_INTERVAL = 30  # каждые 30 сек пишем heartbeat

last_ticket = None
trail_level = 0
last_heartbeat = 0
daemon_lock_fd = None

SINGLE_INSTANCE_HEARTBEAT_MAX_AGE = 120  # sec

def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False

def _read_json(path_):
    try:
        with open(path_, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _acquire_lock_once():
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(fd, str(os.getpid()).encode('utf-8'))
        return fd
    except FileExistsError:
        # Recover from stale lock left by dead process.
        try:
            owner_raw = ''
            with open(LOCK_FILE, 'r') as f:
                owner_raw = (f.read() or '').strip()
            owner_pid = int(owner_raw) if owner_raw else 0
            if not owner_pid or not _pid_alive(owner_pid):
                os.remove(LOCK_FILE)
                fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(fd, str(os.getpid()).encode('utf-8'))
                return fd
        except Exception:
            pass
        return None
    except Exception:
        return None

def _release_lock():
    global daemon_lock_fd
    try:
        if daemon_lock_fd is not None:
            os.close(daemon_lock_fd)
    except Exception:
        pass
    daemon_lock_fd = None
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                owner = (f.read() or '').strip()
            if owner == str(os.getpid()):
                os.remove(LOCK_FILE)
    except Exception:
        pass

def ensure_single_instance():
    global daemon_lock_fd
    daemon_lock_fd = _acquire_lock_once()
    if daemon_lock_fd is None:
        log("🛑 Lock file exists: another daemon instance is starting/running. Exit duplicate.")
        sys.exit(0)

    existing_pid = None
    if os.path.exists(PID_FILE):
        try:
            existing_pid = int(open(PID_FILE, 'r').read().strip())
        except Exception:
            existing_pid = None

    if existing_pid and existing_pid != os.getpid() and _pid_alive(existing_pid):
        hb = _read_json(HEARTBEAT_FILE)
        hb_pid = int(hb.get('pid') or 0) if hb.get('pid') else 0
        hb_ts = float(hb.get('ts') or 0)
        hb_age = time.time() - hb_ts if hb_ts > 0 else 999999
        if hb_pid == existing_pid and hb_age <= SINGLE_INSTANCE_HEARTBEAT_MAX_AGE:
            log(f"🛑 Existing daemon detected pid={existing_pid} heartbeat_age={hb_age:.1f}s. Exit duplicate.")
            sys.exit(0)
        log(f"⚠️ Existing pid={existing_pid} without fresh heartbeat (age={hb_age:.1f}s). Replacing PID ownership.")

    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    atexit.register(_release_lock)


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{ts}] {msg}\n")

def write_state(state_type, data):
    data["_type"] = state_type
    data["_time"] = datetime.now().strftime("%H:%M:%S")
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f)

def heartbeat():
    global last_heartbeat
    now = time.time()
    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        hb = {
            "pid": os.getpid(),
            "time": datetime.now().strftime("%H:%M:%S"),
            "ts": now,
            "ticket": last_ticket
        }
        with open(HEARTBEAT_FILE, 'w') as f:
            json.dump(hb, f)
        last_heartbeat = now

def safe_mt5_init():
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

# Register PID (single-instance guard)
ensure_single_instance()

log(f"🚀 GOLD DAEMON v7 STARTED PID={os.getpid()}")
log(f"   ЧИСТЫЙ ТРЕЙЛИНГ | Activate@{TRAIL_ACTIVATE}pts Step@{TRAIL_STEP} Offset@{TRAIL_OFFSET}")
log(f"   HEARTBEAT every {HEARTBEAT_INTERVAL}s")
write_state("ready", {"title": "🟢 Демон v7 запущен", "body": "Чистый трейлинг + heartbeat. Жду сделок."})

# Main loop
while True:
    try:
        check()
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")
        time.sleep(5)
    heartbeat()  # обновляем heartbeat каждые HEARTBEAT_INTERVAL сек
    time.sleep(CHECK_EVERY)
