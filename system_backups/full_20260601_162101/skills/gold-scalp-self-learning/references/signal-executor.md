# GOLD Signal Executor v1

Bridging monitor signals to actual MT5 trade execution.

## Why needed

- `_gold_monitor_v3.py` only detects and writes `.gold_trade_signal.json`
- `gold_manager_daemon.py` only manages existing positions (trail + partial close)
- **Nobody opened trades** until executor was created (30 May 2026)

## Architecture

```
Monitor v3 → writes signal.json → Executor reads it → opens deal → deletes signal
                                                                      ↓
                                                             Daemon v9 takes over
```

## Signal file format (`.gold_trade_signal.json`)

```json
{
  "action": "V1_BUY",
  "strength": 2,
  "price": 4558.8,
  "sl": 4555.75,
  "tp": 4567.5,
  "rsi5": 15.0,
  "rsi15": 61.0,
  "fibo_nearest": ["78.6", 4557.59],
  "gator": "bullish",
  "fractal_up": 4573.52,
  "fractal_down": 4557.78,
  "time": "18:48:05"
}
```

## Execution logic

1. Every 3s: check if position exists
2. If position exists → delete signal file (avoid stale signal after close)
3. If no position AND signal file exists → read it, open market order
4. Uses separate `MAGIC = 123457` (daemon uses 123456)
5. Fixed lot size: 0.03
6. Price from `mt5.symbol_info_tick(symbol).ask` (BUY) / `.bid` (SELL)
7. Devotion 20, FILLING_IOC

## Lock file

`_gold_executor.py` has its own lock file `.gold_executor.lock` to prevent duplicates.
Use single-instance pattern: `os.O_CREAT | os.O_EXCL` open, write PID, close.

## Restart sequence

Executor MUST start before monitor — otherwise a signal written between executor death and restart will be missed until the next monitor cycle (up to 48 min).

If executor dies while monitor runs: the signal sits in the file unprocessed. When executor restarts, it will pick it up on the next 3s check (assuming no position exists).

## Known issues

- No retry on partial fill (FILLING_IOC rejects instantly if not fillable)
- No volume adjustment (always 0.03)
- No weekend/session check — runs forever
- If MT5 reinit fails → logs error and retries after 10s sleep
