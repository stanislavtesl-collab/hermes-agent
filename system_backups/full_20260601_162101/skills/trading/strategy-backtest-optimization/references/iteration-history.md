# Iteration History — All Versions Tested

All tests on GOLD, lot 0.03, week 25-29 May 2026 (unless noted otherwise).

| Version | Approach | Trades | WR | PnL | PF | DD | Key Change |
|---|---|---|---|---|---|---|---|
| V1.1 | EMA revert, score≥5, TP×2.5, SL×0.5 | 272 | 25% | -$244 | 0.41 | $51 | Baseline |
| V2.0 | Same + ADX filter 18-40 | 191 | 41% | -$294 | 0.33 | $302 | ADX filter |
| V3.0 | H1 trend + EMA20 zone (tight 0.5ATR) | 2 | 50% | -$16 | 0.62 | $42 | H1 trend filter |
| V3.1 Z=0.5 | H1 trend + narrow zone | 8 | 75% | **+$80** | 2.27 | $50 | Wider zone |
| V3.1 Z=1.0 | H1 trend + 1.0ATR zone 🥇 | 14 | 71% | **+$154** | 3.01 | $57 | **Winner V3** |
| V3.2 | V3.1 + SL-cap@1.5ATR (180d) | 324 | 53% | +$445 | 1.09 | $584 | SL cap |
| V4.0 M1 | Multi-TF scalper first attempt | 0 | — | — | — | — | Too strict entry |
| V4.1 H1-vol1.0-noRSI | M1 scalper, trail25 | 656 | 69% | **+$141** | 1.27 | $42 | Relaxed entry |
| V4.2 TRAIL30 | trail30 step10 | 651 | 68% | **+$175** | 1.34 | $50 | Bigger trail offset |
| V4.2 +PARTIAL | trail30 + partial 30%@15pts 🏆 | 651 | **70.5%** | **+$357** | **1.70** | **$42** | **Champion** |
| V4.2 VOL0.9 | trail25 + lower volume | 840 | 71% | +$155 | 0.24 | $48 | More trades |

## V3.2 180-day Validation
- Period: Dec 2025 - May 2026
- 324 trades, 52.8% WR, **+$445 PnL**, PF=1.09, DD=$584
- W/ SL-cap@1.5ATR (without cap: 139 trades, +$152, DD=$773)

## Key Lessons
1. **Partial close is critical** — 30%@+15pts gives 2× PnL boost (fixes micro-profit before trail hits)
2. **SL cap matters** — on 180d, SL-cap@1.5ATR raised PnL from +$152 to +$445 and cut DD from $773 to $584
3. **M1 scalping > M5 position** — more trades, smaller DD, higher WR
4. **H1 trend filter is non-negotiable** — every winning version used it
5. **RSI filter kills scalping** — blocks too many good entries on M1
6. **Distance-from-EMA filters** — reduce trades 5-11×, PnL drops proportionally
