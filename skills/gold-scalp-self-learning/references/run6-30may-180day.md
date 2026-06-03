# Run #6 — Self-Learning 180-Day Validation (30 May 2026)

**Date:** 2026-05-30 09:38 UTC  
**Period:** 180 days (2025-12-01 to 2026-05-29)  
**Symbol:** GOLD M5 | **Lot:** 0.03  
**Data:** 34,719 bars M5 + 11,575 bars M15  

## Baseline

| Metric | Value |
|--------|-------|
| Trades | 2,254 |
| WR | 59.9% |
| Expectancy | $1.12 |
| PF | 1.02 |
| Total PnL | +$2,529 |
| Max DD | $5,150 |
| Sharpe | 0.11 |

## Final (Grid-optimized)

| Metric | Value |
|--------|-------|
| Trades | 1,385 (Alligator=off) / 557 (hard) |
| WR | 53.6% (off) / 57.1% (hard) |
| Expectancy | $39.70 (off) / $41.91 (hard) |
| PF | 1.79 (off) / 1.93 (hard) |
| Total PnL | +$54,986 (off) / +$23,341 (hard) |
| Max DD | $2,435 (off) / $1,764 (hard) |
| Sharpe | 3.06 (off) |

Improvement: +$52,456 (baseline was $2,529) = **+2,075%**

## Top V1 Config (Score=14.25)

```json
{
  "score_threshold": 5,
  "rsi5_strong_oversold": 30,
  "rsi5_mild_oversold": 40,
  "rsi5_strong_overbought": 70,
  "rsi5_mild_overbought": 60,
  "ema_distance_max_pts": 20,
  "pullback_candles_min": 4,
  "fatigue_limit": 6,
  "fatigue_window": 10,
  "rsi15_buy_cap": 55,
  "rsi15_sell_floor": 45,
  "atr_sl_mult": 0.5,
  "atr_tp_mult": 2.5
}
```
- 556 trades, 57.0% WR, $19.73 exp, PF=1.43, DD=$1,761

## MANAGEMENT (Score=30.30)

```json
{
  "trailing_activate_pts": 50,
  "trailing_offset_pts": 60,
  "trailing_step_pts": 50,
  "partial_close_trigger_pts": 150,
  "partial_close_fraction": 0.3
}
```
- 557 trades, 57.1% WR, $41.91 exp, PF=1.93, DD=$1,764

## A/B Alligator-gate

| mode | n | WR | exp$ | total$ | DD$ |
|------|---|----|------|--------|-----|
| hard | 557 | 57.1% | 41.905 | 23,341 | 1,764 |
| off | 1,385 | 53.6% | 39.701 | 54,986 | 2,435 |

**Chosen in Run #4/#5 (29 May):** hard (better quality)  
**Chosen in Run #6 (30 May):** off (higher total PnL)  

Reconciliation: hard wins on quality in BOTH runs. The switch is due to the scoring formula weighting total PnL, and off makes 2.4× more trades. Run #4/#5 had a different baseline (2254 trades baseline, fewer days effect).

## V2

0 trades in all top-5 configs. Dead strategy on GOLD M5.

## V3

1-2 trades in top-5. Statistically insignificant on 180 days.

## Phase 2 — Evolved Strategies

5 generations, pop=300→195, 30 survivors in library.

### Top-3:

| # | id | n | WR | exp$ | PF | DD$ |
|---|----|---|----|------|----|-----|
| 1 | auto_0630 | 24 | 75.0% | 226.85 | 4.41 | 365 |
| 2 | auto_0894 | 26 | 57.7% | 377.73 | — | — |
| 3 | auto_0927 | 25 | 68.0% | 176.44 | 3.36 | 311 |

### Regime Router (top per regime):

| Regime | Strategy | Avg $ | n | WR |
|--------|----------|-------|---|----|
| TREND_UP | auto_0658 | $123.80 | 15 | 53.3% |
| TREND_DOWN | auto_0894 | $377.73 | 26 | 57.7% |
| RANGE_VOLATILE | auto_0894 | $506.81 | 12 | 66.7% |
| RANGE_QUIET | auto_0800 | $70.90 | 5 | 60.0% |

## Log Cross-contamination Bug (30 May 2026)

Run #6 appended to the **same** `.hermes_learning.log` file as Run #4/5 (29 May). When reading the log to check progress, old entries from 20:37-00:01 appeared before new entries from 07:32+. The new run correctly overwrote output JSON files, so the final report is clean. But **mid-run log inspection is confusing** — the file carries 2 full run transcripts.

**Lesson:** always `rm -f .hermes_learning.log` before starting a new full run if you plan to inspect progress mid-run.
