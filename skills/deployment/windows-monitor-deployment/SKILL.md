---
name: windows-monitor-deployment
description: >-
  Deploy and troubleshoot MT5-connected Python monitors/executors on Windows
  (Git-Bash / MINGW64 environment). Covers: rate-limit handling for Twelve Data,
  MT5 initialization pitfalls, background process management, bat-file launcher patterns,
  and the monitor→signal→executor architecture.
tags: [windows, mt5, deployment, twelve-data, rate-limit, git-bash, executor]
related_skills: [gold-scalp-self-learning]
---

# Windows Monitor Deployment (MT5 + Twelve Data)

## Architecture: Monitor → Signal File → Executor

**Two deployment modes:**

### Mode A: Twelve Data Monitor (original)
Monitor reads Twelve Data API, writes signal JSON. No MT5 dependency.

### Mode B: MT5 Direct Monitor (recommended for live trading)
Monitor reads bars directly from MT5 via `mt5.copy_rates_from_pos()`. Eliminates:
- HTTP 429 rate limit errors
- 15-60s API delay vs real-time
- Bar timestamp misalignment with MT5
- API key dependency

**When to use:** Always, if MT5 terminal is already running on same machine.
**When to fall back to Mode A:** MT5 not available, or testing strategy without connecting to broker.

**MT5 Initialization pattern for monitors (init ONCE, never shutdown):**
```python
sys.path.insert(0, "/c/Program Files/Python312/Lib/site-packages")
import MetaTrader5 as mt5

# Init ONCE at script start — NOT per-loop
if not mt5.initialize(path=MT5_PATH, timeout=15000):
    sys.exit("MT5 init failed")
mt5.symbol_select(SYMBOL, True)

# In loop — NEVER call mt5.shutdown():
while True:
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 60)
    closes = [r[4] for r in rates]
    # ... process ...
    time.sleep(check_interval)
```

**CRITICAL:** Do NOT call `mt5.shutdown()` inside the monitor loop. Calling shutdown in a monitor causes `mt5.copy_rates_from_pos()` to return `None` on the next iteration. Executors can shutdown/reconnect each cycle because they are short-lived, but monitors run 24/7.

**Discovered 1 June 2026:** V4.2 and V5.0 monitors were both switched Twelve Data → MT5 after missing 3 real M1 EMA20 breakouts in 10 minutes. Twelve Data bars lagged 15-60s behind actual MT5 closes. The switch eliminated all latency.

- **Monitor:** reads API or MT5, checks conditions, writes signal JSON.
- **Executor:** reads signal JSON, opens trade in MT5, manages trailing/partial close.
- Each strategy pair uses unique filenames (e.g. `v42`, `v50`) to avoid cross-contamination.

## Twelve Data Rate Limits

**Free tier:** 8 requests/minute. 1 request/cycle → 3/min is safe. 2 requests/cycle on 15s → 8/min → HTTP 429.

**Critical patterns (FOUND 1 June 2026):**

### Solution: Single API call per cycle + M15 cache

```python
# Main loop
m15_cache = None   # (closes, trend, e20, e50) persisted across cycles
m15_refresh_counter = 0
REFRESH_INTERVAL = 5   # refresh M15 every N cycles

while True:
    heartbeat()
    try:
        signal, m15_cache = check_signal(m15_cache)  # only 1 API call inside
        # ... print result ...

        m15_refresh_counter += 1
        if m15_refresh_counter >= REFRESH_INTERVAL:
            m15_cache = None  # force M15 refresh on next cycle
            m15_refresh_counter = 0

    except HTTPError as e:
        ts_err = datetime.utcnow().strftime("%H:%M:%S")
        print(f"[{ts_err}] API Error {e.code} — waiting 30s")
        time.sleep(30)
    except Exception as e:
        ts_err = datetime.utcnow().strftime("%H:%M:%S")
        print(f"[{ts_err}] Error: {e}")

    time.sleep(20)  # 3 req/min — safe
```

```python
def check_signal(m15_cache=None):
    # 1 API call (M5 data) — always
    raw5 = fetch_bars("5min", 200)

    # M15 — cached, refreshed only when m15_cache is None
    if m15_cache is not None:
        closes15, trend, e20, e50 = m15_cache
    else:
        try:
            raw15 = fetch_bars("15min", 80)  # extra call only when needed
            # ... parse trend ...
        except HTTPError:
            pass  # keep previous cache (but if None, no cache exists)

    if trend == "SIDEWAYS" or trend is None:
        return None, (closes15, trend, e20, e50) or m15_cache

    # ... check swing levels, emit signal ...
    return signal, (closes15, trend, e20, e50)
```

