# MT5 Migration — 1 June 2026

## Why: Twelve Data monitor caused missed signals

Before: V4.2 monitor read M1 data via Twelve Data HTTP API (3-5s delay + rate limits).
Result: 3 breakouts happened in 10 minutes, monitor detected them but executor never received the signal because MT5
had already moved on (data mismatch between API and terminal).

After: Both monitors read directly from MT5. Zero delay, zero rate limits.

## Problems found during migration

### 1. `elif` bug in V5.0 find_swings

Original code:
```python
if nearest_high:
    # BUY: пробой swing high
    ...
elif nearest_low:
    # SELL: пробой swing low
    ...
```

Bug: If a swing high exists (even far away at +15pts), `nearest_high` is truthy → enters `if` block → doesn't find BUY signal
→ `elif nearest_low` is SKIPPED. SELL never fires when a swing high exists anywhere in the lookback window.

Fix: Separate `if` blocks with a guard:
```python
if nearest_high:
    if prev_c <= nearest_high and last_c > nearest_high:
        signal = {"action": "BUY", ...}

if not signal and nearest_low:
    if prev_c >= nearest_low and last_c < nearest_low:
        signal = {"action": "SELL", ...}
```

### 2. `sl=0` causes `order_send` to return None in MT5 Python API

```python
# WRONG — passes sl=0 as int
request = {"action": mt5.TRADE_ACTION_DEAL, "sl": 0}  # order_send returns None
print(mt5.last_error())  # (-2, 'Invalid "sl" argument')

# RIGHT — omit sl/tp entirely
request = {"action": mt5.TRADE_ACTION_DEAL}  # works
```

Same for `tp=0` → `TRADE_ACTION_SLTP` with `tp=0` also returns None.
Fix: For `TRADE_ACTION_SLTP`, omit `tp` key entirely, don't set to 0.

### 3. FxPro stop level = 30 points

`mt5.symbol_info("GOLD").trade_stops_level` = 30 (points).
`mt5.symbol_info("GOLD").trade_tick_size` = 0.01.
Minimum SL distance = 30 × 0.01 = 0.30 from current price.
But trying SL at 0.30 fails with `retcode=10016 (Invalid stops)`.
Minimum working distance found: **50pts** (0.50).

This means the 30pts trailing offset is **below the minimum stop distance** and may cause `order_send` failures.
Solutions:
- Use wider offset (50pts minimum, 60-80 recommended)
- Or accept that SL may lag by ~20pts from the ideal trail level

### 4. `nohup` required for persistent monitors

`terminal(background=true)` processes die when the background session completes or is polled.
Fix: Use `nohup python -u script.py > logfile 2>&1 &` for long-lived monitors.
Verification: Check heartbeat file freshness, not `ps aux` (Git-Bash doesn't show nohup'd processes from other sessions).

### 5. Process lifecycle

Monitors connected to MT5 are long-lived (stay open). No `mt5.shutdown()` per cycle — init once at startup.

### 6. Signal cleanup

After manual trade opening, delete signal file:
```python
import os
try: os.remove(SIGNAL_FILE)
except: pass
```
Otherwise executor (if it starts later) will pick up a stale signal and open a second trade.

### 7. Git-Bash process visibility

**CRITICAL:** Git-Bash (MINGW64) running inside Hermes' terminal tool does NOT show processes launched from outside (cmd windows, nohup'd processes from other sessions, Explorer-launched Python scripts).
Always verify with:
```bash
cat /path/.heartbeat.json           # timestamp freshness = alive
tasklist | grep python | wc -l      # total count, detect new processes
```
NEVER trust `ps aux` or `ps aux | grep python` for cross-session processes.
