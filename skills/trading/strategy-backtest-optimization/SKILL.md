---
name: strategy-backtest-optimization
description: >-
  Iterative backtesting optimization workflow for GOLD trading strategies.
  Grid-test multiple config variants on a fixed week of data (25-29 May 2026),
  rank by PnL, pick the winner, then refine with partial close / trailing / filters.
  Proven approach: V1 (revert EMA) → V3 (H1-trend) → V4 (M1 scalper + trail + partial).
  Also covers session_search recovery when background backtests were not actually run,
  naming conflict pitfalls in Python backtest scripts (ts vs ts_, time vs numpy datetime),
  and the slow-iteration cycle: hypothesize → grid → rank → refine → re-rank.
  Covers M15 position swing, averaging, adjustable trailing params, SL at trade open.
tags: [backtest, gold, optimization, grid-search, strategy, m15, position, averaging]
related_skills:
  - gold-scalp-self-learning
  - trading:backtest-atman
  - walk-forward-validation
---
# Strategy Backtest & Optimization Workflow

## Core Workflow

When asked to "improve the strategy" or "make it profitable":

1. **Hypothesize** — propose 3-5 config variants
2. **Grid test** — run ALL variants on the SAME fixed week (25-29 May 2026)
3. **Rank** — sort by PnL, report WR/PF/DD/Exp
4. **Pick winner** — best PnL + PF + DD
5. **Refine** — add 2-3 improvements
6. **Re-rank** — compare refined against winner
7. **Repeat** — until user says "good enough"

## What Killed V1 (EMA Reverts)
- TP too far — 0% reached
- SL too narrow — stopped out before reversing
- Trading against H1 trend
- Too many trades (272/week, 75% losers)

## What Fixed It (V3.2 → V4.2)

| Problem | Fix |
|---|---|
| Trading against trend | H1 EMA50 filter |
| SL too narrow | H1 swing capped at ATR×1.5 |
| TP never reached | Trailing stop instead of fixed TP |
| Too many losers | Volume spike filter on M1 EMA20 |
| Bad R:R | Partial close 30% @ +15pts |
| SL not set at open | SL in order_send(): `"sl": sl_price` |

## V4.2 Champion Config
```
Trend: H1 EMA50 ± ATR×0.2. Entry: M1 > EMA20 + volume >= avg(10)
Trail: offset=30pts, step=10pts. Partial: 30% @ +15pts
SL: max(entry - H1 ATR×0.3, 15-bar low - 5pts)
RSI filter: OFF. ATR filter: OFF
```
651 trades, 70.5% WR, +$357 PnL, PF=1.70, DD=$42

## V5.0 — M5 Swing Breakout
Pure level breakout. No EMA-revert. SL 50pts. Trailing 30/10.

## M15 Position Swing (June 2026)
H4→H1→M15 для удержания 200-250pts. Magic=123463. NO partial close. TP=250pts.
references/m15-position-swing.md

## Averaging (June 2026)
- 1 усреднение макс. Доб. лот того же объёма на сильном уровне
- H1 тренд подтверждает. Средняя пересчитывается. SL на обе.
- Ждёт лучшую точку в live (каждые 2с)
- references/averaging-rules.md

## Трейлинг — параметры

| Параметр | Ослабленный | Агрессивный | По умолчанию |
|---|---|---|---|
| Активация | 60pts | 15pts | 30pts |
| Offset | 60pts | 20pts | 30pts |
| Step | 20pts | 5pts | 10pts |

## SL при открытии
В order_send(): `"sl": sl_price`. SL_DISTANCE=8.00 (800pts).

## numpy-safety (CRITICAL)

MT5 `positions_get()` fields (`sl`, `price_current`, `volume`, `tp`) can return **numpy arrays** instead of native floats when the terminal is busy or the position struct is read from a cached state. `float(array_value)` raises:
```
ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
```

This crash loops an executor indefinitely — every 2-second cycle throws, signals pile up uncleared, and the whole trading system goes blind.

**Wrong** (crashes on array):
```python
float(pos.sl) if pos.sl is not None else None
```

**Right** — use a `safe_val()` wrapper everywhere:
```python
def safe_val(val):
    \"\"\"Безопасно приводит MT5 значение к float или None.\"\"\"
    if val is None:
        return None
    try:
        v = float(val)
        return None if v > 1e10 or v < -1e10 else v
    except (TypeError, ValueError):
        return None
```

Apply `safe_val()` to **every** access of: `pos.sl`, `pos.price_current`, `pos.volume`, `pos.tp`. Not just the trailing-stop code — **also** in `try_average()`, `close_position()`, and anywhere else that reads a position field.

**Symptoms a running executor has this bug:**
- Log file fills with "The truth value of an array..." errors every 2-3 seconds
- Signal files (`.gold_trade_signal.json`, `.gold_trade_signal_v50.json`) are silently consumed/cleared without opening trades
- Heartbeat file keeps updating but no positions are opened
- `ps aux | grep python` shows the process alive but doing nothing productive

**False-negative trap (1 June 2026):** After patching safe_val() and restarting, `grep Error | tail -3` showed old errors from the killed process's log — creating the illusion the fix didn't work. **Always check timestamps:** `grep Error .universal_executor.log | grep -E "$(date +%H:%M)"` — only errors since restart matter. Or clear the log on restart.

## Разделение magic
- Скальпинг (V4.2/V5.0): magic=123462, partial 30%@+15pts
- Позиционка M15: magic=123463, NO partial, TP=250pts

## Python Backtest Pitfalls
- ts conflicts with numpy datetime64 → use ts_step
- rsi() output N-4 shorter → clamp: `min(j, len(arr)-1)`
- .ewm().values → .ewm().mean().values
- searchsorted → always `min(gi, len(arr)-1)`
- `elif` swing bug: use `if not signal and ...` not `elif`

## Data Source: MT5 > Twelve Data
MT5 real-time, zero-latency. Twelve Data: 8 req/min, HTTP 429.

## Filter Relaxation
"ослабь фильтры" → remove trend-direction filters, trade both sides.

## Reference Files
- references/champion-v42-config.md
- references/iteration-history.md
- references/naming-conflicts.md
- references/deployment-guide.md
- references/m15-position-swing.md
- references/averaging-rules.md
