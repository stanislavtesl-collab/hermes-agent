# 2025 Reanalysis — Atman-v04 on Current Gold Market

## Why 2025 Matters

Gold structurally broke out in 2025 ($2,060→$4,570+). Pre-2025 behavior (range-bound, mean-reverting) is completely different from 2025 behavior (trending, explosive). **All strategy parameters tuned on 2019-2024 data are suspect.**

## Baseline Results (2025 only, Jan-May 2026, 166 trades)

```
PF:      0.819  ← LOSING
Total:   -$417  on $1,550 start
Max DD:  $1,056 (68%)
WR:      29.5%
Sharpe:  -2.26 (negative = bad)
```

## Pattern-by-Pattern (2025 only)

| Pattern | Trades | WR | PF | PnL | Verdict |
|---------|--------|----|----|-----|---------|
| **A**   | 49     | 40.8% | **2.11** | **+$56** | **KEEP — promising** |
| **C**   | 116    | 25.9% | 0.84 | **-$399** | **KILL — losing money** |
| D_ASIAN | 1      | 0%    | 0.0  | -$75   | Dead — 1 trade in 5 months |

## Exit Distribution

| Outcome | Count | % |
|---------|-------|---|
| **TP**  | 50    | 30.1% | ← only 1 in 3 reaches full target
| **BE**  | 38    | 22.9% | ← 1 in 4 hits break-even at $0 (missed opportunity)
| **SL**  | 78    | 47.0% | ← nearly half lose money

**Key insight:** 555pts TP is too large for 2025 vol regime. If TP were smaller (250-350pts), many of the "SL" and "BE" trades would convert to small wins.

## Toxic Hours (UTC) — 2025 only sorted by PnL

| Hour | Trades | PnL | WR | PF | 
|------|--------|-----|----|----|
| **07:00** | 36 | **-$453** | 22% | 0.46 | ← OPEN LONDON = DEATH
| **11:00** | 10 | -$219 | 0% | 0.0  |
| **09:00** | 7  | -$180 | 14% | 0.03 |
| **10:00** | 17 | -$76  | 29% | 0.80 |
| **14:00** | 10 | -$152 | 30% | 0.23 |
| **16:00** | 7  | -$131 | 57% | 0.14 | ← 57% WR but huge avg loss
| **08:00** | 19 | +$11  | 32% | 1.06 |

**Conclusion: 07-12 UTC is entirely toxic (-$1,100 total). Kill it.**

## Good Hours (UTC) — 2025 only

| Hour | Trades | PnL | WR | PF | 
|------|--------|-----|----|----|
| **18:00** | 8  | **+$463** | 25% | 5.8 | ← BEST HOUR. Small N but monster avg
| **13:00** | 8  | +$107 | 38% | 5.6 |
| **17:00** | 12 | +$105 | 33% | 3.3 |
| **19:00** | 6  | +$103 | 67% | 3.3 |
| **15:00** | 10 | -$10  | 40% | 0.96 | ← marginal

## By Day of Week

| Day | Trades | PnL | WR | PF |
|-----|--------|-----|----|----|
| **Mon** | 31 | **-$696** | 36% | 0.37 | ← WORST. Lose and lose big
| **Tue** | 28 | +$8  | 25% | 1.02 |
| **Wed** | 34 | -$261 | 24% | 0.56 |
| **Thu** | 29 | **+$720** | 31% | 4.0 | ← BEST
| **Fri** | 44 | -$188 | 34% | 0.56 |

## Recommended Optimization Direction

1. **Pattern A only** — Pattern C is -$399 liability
2. **Hours: 13-20 UTC** — saves ~$1,100 from toxic morning hours
3. **TP: 250-300pts** (not 555) — capture more of the 47% SL trades
4. **BE: 30-35%** (not 50%) — lock in partial profits earlier
5. **Trailing: 20-30pts** after BE — run remaining position
6. **Skip Monday** if possible (or at minimum, tighten SL to 120pts)

## Optimizer Results (1,440 configs, 30 May 2026)

**Key finding:** Hours and DOW filters dominate the ranking. The top-15 configs ALL use Hours=13-19 and DOW=not_mon — suggesting these are the most impactful parameters.

**⚠️ WARNING: Only 23 trades per config.** The optimizer found a PF=27 config by fitting to 23 profitable trades. This is **not statistically significant**. The required minimum for any trading strategy is 100+ trades.

**Next iteration priority:** Increase trade count by expanding hours (10-20 or 8-20) even if it drops PF to 1.5-2.0. A PF=1.5 with 200 trades is more reliable than PF=27 with 23 trades.

**Best config found (preliminary, low confidence):**
```json
{
  "tp": 500,
  "sl": 150,
  "be": 0.30,
  "trail": 30,
  "hours": "13-19",
  "dow": "not_mon",
  "pf": 27.26,
  "wr": 0.91,
  "total": 89,
  "dd": 2,
  "n": 23
}
```

**Runner-up (same configs wider):**
- All top-15 configs share: Hours=13-19, DOW=not_mon, Trail=30 (or 0)
- TP variation across top-15: 400-500pts (larger TP better when adjusted for few trades)
- SL variation: 150-185pts (tighter slightly better)
- BE variation: 0.30-0.50 (no clear winner — BE is less impactful than hours/DOW)

