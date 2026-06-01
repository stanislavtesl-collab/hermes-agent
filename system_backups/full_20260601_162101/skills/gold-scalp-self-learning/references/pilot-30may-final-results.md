# Self-Learning Pilot Results — 30 May 2026

## Execution
- **Command:** `hermes_self_learning.py --days 30 --population 50 --generations 2 --max-trials 50`
- **Duration:** ~6.5 min (incl. 4 failed attempts, final run = 4.5 min)
- **Data:** 6036 M5 bars (30 days GOLD)
- **Account:** 591712391 (FxPro Demo, $1,556.52)

## Outcome Summary

| Metric | Baseline | Optimized | Delta |
|--------|----------|-----------|-------|
| Trades | 384 | 212 | -45% |
| Win Rate | 61.2% | 57.5% | -3.7pp |
| Expectancy | $2.33 | **$21.36** | **9.2x** |
| Total PnL | +$893 | +$4,528 | +407% |
| Max DD | $2,224 | **$583** | -74% |

## Optimal Parameters

### V1 (EMA Revert — primary)
```json
{
  "score_threshold": 5,
  "rsi5_strong_oversold": 35,
  "rsi5_mild_oversold": 45,
  "rsi5_strong_overbought": 65,
  "rsi5_mild_overbought": 55,
  "ema_distance_max_pts": 10,
  "pullback_candles_min": 4,
  "fatigue_limit": 6,
  "fatigue_window": 10,
  "rsi15_buy_cap": 55,
  "rsi15_sell_floor": 45,
  "atr_sl_mult": 0.5,
  "atr_tp_mult": 1.5
}
```
- Score: **7.394** (grid rank #1)
- 210 trades, 58.1% WR, $8.23 exp, DD $837

### MANAGEMENT
```json
{
  "trailing_activate_pts": 50,
  "trailing_offset_pts": 60,
  "trailing_step_pts": 80,
  "partial_close_trigger_pts": 150,
  "partial_close_fraction": 0.3
}
```
- Score: **26.185** (vs 14.8 for current 80/100/80)
- 212 trades, 57.5% WR, $21.36 exp, **DD $583** 

### V2 (Breakout)
- 0 trades on 30-day window (normal — rare signal)
- Keep as-is, no optimization needed

### V3 (VWAP M1 Micro)
- 1 trade, exp $96.21 (statistically insignificant)
- Keep for edge cases

### Alligator-gate
- **Hard** chosen over Off
- Hard: 212 trades, 57.5% WR, $21.36 exp, +$4,528 total
- Off: 500 trades, 53.8% WR, $19.57 exp, +$9,784 total
- Hard reduces trades by 58% but increases expectancy by 9%

## Phase 2 — Evolved Strategies

- 50 random DSL strategies → 2 generations → **10 survivors**
- Best: `auto_0054` (615 trades, 32.5% WR, $22.52 exp)
- Regime router built: TREND_UP/TREND_DOWN/RANGE_QUIET/RANGE_VOLATILE/BREAKOUT
- RANGE_QUIET best: `auto_0094` avg $114.33/trade, 63.6% WR (11 trades)
- TREND_DOWN best: `auto_0055` avg $26.79/trade, 33.2% WR (397 trades)

## Key Fixes Applied
1. `grid_mgmt()` expanded 3×3×3×3×3 → 4×4×4×4×2 (fixed crash)
2. `evolve(df, seeds, generations=...)` → `gens=...` (fixed TypeError)
3. Log accumulation: clean `.hermes_*` before each re-run
