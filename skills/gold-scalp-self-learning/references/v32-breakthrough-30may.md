# V3.2 H1 Trend-Following — Breakthrough (30 May 2026)

## Context
After testing 7 variants on week 25-29 May 2026 (ALL negative with revert-to-EMA approach), 
a fundamentally different strategy was developed: H1 trend-following.

## The failure that led to the breakthrough
V1.1 (score≥5, RSI5=30/40/60/70, TP×2.5, SL×0.5, Alligator=HARD):
- 272 trades, WR 25%, PnL -$244 on one week
- Week had: Mon -$30, Tue -$59, Wed -$49, Thu -$59, Fri -$47
- Every day negative, every config negative for 7 iterations

## The fundamental shift
Instead of "find reversals to EMA20" → "ride H1 trend with pullback entries"

## Key insight chain
1. H1 EMA50 defines direction → trade WITH it, never against
2. H1 EMA20 zone (~1.0×H1 ATR) defines entry area → wait for pullback to this zone
3. H1 swing low/high defines SL → but swing can be 200-500pts away (too wide!)
4. **SL cap at H1 ATR×1.5** → turned -$151 uncapped into +$445 capped (+292%)
5. TP = H1 ATR×1.5 → reachable (155pts avg) vs V1 TP×2.5 (250-700pts, 0% hit rate on trend days)

## Tested configs (180-day, Dec 2025 - May 2026)

| Config | Trades | WR | PnL | PF | DD | Exp |
|--------|--------|----|-----|----|----|-----|
| BASE (uncapped, no partial) | 139 | 64.7% | +$151 | 1.07 | $773 | $1.09 |
| +PARTIAL 30%@0.5TP | 139 | 64.7% | -$463 | 0.80 | $1,001 | -$3.33 |
| **+SL-CAP@1.5ATR** | **324** | **52.8%** | **+$445** | **1.09** | **$584** | **$1.37** |
| +PARTIAL+CAP | 324 | 52.8% | -$845 | 0.82 | $1,078 | -$2.61 |
| +TRAIL 30/40 (no cap) | 1,511 | 90.5% | +$650 | 1.16 | $490 | $0.43 |
| +TRAIL+RSI | 1,028 | 87.9% | -$1,298 | 0.67 | $1,445 | -$1.26 |

## Winner: SL-CAP@1.5ATR
- 3× more trades than BASE (capped SL lets more entries through)
- +292% PnL vs BASE
- -24% DD vs BASE
- PF same (1.09) — quality preserved

## Never do:
- **Partial close** on trend-following → -$463 vs +$445 (without). Partial exits before trend develops.
- **Uncapped SL** on trend-following → +$151 vs +$445. H1 swings can be 200-500pts.

## Comparison with V1 on same week (25-29 May)
| | V1.1 | V3.2 BASE | V3.2 SL-CAP |
|---|---|---|---|
| Trades | 272 | **8-14** | **14-324** (180d) |
| WR | 25% | **71-75%** | **52.8%** |
| Week PnL | -$245 | **+$80-154** | **—** |
| 180d PnL | +$10,970 (V1 opt) | +$151 | **+$445** |
