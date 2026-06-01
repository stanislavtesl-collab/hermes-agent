# Week Backtest — V1.1 through V3.1 (25-29 May 2026)

## Test Data
- **Period:** Mon 25 May 00:00 UTC → Fri 29 May 23:55 UTC
- **Symb ol:** GOLD (XAUUSD)
- **Timeframe:** M5
- **Bars:** 1,346
- **Terminal:** FxPro Demo 591712391
- **Lot:** 0.03

## Results Summary

| Version | Approach | Trades | PnL | WR | PF | DD | TP hit |
|---------|-----------|--------|-----|----|----|----|---------|
| V1.1 | score≥5, TP×2.5, SL×0.5, GATOR=HARD | 272 | -$244 | 25% | 0.41 | $246 | 0 |
| A | TP=1.5, SL=1.0, GATOR=HARD | 219 | -$315 | 42% | 0.36 | $326 | 10 |
| B | TP=1.0, SL=0.8, GATOR=HARD | 243 | -$350 | 37% | 0.31 | $354 | 23 |
| C | TP=1.5, SL=1.0, GATOR=OFF | 314 | -$374 | 46% | 0.45 | $377 | 20 |
| D | ADAPT TP, SL=1.0, GATOR=HARD | 222 | -$313 | 43% | 0.37 | $324 | 18 |
| V2.0 | ADX=18-40, RSI tighter, HARD | 191 | -$294 | 41% | 0.33 | $302 | 7 |
| V2.0 | ADX=18-40, SL=0.8 | 200 | -$273 | 36% | 0.34 | $278 | 7 |
| V2.0 | ADX=15-35, score≥6, SL=1.2, TP=2.0 | 118 | -$236 | 37% | 0.26 | $241 | 1 |
| V3.0 | H1-trend, entry near H1 EMA20, HARD | 2 | -$16 | 50% | 0.62 | $42 | 1 |
| V3.0 | H1-trend, LEVEL TP | 2 | -$8 | 50% | 0.80 | $42 | 1 |

## Per-Day Breakdown (V1.1)

| Day | Trades | PnL | WR |
|-----|--------|-----|----|
| Mon | 46 | -$29.73 | 22% |
| Tue | 63 | -$58.97 | 24% |
| Wed | 51 | -$49.44 | 25% |
| Thu | 49 | -$59.32 | 22% |
| Fri | 63 | -$47.41 | 32% |

## Per-Direction (V1.1)
- BUY: 134 trades, -$135.18, WR 22%
- SELL: 138 trades, -$109.69, WR 28%

## Key Findings

1. **ALL variants negative** on this week. The strategy doesn't fail for one reason — it fails for many simultaneously.
2. **Zero TP hits on V1.1** — TP×2.5 is too far for M5 on any day with +20pts movement.
3. **V3.0 H1-trend-following** gave first TP hits (+$25.76 and +$33.62) but only 2 trades/week — too few.
4. **Market was highly chaotic** this week: GOLD 4490→4590→4370→4590 = 200pt+ swings.
5. **Average loss ≈ -$2 per trade** — consistent across all variants. The edge is missing, not the parameters.
