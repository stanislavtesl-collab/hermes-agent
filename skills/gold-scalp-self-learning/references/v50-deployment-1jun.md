# V5.0 Level Breakout — Deployment (1 June 2026)

## Status

V5.0 Level Breakout (M5+M15 swing high/low) deployed and running parallel to V4.2:

| System | Monitor | Executor | TF | Signal File | Magic |
|--------|---------|----------|----|-------------|-------|
| V4.2 Multi-TF Scalper | ✅ PID 5556 | ✅ cmd window | M1+H1 | .gold_trade_signal.json | 123450 |
| V5.0 Level Breakout | ✅ PID 11484 | ✅ PID 8984 | M5+M15 | .gold_trade_signal_v50.json | 123460 |

## Key Files

- `_gold_monitor_v50.py` — monitor with M15 trend cache + rate-limit protection
- `_gold_executor_v50.py` — executor with trailing 25/10, no partial close
- `run_executor_v50.bat` — user double-click launcher
- `.gold_trade_signal_v50.json` — signal file (monitor writes → executor reads)
- `.gold_executor_v50_heartbeat.json` — executor heartbeat (added after first deploy failed — was missing)
- `.monitor_v50_heartbeat.json` — monitor heartbeat

## Rate-Limit Protection (Critical Lesson)

V5.0 crashed on first launch with **HTTP 429 Too Many Requests** — 2 API calls (M5 + M15) every 15s = 8 req/min, exceeding Twelve Data free tier.

**Fix implemented:**
- Only 1 API call per loop (M5 data). M15 trend cached and reused.
- M15 cache reset every 5 loops (~100s) for refresh.
- sleep(20) between loops = 3 req/min (safe).
- On HTTPError 429 — sleep 30s, retry.
- `from urllib.error import HTTPError` added.

## Python 3.12 `datetime` Gotcha

`datetime.utcnow()` is deprecated. Use `datetime.now(timezone.utc)` via `from datetime import datetime, timezone`.

**Wrong:** `datetime.now(datetime.UTC)` — raises `AttributeError` because `datetime` is the class, not the module.
**Right:** `datetime.now(timezone.utc)` — works.

## Test Trade (1 June 2026)

Manual test: OPEN SELL #237426299 @ $4,504.98 → CLOSE @ $4,505.13. Spread ~15pts. Balance impact: $1,555.74 → $1,555.51 (-$0.23 spread).

**Lesson:** mt5.order_send() returns `None` if `sl=0` is passed. Error: `('Invalid "sl" argument')`. Fix: omit `sl`/`tp` entirely when not using them, don't pass 0.

## V5.0 Entry Logic

- M15 trend by EMA20/EMA50: UP (price>EMA20>EMA50), DOWN (price<EMA20<EMA50), SIDEWAYS (else)
- If SIDEWAYS — no signal
- Find M5 swing high/low (15-bar lookback)
- BUY: trend=UP + price broke above nearest swing high
- SELL: trend=DOWN + price broke below nearest swing low
- SL: 50pts below/above swing level
- Trailing: offset=25, step=10 (tighter than V4.2's 30/10)
- NO partial close

## Backtest (14 days, 18-31 May 2026)
- 94 trades, WR 66%, PnL +$148.97, PF 15.01, Max DD $1.23
- $1,550 → $1,698.92 (+9.6%)
- Round-number entries ($X00) never triggered
