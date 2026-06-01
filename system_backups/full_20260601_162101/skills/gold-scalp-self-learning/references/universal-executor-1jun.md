# Universal Executor — V4.2 + V5.0 in One Process

**Created:** 1 June 2026
**Problem:** Two separate executors (V4.2 + V5.0) each called `mt5.initialize()` independently. One or both would fail to take signals — V4.2 crashed with numpy error, V5.0 didn't open because magic mismatch.

## Architecture

```python
# _gold_universal_executor.py — ONE init, check BOTH signal files every 2s
mt5.initialize(path=MT5_PATH)  # done ONCE at startup

while True:
    # Check V4.2 signal
    signal_v42 = read_signal(".gold_trade_signal.json")
    if signal_v42 and not has_open_trade(magic=12345):
        open_trade(signal_v42)
        clear_signal(".gold_trade_signal.json")
    
    # Check V5.0 signal
    signal_v50 = read_signal(".gold_trade_signal_v50.json")
    if signal_v50 and not has_open_trade(magic=123460):
        open_trade(signal_v50)
        clear_signal(".gold_trade_signal_v50.json")
    
    # Trailing for any open trade
    manage_trailing()
    
    time.sleep(2)
```

## Key Design Decisions

1. **Single MT5 init** — `initialize()` is called once at startup. All subsequent operations reuse the same connection.
2. **Loop interval 2s** — fast enough to catch signals within MT5's tick resolution. Executor V1 used 3s, this is tighter.
3. **Magic number matching** — `has_open_trade(magic)` checks positions by magic, not ticket. V4.2 = 12345, V5.0 = 123460.
4. **Signal file clearing** — after opening, the signal file is emptied to prevent re-opening.
5. **Trailing is per-trade** — each source writes its own trailing config to the signal file. The executor applies trailing per that source's config.

## Signal File Formats

**V4.2** (`.gold_trade_signal.json`):
```json
{
  "action": "SELL",
  "price": 4504.43,
  "magic": 12345,
  "source": "monitor_v42",
  "trailing_offset": 30,
  "trailing_step": 10,
  "partial_close_pts": 15,
  "partial_close_fraction": 0.3
}
```

**V5.0** (`.gold_trade_signal_v50.json`):
```json
{
  "action": "SELL",
  "price": 4499.84,
  "entry_level": 4499.84,
  "lot": 0.03,
  "magic": 123460,
  "source": "V50",
  "trailing_offset": 25,
  "trailing_step": 10,
  "partial_close_pts": 0
}
```

## Deployment

1. Kill old executors: `taskkill /F /PID <pid1> <pid2>`
2. Clean locks: `rm -f .gold_executor_v42.lock .v42_trail.json`
3. Write `run_universal_executor.bat`:
```bat
@echo off
chcp 65001 >nul
title Universal GOLD Executor
cd /d C:\Users\Administrator\Desktop\FxPro
echo === UNIVERSAL GOLD EXECUTOR ===
echo.
"C:\Program Files\Python312\python.exe" -u _gold_universal_executor.py
pause
```
4. User double-clicks `.bat` — console window opens with executor running.
5. Verify via heartbeat: `cat .gold_executor_universal_heartbeat.json`

## Lessons Learned

1. **Magic mismatch was the root cause** of V5.0 executor not opening trades — monitor wrote magic=123460, executor checked for its own magic. The universal executor uses `has_open_trade(magic=X)` with the correct magic per source.
2. **Different signal files** — V4.2 writes to `.gold_trade_signal.json`, V5.0 to `.gold_trade_signal_v50.json`. Never cross-contaminate.
3. **Trailing config per source** — each signal carries its own trailing params (offset/step/partial). The executor applies them dynamically.
4. **Partial close confirmed working** — V5.0 partial 30% @ +29pts on trade #237487560 gave +$0.87 profit. Only the fraction that was open at activation benefits.
