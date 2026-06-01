# Trade #236834984 Postmortem: -$12.99 Loss (30 May 2026)

## The Signal

```
V1_BUY (сила 2) @ 4557.32 SL=4553.0 TP=4565.34
Score=5/6 ✅ | RSI5<30 +3 | откат 7/10 +1 | нет усталости 3/10 +1 | RSI15=59.8>=55 ❌
```

## What Happened

| Time | Price pts | P&L | Event |
|---|---|---|---|
| 18:49:12 | Entry 4557.32 | — | BUY opened |
| 18:49:12 | -23pts | -$0.69 | immediate loss |
| 18:49:35 | -127pts | -$3.81 | price tanked |
| 18:49:46 | -130pts | -$3.90 | bottom range |
| 18:50:20 | -207pts | -$6.21 | deeper |
| 18:51:05 | -224pts | -$6.72 | minor recovery |
| 18:52:47 | -354pts | -$10.62 | worst point |
| 18:53:21 | SL | -$12.99 | closed |

Total duration: 4min 9sec. Price never went positive once.

## Root Cause

**M15 trend confirmed bearish, M5 oversold was a trap.**

M5 candles before entry:
- 18:35 🟢 +3.06
- 18:40 🔴 -2.50
- 18:45 🔴 -4.74 ← heavy red
- 18:50 🟢 +0.87 ← weak bounce
- 18:55 🟢 +1.64 ← weaker
- 19:00 🔴 -2.62 ← back to red

Key metrics at entry:
- RSI5 = 15 (extreme oversold on M5 — trap)
- RSI15 = 59.8 (>55, bearish on M15 — should have blocked)
- Gator = bearish (Alligator jaws bearish)
- 7/10 last M5 candles = red (momentum down)
- Fibo 78.6% = 4557.60 — price was exactly at this level, no rejection bounce

The score was 5/6 but the one failed condition (RSI15 >= 55) was the most important one.

## Three Ways This Could Have Been Avoided

1. **RSI15 veto** — if RSI15 > 55 and Gator bearish → score=0 (IMPLEMENTED immediately after)
2. **Wait for stabilization** — 4+ mixed-color candles before entering
3. **SL by ATR** — entry - ATR_M5 * 2 = 4557.32 - 80pts = 4556.52 → loss: -$2.40 instead of -$12.99

**Winner: #1.** Veto rule was implemented in _gold_monitor_v3.py immediately after this trade.

## The Counterfactual: What If We Entered SELL?

| Time | SELL pts | SELL $ |
|---|---|---|
| 18:49:12 | 0 | $0 |
| 18:49:35 | +127 | +$3.81 |
| 18:50:20 | +207 | +$6.21 |
| 18:52:47 | +354 | +$10.62 |
| Best exit | **+354pts** | **+$10.62** |

## Lesson for Future

The scoring system's weakest link: RSI5 oversold on a falling market.

When RSI5 < 30:
- If RSI15 > 45 (weak bear trend) → proceed with caution (buy)
- If RSI15 > 55 (confirmed bear trend) → **BLOCK BUY** (score=0)
- If Gator = bearish + RSI15 > 55 → **DEFINITE BLOCK**

The same applies in reverse for SELL and RSI15 < 45.

The +3 points from RSI5<30 are too heavy for a single condition. Never outweighed the M15 context.
