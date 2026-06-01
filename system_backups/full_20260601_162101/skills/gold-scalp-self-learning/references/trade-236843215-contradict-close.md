# Trade #236843215 — Contradict Close Case Study (30 May 2026)

## Timeline
- **19:06:26** — Monitor v3 emits `V1_SELL @ 4557.76` (score 4/6, RSI5=70.5, RSI15=57.7, **gator=bullish**)
- **19:06:29** — Executor opens SELL #236843215 @ 4556.94, SL=4560.65, TP=4549.5
- **19:06:39** — Daemon logs entry, price immediately drops to -144pts
- **19:06:39 → 19:08:20** — Price oscillates -168pts to +52pts (2 minutes of noise)
- **19:14:56** — **Executor v2 (reloaded with contradict-close) closes SELL @ 4557.05**

## Why this was contradictory
- **Alligator = bullish** (Lips=4557.16 > Teeth=4559.86 > Jaw=4562.53)
- **Direction = SELL** (against the trend)
- RSI5=70.5 triggered the "overbought → SELL" scoring, but Alligator said "bullish"

## What went wrong
1. **Monitor didn't block it** — the Alligator gate at that point only blocked BUY on bearish (soft rule: RSI15>55 + bearish). The equivalent SELL-on-bullish block wasn't implemented yet.
2. **Executor v1 didn't have contradict-close** — it was designed to only open trades
3. **Wait time:** 8 minutes 27 seconds from open to close — 169 executor cycles of 3s each. The contradiction was detectable from cycle 1.
4. **Pts log bug:** executor logged "+13.0pts" (using `abs()`) but actual was "-11.0pts" (4557.05 - 4556.94 = +0.11 for BUY, but this was SELL, so +0.11 in wrong direction = -0.11 = -11pts for SELL)

## What was learned/fixed
1. **Alligator gate hardened:** Both directions blocked. Bearish → no BUY. Bullish → no SELL. Not conditional on RSI15.
2. **Contradict Close added to executor:** Every 3s cycle checks Alligator direction vs position direction. Closes at market immediately.
3. **Pts calc fixed:** `round(abs(price - entry))` → proper direction-aware formula `(close - entry)/point for BUY else (entry - close)/point`
4. **User preference recorded:** "Close contradictory trades at zero or micro-profit, don't wait for reversal"

## Numeric breakdown
| Metric | Value | Notes |
|--------|-------|-------|
| Max adverse | -168pts (-$5.04) | Worst point during 8-min wait |
| SL risk | 373pts (-$3.73) | Would have been loss if SL triggered |
| Actual loss | -11pts (-$0.39) | Contradict close at entry-11pts |
| Saved vs SL | **$3.34** | $3.73 - $0.39 = 89.5% of SL loss avoided |
| Time to close | 8m27s | First executor had no contradict logic |
| After fix detection time | ~3s | One executor cycle |

## The user's exact words
> "Если такая спорная сделка возникла, то старайся ее закрыть около ноля или плюс микропрофит. Возьми это за правило себе."
