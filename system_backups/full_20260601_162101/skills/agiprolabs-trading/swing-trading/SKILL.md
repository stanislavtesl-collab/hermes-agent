---
name: swing-trading
description: >
  Swing trading and growth stock analysis for US equities.
  Use for CANSLIM screening, VCP pattern detection, breakout trade planning,
  position sizing, theme detection, earnings analysis, and technical chart interpretation.
  Always check market regime first before running swing analysis.
---

# Swing Trading Playbook

## Pre-Trade Checklist

1. ✅ Market regime allows new positions (exposure posture = allow)
2. ✅ Stock meets minimum criteria (CANSLIM or VCP)
3. ✅ Position size calculated (1-2% risk per trade)
4. ✅ Entry, stop, and target defined
5. ✅ Order type selected (stop-limit bracket pre-placement, limit post-confirmation)

## Methodologies

### CANSLIM Screening
- **C**urrent quarterly EPS: ≥25% growth
- **A**nnual earnings growth: ≥25% over 3-5 years
- **N**ew products/management/highs
- **S**upply and demand: low float, high demand
- **L**eader or laggard: top relative strength
- **I**nstitutional sponsorship: increasing ownership
- **M**arket direction: confirmed uptrend

### VCP (Volatility Contraction Pattern)
- Screen S&P 500 for VCP setups
- Identify contraction phases (3+ contractions)
- Mark pivot points for entry
- Volume dry-up in contractions
- Volume expansion on breakout

### Breakout Trade Planning
- Entry: pivot point + small buffer
- Stop: below last contraction low or 7-8% from entry
- Target: 20-25% gain or trailing stop
- Position size: (account_risk%) / (entry - stop)
- Portfolio heat: sum of all position risks ≤ total account risk limit

### Earnings Analysis
- 5-factor scoring:
  1. Gap Size
  2. Pre-Earnings Trend
  3. Volume Trend
  4. MA200 Position
  5. MA50 Position
- PEAD screening for post-earnings drift

### Theme Detection
- Identify trending themes across sectors
- Calculate theme heat scores
- Correlate with swing opportunities

## Position Sizing Formula

```
risk_per_trade = account_size * risk_percentage (typically 0.01-0.02)
share_count = risk_per_trade / (entry_price - stop_price)
dollar_risk = share_count * (entry_price - stop_price)
```

## Outputs

- `canslim_candidates`: screened stocks with composite scores
- `vcp_candidates`: tickers, pivot points, contraction data
- `entry_plan`: entry, stop, target, shares, risk amount
- `alpaca_order`: stop-limit bracket or limit bracket JSON
- `earnings_scores`: 5-factor grades
- `theme_report`: trending themes + heat scores
