# V4.1 Multi-TF Scalper — 30 May 2026

## Concept
H1 EMA50 trend filter → M1 entry on EMA20 cross + volume impulse → pure trailing stop (no TP).

## Backtest Results (week 25-29 May 2026, 6728 M1 bars)

### Winner: H1-trend, vol1.0, no-RSI, trail-25/step-10
| Metric | Value |
|--------|-------|
| Trades | 656 (131/day) |
| WR | 69% |
| PnL | **+$141** |
| PF | 1.27 |
| DD | **$42** (best of ALL strategies) |
| Exp | +$0.21 |
| AvgW / AvgL | $1.47 / -$2.63 |

### RSI filter comparison
| Config | Trades | WR | PnL | PF | DD |
|--------|--------|----|-----|----|----|
| no-RSI | 656 | 69% | **+$141** | 1.27 | $42 |
| RSI70 | 381 | 61% | -$130 | 0.67 | $136 |

RSI>70 filter kills entry on strong trends (blocks accelerating moves).

### M30 vs H1 trend filter
- H1 trend: 656 trades, profitable
- M30 trend: 0 trades (filter too slow for M1 scalping)

## Key Parameters
- `zone = 1.0` (fraction of H1 ATR for entry zone — not used, replaced by EMA20 cross)
- `vol_mult = 1.0` (any volume spike above avg)
- `trail_offset = 25pts`, `trail_step = 10pts`
- `use_rsi_filter = False` (critical — kills PnL)
- `max_hold = 120 bars` (2 hours timeout)
- SL: last 15-bar M1 swing capped at H1×0.3 ATR

## Weaknesses
1. Avg loss ($2.63) > avg win ($1.47) — 1.8× risk/reward ratio
2. 656 trades/week = high commission in real trading
3. Needs "no entry if price far from EMA20" filter to reduce losers

## Future improvements to test
1. Add "price within H1 ATR×0.5 of EMA20" entry filter (avoid entries at extremes)
2. Increase trail offset from 25 to 35pts (reduce small losers)
3. Add min profit filter: trail only if +10pts reached (skip tiny profits)
4. Test on 180-day full history
