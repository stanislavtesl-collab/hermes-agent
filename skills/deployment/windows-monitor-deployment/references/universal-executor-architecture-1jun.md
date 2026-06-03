# Universal Executor Architecture (1 June 2026)

## Problem
Two separate executors (V4.2 + V5.0) each calling `mt5.initialize()` independently.
MT5 init is expensive and hangs from Git-Bash subprocess. Having 2 executors means:
- 2 init calls (one may fail while other works)
- 2 lock files to manage
- 2 bat files for the user to click
- Both can miss signals while waiting for init

## Root Cause
On 1 June 2026, V4.2 executor crashed with numpy error (numpy array used in `if`),
V5.0 executor had magic number mismatch (monitor wrote `magic: 123460`, executor checked `magic: 123461`).
**Neither executor picked up any signal** — user had to open 2 trades manually.

## Solution
`_gold_universal_executor.py` — one process, one `mt5.initialize()`, reads BOTH signal files.

## Architecture
```
_gold_monitor_v42.py  →  .gold_trade_signal_v42.json  ─┐
                                                         ├→ _gold_universal_executor.py
_gold_monitor_v50.py  →  .gold_trade_signal_v50.json  ─┘
                                                         │
                                                         ├→ open_trade (V4.2 params if source=monitor_v42)
                                                         ├→ open_trade (V5.0 params if source=monitor_v50)
                                                         └→ manage_open_positions() (trailing + partial for ALL)
```

## Key Design Decisions

### 1. Minimal Signal Validation
```python
# RIGHT — only check fields all monitors always write
if sig.get("source", "").startswith("monitor_") and sig.get("action") in ("BUY", "SELL"):
    ticket = open_trade(sig)
```

### 2. One `open_trade()` Function
Same function handles both strategies — only differences per strategy are:
- Magic number (from signal JSON)
- Lot size (from signal JSON)
- Trailing params (from signal JSON)
- SL/TP calculations (same logic, different parameters)

### 3. `sl=0` / `tp=0` Bug
`mt5.order_send()` returns `None` with error `(-2, 'Invalid "sl" argument')` when `sl=0` or `tp=0` is passed.
**Fix:** Never pass 0. Omit keys entirely.
```python
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "GOLD",
    "volume": 0.03,
    "type": mt5.ORDER_TYPE_SELL,
    "price": tick.bid,
    "deviation": 10,
    "magic": 123460,
}
# Add SL only if specified
if "sl" in sig and sig["sl"] is not None:
    request["sl"] = sig["sl"]
# Add TP only if specified
if "tp" in sig and sig["tp"] is not None:
    request["tp"] = sig["tp"]
```

### 4. Signal File Removal
Executor deletes the signal file AFTER successfully opening a trade:
```python
if result and result.retcode == mt5.TRADE_RETCODE_DONE:
    try: os.remove(sig_file)
    except: pass
    return result.order
```

### 5. Universal Trailing
Trailing loop calculates trailing stop for ALL open positions, regardless of which strategy opened them:
```python
def manage_open_positions():
    positions = mt5.positions_get(symbol="GOLD")
    for pos in positions:
        if pos.comment == "monitor_v42":
            do_v42_trailing(pos)
        elif pos.comment == "monitor_v50":
            do_v50_trailing(pos)
```

## Deployment
User double-clicks `run_universal_executor.bat`:
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

## Heartbeat
```json
{"last_check": "2026-06-01T12:38:12", "pid": 8132}
```
Written every loop cycle (2s). Check with:
```bash
cat .gold_executor_universal_heartbeat.json
```

## Verification (1 June 2026)
- PID 8132, heartbeat updating every 2s ✓
- V50 SELL #237487560 @ $4,499.67 opened successfully ✓
- Partial close 0.01 lots @ $4,499.38 (+29pts) worked ✓
- Signal file removed after trade open ✓
