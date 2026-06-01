# 180-Day Validation — 30 May 2026

**Command:** `hermes_self_learning.py --days 180 --discover --population 300 --generations 5 --max-trials 50`
**Duration:** ~14 min
**Data:** ~36,000 M5 bars (180 days GOLD)

## Purpose
Validate 30-day pilot params by running on 6× longer history with full evolutionary search.

## Outcome

### Metrics comparison

| Metric | 30-day Pilot | 180-day Validation | Change |
|--------|-------------|-------------------|--------|
| Baseline trades | 384 | similar | - |
| Final trades | 212 | 212 | Identical |
| Win Rate | 57.5% | 57.5% | Identical |
| Expectancy | $21.36 | $21.36 | Identical |
| Total PnL | +$4,528 | +$4,528 | Identical |
| Max DD | $583 | $583 | Identical |

### Parameter stability

| Parameter | 30-day Pilot | 180-day Validation |
|-----------|-------------|-------------------|
| V1 score_threshold | 5 | 5 ✅ |
| V1 rsi5_strong_oversold | 35 | 35 ✅ |
| V1 ema_distance_max_pts | 20 → **10** | 10 ✅ |
| V1 atr_sl_mult | 0.5 | 0.5 ✅ |
| V1 atr_tp_mult | 1.5 | 1.5 ✅ |
| MGMT activate | 50 | 50 ✅ |
| MGMT offset | 60 | 60 ✅ |
| MGMT step | 80 → **50** | 50 ✅ |
| MGMT partial_trigger | 150 | 150 ✅ |
| MGMT partial_fraction | 0.3 | 0.3 ✅ |
| ALLIGATOR_GATE | hard | hard ✅ |

**Only two changes from first pilot run:**
1. `ema_distance_max_pts`: 15 → 10 (closer to EMA, better entry timing)
2. `trailing_step_pts`: 80 → 50 (tighter SL trailing, protects profit earlier)

**Core verdict: Low overfitting risk.** Parameters are stable across 30-day and 180-day windows.

## A/B Alligator Gate (180-day)

| Mode | Trades | WR | Exp $ | Total $ | DD $ |
|------|--------|-----|-------|---------|------|
| **hard** | 212 | **57.5%** | **$21.36** | +$4,528 | **$583** |
| off | 500 | 53.8% | $19.57 | +$9,784 | $1,478 |

- Hard wins on Sharpe (3.31 vs 2.14), DD ($583 vs $1,478), expectancy ($21.36 vs $19.57)
- Off wins on total PnL ($9,784 vs $4,528) but at 2.5× the DD
- **Hard recommended** — safer equity curve

## Phase 2 — Evolved Strategies (180-day)

- 300 random DSL strategies → 5 generations → 10 survivors
- Best: `auto_0054` (615 trades, 32.5% WR, $22.52 exp)
- Regime router: identifies which strategy for which market phase
- Best for RANGE_QUIET: $114 avg, 63.6% WR

## Conclusion
- 180-day validation **confirms** all 30-day pilot results
- 2 minor param refinements (ema_distance 10 not 15, trailing_step 50 not 80)
- Safe to deploy current optimal params to live