**Key points:**
- Only 1 API call (M5) per normal cycle → ~3 req/min
- M15 calls happen every 5 cycles + on first start ≈ ~0.6 req/min extra
- 429 in M15 call → keep old cache (graceful degradation)
- Catch `HTTPError` specifically in both `check_signal` and `main` loop
- `time.sleep(20)` min between cycles (can go to 15 if API count stays under 6/min)

### Additional protection: inter-call delay for new sessions

When starting fresh (no cache), the first cycle makes 2 rapid calls. Add a small delay:

```python
# In fetch_bars or in first-cycle path
time.sleep(8)  # between M5 and M15 calls on cold start
```

## MT5 Initialization — Windows Git-Bash Pitfalls

### ⚠️ CRITICAL: `terminal(background=true)` from Git-Bash CANNOT connect to MT5

The subprocess spawned by `terminal()` in MINGW64 has a different environment than a standalone Python process. `mt5.initialize()` will **hang indefinitely** — the process appears to start (PID exists) but never produces output or heartbeat.

**Foreground connectivity probe always works:**
```python
terminal(command="python -c \"import MetaTrader5 as mt5; print(mt5.initialize(path=r'C:\\Users\\Administrator\\Desktop\\FxPro\\terminal64.exe', timeout=30000))\"", timeout=30)
```

### What does NOT work:
| Method | Result |
|--------|--------|
| `terminal(background=true)` + `python script.py &` | ❌ Hangs on mt5.initialize() |
| PowerShell `Start-Process -FilePath python` inside terminal() | ❌ "No app associated" |
| `cmd //c start /B python ...` from terminal() | ❌ Same Git-Bash subprocess hang |
| Python subprocess.Popen inside a script from terminal(background) | ❌ Same environment |

### The ONLY reliable method: bat file (user clicks)

Two variants:

**Variant A — Simple:**
```bat
@echo off
chcp 65001 >nul
title GOLD Executor vX.Y
cd /d C:\Users\Administrator\Desktop\FxPro
echo === GOLD EXECUTOR vX.Y ===
echo.
del /f .gold_executor_vXY.lock 2>nul
"C:\Program Files\Python312\python.exe" -u _gold_executor_vXY.py
pause
```

**Variant B — With MT5 pre-check (recommended):**
```bat
@echo off
chcp 65001 >nul
title GOLD Executor vX.Y
cd /d C:\Users\Administrator\Desktop\FxPro
echo === GOLD EXECUTOR vX.Y ===
echo.
del /f .gold_executor_vXY.lock 2>nul
"C:\Program Files\Python312\python.exe" -c "
import MetaTrader5 as mt5
import sys, time, os
os.chdir(r'C:\Users\Administrator\Desktop\FxPro')
path = r'C:\Users\Administrator\Desktop\FxPro\terminal64.exe'
print('MT5 init...', end=' ')
ok = mt5.initialize(path=path, timeout=30000)
print(ok)
if ok:
    print('Connected! Account:', mt5.account_info().login)
    mt5.shutdown()
    time.sleep(1)
    exec(open('_gold_executor_vXY.py').read())
else:
    print('Error:', mt5.last_error())
    input('Press Enter to exit...')
"
pause
```

### Monitor launching (works via terminal background)

Monitors have NO MT5 dependency — they only call Twelve Data API:

```python
terminal(background=true, command="cd /c/Users/Administrator/Desktop/FxPro && python -u _gold_monitor_vXY.py &")
```

No notification needed — monitor is a long-lived daemon. Verify via heartbeat file.

## Liveness Verification (Windows-specific)

**Git-Bash `ps aux` does NOT show MT5-connected Python processes!** Always use:

1. **Heartbeat file** (monitor writes every N seconds):
   ```bash
   cat .monitor_vXY_heartbeat.json
   # {"last_check": "2026-06-01T10:57:12", "pid": 6092}
   ```

2. **Executor heartbeat file** — executors MUST write a heartbeat too, not just monitors:
   ```python
   # In the executor main loop:
   hb = {"last_check": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()}
   with open(HEARTBEAT_FILE, "w") as f:
       json.dump(hb, f)
   ```
   Without this, a dead executor can only be detected by stale lock-file PID that no longer appears in tasklist. The heartbeat tells you instantly if the executor is alive and looping.

3. **Log file** (executor writes on every action):
   ```bash
   tail -5 .gold_executor_vXY.log
   ```

4. **PowerShell process check** (when heartbeat is stale):
   ```powershell
   powershell -Command "Get-Process -Id <PID> -ErrorAction SilentlyContinue | Select-Object Id,ProcessName"
   ```

## Python scripts — required imports and error handling

**Always import (from the 1 June 2026 crash):**
```python
import json, time, os, sys       # sys needed for exit on missing key
from datetime import datetime
import urllib.request
from urllib.error import HTTPError   # catch 429 specifically
```

