# V1 One-Day Backtest — 29 May 2026 (GOLD M5)

## Purpose
Validate V1.1 parameters on a single trading day to check if the 180-day optimal params (TP×2.5) work on a live day.

## Day Context
- **Date:** 29 May 2026
- **GOLD range:** ~4490 → ~4580 (+90pts, strong uptrend)
- **Bars:** 265 M5 candles (01:00-23:00 UTC)

## V1.1 Parameters Tested
score≥5 | RSI5=(30/40/60/70) | EMA≤20pts | SL=0.5×ATR | TP=2.5×ATR | Alligator=HARD | Trail 50/60/50 | Partial 30%@150

## Results
| Metric | Value |
|---|---|
| Trades | 63 (47 SELL, 16 BUY) |
| WR | 32% |
| **Total PnL** | **-$47.41** |
| PF | 0.50 |
| DD | $51.68 |
| Avg Win | $2.34 |
| Avg Loss | -$2.19 |

## Root Cause Analysis
1. **ZERO TP exits** — TP was 700-2800pts away, market never reached it. Every trade closed on SL or micro-profit.
2. **47 SELL vs 16 BUY** — Alligator=hard was bullish, so SELL was the allowed direction. That shorted INTO a +90pt uptrend. Alligator correctly identified trend direction, but V1 kept firing counter-trend signals.
3. **SL too tight for trend** — 0.5×ATR ≈150pts. In a +90pt trending day, price easily blew through 150pt SL in one move (04:00-05:00 saw +40pts in 1 hour).
4. **Scoring allowed too many entries** — 63 trades in one day = one every ~4 bars. The score≥5 threshold was too low for this day.

## Key Insight
**TP×2.5 does NOT work on M5 for a strong trending day.** The 180-day average masks this because on range-bound days the TP is reachable, but on trend days the SL always fires first.

## Recommended Fix
Add **regime-adaptive TP/SL** to monitor v3:
- If ADX(14) > 25 (strong trend) → TP = ATR × 1.0-1.5, SL = ATR × 0.8
- If ADX(14) < 20 (ranging) → TP = ATR × 2.5, SL = ATR × 0.5
- Or simpler: cap TP to min(ATR×1.5, 100pts) on M5

## Script
`C:\Users\Administrator\Desktop\FxPro\_backtest_v1_yesterday.py` — standalone one-day backtest script for V1. Run with:
```bash
"/c/Program Files/Python312/python.exe" "/c/Users/Administrator/Desktop/FxPro/_backtest_v1_yesterday.py"
```
Requires MT5 terminal running and `MetaTrader5` package installed.
