"""GOLD DAEMON v8 — PARTIAL CLOSE + ТРЕЙЛИНГ
- Partial Close 50% @ +100pts
- Трейлинг 80/100/80
- Heartbeat каждые 30 сек
- PID-файл + watchdog
- Авто-реконнект MT5"""
import MetaTrader5 as mt5
import time, os, json, sys, atexit
from datetime import datetime

WORKDIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(WORKDIR, ".gold_state.json")
LOG_FILE = os.path.join(WORKDIR, ".gold_manager.log")
PID_FILE = os.path.join(WORKDIR, ".gold_daemon.pid")
HEARTBEAT_FILE = os.path.join(WORKDIR, ".gold_heartbeat.json")
LOCK_FILE = os.path.join(WORKDIR, ".gold_daemon.lock")
path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

TRAIL_ACTIVATE = 80
TRAIL_OFFSET = 100
TRAIL_STEP = 80
PARTIAL_AT = 100  # partial close at +100pts
CHECK_EVERY = 10
MAX_RETRIES = 3
HEARTBEAT_INTERVAL = 30

last_ticket = None
trail_level = 0
partial_closed = False
last_heartbeat = 0
daemon_lock_fd = None
SINGLE_INSTANCE_HEARTBEAT_MAX_AGE = 120

def _pid_alive(pid):
    try: os.kill(int(pid), 0); return True
    except: return False

def _read_json(p):
    try:
        with open(p) as f: return json.load(f)
    except: return {}

def _acquire_lock_once():
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.write(fd, str(os.getpid()).encode())
        return fd
    except FileExistsError:
        try:
            owner_raw = open(LOCK_FILE).read().strip()
            owner_pid = int(owner_raw) if owner_raw else 0
            if not owner_pid or not _pid_alive(owner_pid):
                os.remove(LOCK_FILE)
                fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(fd, str(os.getpid()).encode())
                return fd
        except: pass
        return None
    except: return None

def _release_lock():
    global daemon_lock_fd
    try:
        if daemon_lock_fd: os.close(daemon_lock_fd)
    except: pass
    daemon_lock_fd = None
    try:
        if os.path.exists(LOCK_FILE):
            owner = open(LOCK_FILE).read().strip()
            if owner == str(os.getpid()): os.remove(LOCK_FILE)
    except: pass

def ensure_single_instance():
    global daemon_lock_fd
    daemon_lock_fd = _acquire_lock_once()
    if daemon_lock_fd is None:
        log("Lock exists: exit duplicate")
        sys.exit(0)
    existing_pid = None
    if os.path.exists(PID_FILE):
        try: existing_pid = int(open(PID_FILE).read().strip())
        except: existing_pid = None
    if existing_pid and existing_pid != os.getpid() and _pid_alive(existing_pid):
        hb = _read_json(HEARTBEAT_FILE)
        hb_pid = int(hb.get("pid") or 0) if hb.get("pid") else 0
        hb_ts = float(hb.get("ts") or 0)
        hb_age = time.time() - hb_ts if hb_ts > 0 else 999999
        if hb_pid == existing_pid and hb_age <= SINGLE_INSTANCE_HEARTBEAT_MAX_AGE:
            log(f"Existing daemon pid={existing_pid} hb_age={hb_age:.1f}s. Exit duplicate.")
            sys.exit(0)
    with open(PID_FILE, "w") as f: f.write(str(os.getpid()))
    atexit.register(_release_lock)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, "a") as f: f.write(f"[{ts}] {msg}\n")

def write_state(t, data):
    data["_type"] = t
    data["_time"] = datetime.now().strftime("%H:%M:%S")
    with open(STATE_FILE, "w") as f: json.dump(data, f)

def hb():
    global last_heartbeat
    now = time.time()
    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        d = {"pid": os.getpid(), "time": datetime.now().strftime("%H:%M:%S"), "ts": now, "ticket": last_ticket}
        with open(HEARTBEAT_FILE, "w") as f: json.dump(d, f)
        last_heartbeat = now

def safe_mt5():
    for a in range(MAX_RETRIES):
        try: mt5.shutdown()
        except: pass
        time.sleep(1)
        try:
            if mt5.initialize(path=path, timeout=20000):
                time.sleep(0.3); return True
        except: pass
        log(f"MT5 init {a+1}/{MAX_RETRIES} failed")
        time.sleep(3)
    return False