**Never use `ts` variable outside the try block where it's defined** — it causes a cascading NameError if the try block raises before `ts` is assigned.

```python
# BROKEN (crashes twice):
try:
    signal = check_signal()
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts}] ...")
except Exception as e:
    print(f"[{ts}] Error: {e}")  # NameError: ts not defined if exception before assignment!

# FIX:
try:
    signal = check_signal()
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts}] ...")
except HTTPError as e:
    ts_err = datetime.utcnow().strftime("%H:%M:%S")  # define inside exception handler
    print(f"[{ts_err}] API Error {e.code}")
except Exception as e:
    ts_err = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts_err}] Error: {e}")
```

## Universal Executor Pattern (Added 1 June 2026)

**Problem:** Two separate executors (V4.2 + V5.0) each calling `mt5.initialize()` independently. MT5 init is expensive and can hang from Git-Bash subprocess. Having 2 executors means 2 init calls, 2 lock files, 2 bat files for the user to manage. On 1 June 2026, both executors failed to pick up signals — V4.2 executor crashed with numpy error, V5.0 executor had magic mismatch. A single universal executor fixed all issues.

**Solution:** `_gold_universal_executor.py` — ONE process, ONE `mt5.initialize()`, reads BOTH signal files:

```python
SIGNAL_FILES = [
    ".gold_trade_signal_v42.json",  # V4.2
    ".gold_trade_signal_v50.json",  # V5.0
]

# MT5 init ONCE at startup
if not mt5.initialize(path=MT5_PATH, timeout=30000):
    sys.exit("MT5 init failed")

# Main loop — check both files every 2s
while True:
    for sig_file in SIGNAL_FILES:
        signal = read_signal(sig_file)
        if signal:
            ticket = open_trade(signal)
            remove_signal(sig_file)
    
    # Trailing + partial close management for all open positions
    manage_open_positions()
    
    time.sleep(2)
```

**Signal JSON format (both strategies write the same structure):**
```json
{
  "action": "BUY" / "SELL",
  "symbol": "GOLD",
  "price": 4509.15,
  "lot": 0.03,
  "entry_level": 4509.00,
  "sl": 4508.50,
  "trend_m15": "UP" / "DOWN",
  "reason": "...",
  "trailing_offset": 30,
  "trailing_step": 10,
  "timestamp": "2026-06-01T10:57:12",
  "source": "monitor_v42" / "monitor_v50",
  "magic": 123461
}
```

**CRITICAL: Signal validation must be minimal:**
```python
# RIGHT — check only fields every monitor version writes
if sig.get("source", "").startswith("monitor_") and sig.get("action") in ("BUY", "SELL"):
    ticket = open_trade(sig)

# WRONG — overspecified (found 1 June 2026 — executor filtered out ALL signals!)
if sig.get("data_source") == "MT5_ONLY" and ...  # monitor never writes this
```

On 1 June 2026, `_gold_executor_v42.py` checked `sig.get("data_source") == "MT5_ONLY"` — a field no MT5-based monitor ever writes → ALL signals silently skipped. **Always validate only what the monitor actually writes.**

**`mt5.order_send()` with `sl=0` / `tp=0` crashes (found 1 June 2026):**
```python
# CRASHES: returns None with error 'Invalid "sl" argument'
request = {"sl": 0}  # NEVER pass 0

# RIGHT: omit keys when not used
if "sl" in sig and sig["sl"] is not None:
    request["sl"] = sig["sl"]
if "tp" in sig and sig["tp"] is not None:
    request["tp"] = sig["tp"]
```

**Universal executor bat file:**
```bat
@echo off
chcp 65001 >nul
title GOLD Universal Executor
cd /d C:\Users\Administrator\Desktop\FxPro
echo === GOLD UNIVERSAL EXECUTOR ===
del /f .gold_executor_v42.lock .gold_executor_v50.lock 2>nul
C:\Program Files\Python312\python.exe -u _gold_universal_executor.py
pause
```

**Verification:** check heartbeat:
```bash
cat .gold_executor_universal_heartbeat.json
```

## Signal file format convention

Each strategy pair uses a unique signal file name. The universal executor reads ALL of them.

| Strategy | Signal file | Heartbeat file | Trail file | Magic |
|----------|------------|----------------|------------|-------|
| V4.2 | `.gold_trade_signal_v42.json` | `.monitor_v42_heartbeat.json` | `.v42_trail.json` | 123461 |
| V5.0 | `.gold_trade_signal_v50.json` | `.monitor_v50_heartbeat.json` | `.v50_trail.json` | 123460 |
| Universal exec | — | `.gold_executor_universal_heartbeat.json` | `.universal_trail.json` | both |

**Executor removes signal file after opening trade** — prevents duplicate opens.

## Signal JSON format (Twelve Data -> MT5)

