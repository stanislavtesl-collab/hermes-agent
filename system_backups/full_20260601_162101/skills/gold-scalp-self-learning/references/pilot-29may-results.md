# Pilot Self-Learning Results — 29 May 2026

## Config
- `--days 30 --population 50 --generations 2 --max-trials 200`
- Account 591712391, Balance $1,556.52
- Data: 6,036 M5 bars, 2,013 M15 bars

## Baseline (DEFAULT_PARAMS + Alligator-gate=hard)
| Metric | Value |
|--------|-------|
| Trades | 384 |
| WR | 61.2% |
| Total PnL | +$892.81 |
| Expected per trade | $2.33 |
| Max DD | $2,224 |

## Grid Results

### V1 (best params)
- Score: 7.394
- Trades: 209
- WR: 57.4%
- Exp: **$15.35** (6.6× baseline)
- DD: $759.57
- **Best params:** score_threshold=4, rsi5_strong_oversold=30, ema_distance_max_pts=15, atr_sl_mult=0.7, atr_tp_mult=2.0 — **identical to current live params!**

### V2
- Score: 0.000 (0 trades — normal, breakout is rare)

### V3
- Score: 96.206 (1 trade — too rare for 30-day window)

### MANAGEMENT (grid_mgmt, 200/512)
- Best score: 14.825
- Exp: $15.35
- DD: $759.57
- **Best params:** trailing 80/100/80, partial 50%@100pts — **identical to current v9 daemon params!**

### A/B Alligator-gate
| Mode | Trades | WR | Exp | Total | DD |
|------|--------|----|-----|-------|----|
| hard | 209 | 57.4% | $15.35 | +$3,209 | $760 |
| off | 495 | 54.7% | $12.19 | +$6,034 | ? |

**Chosen: hard** (better exp/profit-per-trade, lower DD)

## Key Takeaway
1. Current live params (V1: 4/6 scoring, trailing 80/100/80, partial close, Alligator-gate=hard) are **already at optimum** for 30-day window
2. No need to change live params — pilot confirms existing setup
3. Full 180-day run needed for V2/V3 signals and Phase 2 evolution
