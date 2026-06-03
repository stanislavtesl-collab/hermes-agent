# V4.2 Multi-TF Scalper — Champion Config

## Date
2026-05-30, validated on 25-29 May 2026

## Parameters
| Param | Value | Why |
|---|---|---|
| Trend TF | H1 EMA50 | Stable, filters noise |
| Entry TF | M1 | High granularity for scalping |
| Entry condition | Price > M1 EMA20 + volume >= avg(10) | Confirms impulse |
| Trend direction | Price > H1 EMA50 + ATR×0.2 → BULL only, < → BEAR only | With-trend only |
| Trailing offset | 30pts | Optimal — 25 is too tight, 35 too loose |
| Trailing step | 10pts | Frequent updates |
| Partial close | 30% @ +15pts | Locks micro-profit, 2× PnL boost |
| SL formula | max(entry - H1 ATR×0.3, 15-bar low - 5pts) | Adapts to vola |
| RSI filter | OFF | Reduces quantity too much |
| ATR filter | OFF | Not needed |
| Max hold | 120 bars (2 hours) | Prevents overnight drift |
| Lot | 0.03 | Demo account |

## Performance
- Period: 25-29 May 2026 (5 trading days)
- Trades: 651 (130/day)
- Win Rate: 70.5%
- PnL: **+$357.07**
- Profit Factor: 1.70
- Max DD: $42.21
- Expectancy: $0.55/trade
- Avg Win: $1.90
- Avg Loss: -$2.68

## Code Structure
The reference script is `C:\Users\Administrator\Desktop\FxPro\_backtest_v42_final.py`.

Key functions:
1. Data fetch: MT5 M1/M5/H1 with 168h lookback
2. Indicator computation: M1 EMA20, M1 vol_ma10, M5 RSI5, H1 EMA50, H1 ATR14
3. TF mapping: H1 → M1 via forward-fill timestamp matching
4. Backtest loop: entry on EMA20 breakout + volume → trail + partial → SL/timeout exit
5. Report: per-config PnL/WR/PF/DD/Exp

## Testing New Ideas
When testing modifications to V4.2, always:
1. Keep the `run()` function signature extensible (kwargs for new params)
2. First test on the reference week (25-29 May)
3. If promising, expand to 180-day test
4. Compare to V4.2 champion — must beat +$357/5days or PF > 1.70