Executor expects:
```json
{
  "action": "BUY",
  "symbol": "GOLD",
  "price": 4509.15,
  "lot": 0.03,
  "entry_level": 4509.00,
  "sl": 4508.50,
  "trend_m15": "UP",
  "reason": "Swing high BUY @ 4509.00",
  "trailing_offset": 25,
  "trailing_step": 10,
  "timestamp": "2026-06-01T10:57:12",
  "source": "monitor_v50"
}
```

## File naming conventions

All files in `C:\Users\Administrator\Desktop\FxPro\`:

| Pattern | Example | Purpose |
|---------|---------|---------|
| `_gold_monitor_vXY.py` | `_gold_monitor_v50.py` | Monitor script |
| `_gold_executor_vXY.py` | `_gold_executor_v50.py` | Executor script (opens + manages trade) |
| `run_executor_vXY.bat` | `run_executor_v50.bat` | User-clickable launcher |
| `.monitor_vXY_heartbeat.json` | `.monitor_v50_heartbeat.json` | Monitor liveness |
| `.gold_executor_vXY_heartbeat.json` | `.gold_executor_v50_heartbeat.json` | Executor liveness (MUST be present!) |
| `.gold_trade_signal_vXY.json` | `.gold_trade_signal_v50.json` | Signal file |
| `.gold_executor_vXY.lock` | `.gold_executor_v50.lock` | Executor lock (prevents duplicate) |
| `.vXY_trail.json` | `.v50_trail.json` | Trail state |
| `.gold_executor_vXY.log` | `.gold_executor_v50.log` | Executor log |

## Full deployment sequence (proved 1 June 2026)

```python
# 1. Kill stale processes
terminal(command="taskkill /F /IM python.exe 2>/dev/null")

# 2. Clean locks and stale signal files
terminal(command="rm -f .gold_executor_vXY.lock .vXY_trail.json .gold_trade_signal_vXY.json .monitor_vXY_heartbeat.json")

# 3. Create files (if not already present)
write_file(path="_gold_monitor_vXY.py", content="...")
write_file(path="_gold_executor_vXY.py", content="...")
write_file(path="run_executor_vXY.bat", content="...")

# 4. TEST monitor (no MT5 needed)
terminal(command="python -c \"exec(open('_gold_monitor_vXY.py').read())\"", timeout=30)

# 5. Launch monitor in background
terminal(background=true, command="cd /c/Users/Administrator/Desktop/FxPro && python -u _gold_monitor_vXY.py &")

# 6. Verify monitor is alive
terminal(command="sleep 15 && cat .monitor_vXY_heartbeat.json")

# 7. Ask user to click the bat file (executor needs MT5 — bat is the only reliable method)
# "Кликни run_executor_vXY.bat в папке FxPro — откроется окно cmd"
```

## Pitfalls found in production (1 June 2026)

1. **Too many API calls:** Monitor making 2 calls per cycle hits 429 on free tier. Fix: cache M15, single M5 call per cycle, 20s sleep.
2. **Cascading NameError:** `ts` inside exception handler defined earlier in try block — if exception before `ts` assignment, second exception crashes the process. Fix: always define `ts_err` inside each exception handler.
3. **Missing `sys` import:** `sys.exit()` used but `import sys` not present — crashes on missing API key. Fix: always import `sys`.
4. **`urllib.error.HTTPError` not imported:** Can't catch 429 specifically. Fix: `from urllib.error import HTTPError`.
5. **`terminal(background=true)` from Git-Bash + MT5:** Hangs on `mt5.initialize()`. Fix: user clicks bat file.
6. **Subprocess vs standalone environment:** Foreground `terminal(command="python probe.py", timeout=30)` works for testing; only long-running MT5 background fails.
7. **Executor signal filter mismatch:** When switching from Twelve Data → MT5 data source, monitor signals may lack fields the executor checks. On 1 June 2026, `_gold_executor_v42.py` had `sig.get("data_source") == "MT5_ONLY"` condition that no MT5-based monitor ever writes — executor silently skipped all signals. **Fix:** keep executor signal validation minimal — check only `source` and `action` fields:
   ```python
   # RIGHT (check what the monitor actually writes):
   if sig.get("source", "").startswith("monitor_") and sig.get("action") in ("BUY", "SELL"):
       ticket = open_trade(sig)
   ```
8. **Executor `mt5.order_send()` with explicit `sl=0` or `tp=0`:** Error `('Invalid "sl" argument')`. Never pass 0. Omit keys entirely when not used.
9. **Twelve Data bars ≠ MT5 bars in real-time** — Time series from Twelve Data can lag 15-60s behind MT5 terminal bars, causing missed breakouts. The monitor sees a breakout signal, but MT5 already shows price 10pts past the level. **Fix:** use MT5 as data source whenever possible.