def modify(ticket, new_sl, tp):
    for a in range(MAX_RETRIES):
        if not safe_mt5(): continue
        r = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": ticket, "sl": new_sl, "tp": tp})
        if r and r.retcode == mt5.TRADE_RETCODE_DONE:
            mt5.shutdown(); return True
        log(f"Modify {a+1} retcode={r.retcode if r else 'None'}")
        mt5.shutdown(); time.sleep(1)
    return False

def check():
    global last_ticket, trail_level, partial_closed
    if not safe_mt5():
        log("MT5 init failed"); return
    mt5.symbol_select(symbol, True)
    pos = mt5.positions_get(symbol=symbol)
    acc = mt5.account_info()
    if not acc: mt5.shutdown(); return
    if pos and len(pos) > 0:
        for p in pos:
            t = p.ticket; d = "B" if p.type == 0 else "S"
            entry = p.price_open; cur = p.price_current
            pf = round(p.profit, 2); sl = p.sl; tp = p.tp; vol = p.volume
            pts = round((cur - entry) / 0.01, 1) if d == "B" else round((entry - cur) / 0.01, 1)
            icon = chr(0x1f7e2) if pf >= 0 else chr(0x1f534)
            
            if t != last_ticket:
                write_state("open", {"title": f"NEW {d} GOLD #{t}", "body": f"Entry: {entry} SL: {sl} TP: {tp} Bal: ${acc.balance:.2f}"})
                log(f"NEW #{t} {d} @ {entry} SL={sl} TP={tp} Bal=${acc.balance:.2f}")
                last_ticket = t; trail_level = 0; partial_closed = False
            
            if not partial_closed and vol >= 0.03 and pts >= PARTIAL_AT:
                half = round(vol / 2, 2)
                cr = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": half,
                    "type": mt5.ORDER_TYPE_SELL if d == "B" else mt5.ORDER_TYPE_BUY,
                    "position": t, "price": cur, "deviation": 20, "magic": 123456,
                    "comment": "PARTIAL_100", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC})
                if cr and cr.retcode == mt5.TRADE_RETCODE_DONE:
                    partial_closed = True
                    fix = round((cur - entry) / 0.01, 1) if d == "B" else round((entry - cur) / 0.01, 1)
                    write_state("partial", {"title": f"PARTIAL #{t}: +{fix}pts", "body": f"Closed {half} lot @ {cur:.2f}"})
                    log(f"PARTIAL #{t} {half} @ {cur:.2f} fix=+{fix}pts")
                else:
                    log(f"Partial fail retcode={cr.retcode if cr else 'None'}")
            
            if pts >= TRAIL_ACTIVATE:
                lvl = int(pts // TRAIL_STEP) * TRAIL_STEP
                if lvl > trail_level:
                    nsl = round(cur - TRAIL_OFFSET * 0.01, 2) if d == "B" else round(cur + TRAIL_OFFSET * 0.01, 2)
                    if (d == "B" and nsl > sl) or (d == "S" and nsl < sl):
                        if modify(t, nsl, tp):
                            fix = round((nsl - entry) / 0.01, 1) if d == "B" else round((entry - nsl) / 0.01, 1)
                            write_state("trail", {"title": f"TRAIL #{t}: SL={nsl}", "body": f"Fixed +{fix}pts"})
                            log(f"TRAIL #{t} SL={nsl} fix=+{fix}pts")
                            trail_level = lvl
            log(f"{icon} #{t}: {pts}pts ${pf:.2f} SL={sl}")
    else:
        if last_ticket is not None:
            write_state("closed", {"title": "TRADE CLOSED", "body": f"Balance: ${acc.balance:.2f}"})
            log(f"CLOSED #{last_ticket} Bal=${acc.balance:.2f}")
            last_ticket = None; trail_level = 0
    mt5.shutdown()

ensure_single_instance()
log(f"GOLD DAEMON v8 STARTED PID={os.getpid()}")
log(f"  TRAIL {TRAIL_ACTIVATE}/{TRAIL_OFFSET}/{TRAIL_STEP} + PARTIAL {PARTIAL_AT}pts")
write_state("ready", {"title": "Daemon v8 ready", "body": "Trail 80/100/80 + Partial 50%@100pts"})
while True:
    try: check()
    except Exception as e: log(f"Error: {e}"); time.sleep(5)
    hb(); time.sleep(CHECK_EVERY)
