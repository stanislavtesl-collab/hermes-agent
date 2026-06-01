# V1 Refactor — Week Backtest Results (25-29 May 2026)

## Context

User asked "перекрути стратегию чтобы работала на любом рынке". Ran full week (Mon-Fri) M5 backtest of V1.1 and 4 variants.

## Results Summary

| Version | Idea | Trades | PnL | WR | PF | 
|---|---|---|---|---|---|
| V1.1 (original) | score≥5, TP×2.5, SL×0.5, GATOR=HARD | 272 | -$244 | 25% | 0.41 |
| A: TP=1.5 SL=1.0 HARD | SL wider, TP realistic | 219 | -$315 | 42% | 0.36 |
| B: TP=1.0 SL=0.8 HARD | R:R=1:1 | 243 | -$350 | 37% | 0.31 |
| C: TP=1.5 SL=1.0 OFF | No Alligator blocks | 314 | -$374 | 46% | 0.45 |
| D: ADAPT TP | TP depends on ATR | 222 | -$313 | 43% | 0.37 |
| V2.0 ADX=18-40 | ADX filter + tighter entry | 191 | -$294 | 41% | 0.33 |

**ALL negative.** Week had chaotic 200pt swings in both directions.

## Key Lesson: EMA-Revert Fails on Strong Trend/Haotic Week

The core V1 strategy (buy dips to EMA20, sell rips to EMA20) **cannot** produce positive expectancy when:
- GOLD moves 100-200pts per day without clean pullbacks to EMA
- Price slices through EMA20 on every bar (no "revert" structure)
- SL (0.5-1.0×ATR) gets hit before a TP (1.5-2.5×ATR) has any chance

The signal-to-noise ratio collapses: 200+ trades/week with 25-46% WR means every "signal" is mostly noise.

## What Did NOT Work

1. **Tightening SL (0.8×ATR)** — even worse, more early exits
2. **Widening SL (1.2×ATR)** — still hit, just bigger losses
3. **Removing Alligator gate** — more trades, same low WR
4. **Adaptive TP** — marginally better, still negative
5. **ADX filter (18-40)** — fewer trades, still negative

## What V3.0 Attempts (unfinished)

Trend-following approach:
- H1 EMA50 defines direction (not Alligator M5)
- Enter ONLY with H1 trend on pullback to H1 EMA20
- SL at H1 swing low/high (not ATR-based)
- TP = H1 ATR×1.5 or next H1 level
- Target: 5-20 trades/week (not 200-300)

## Next Steps After This Session

If V3.0 fails:
1. **ML classifier** (XGBoost) on historical patterns
2. **Multi-timeframe confirmation** (H4 trend → H1 entry → M5 signal)
3. **Price action patterns** (pin bars, engulfing, inside bars only — no indicator scoring)
