---
name: core-portfolio
description: >
  Long-term portfolio management and dividend investing for US equities.
  Use for weekly portfolio reviews, dividend health monitoring, rebalancing,
  value-dividend screening, Kanchi-style income portfolio management,
  and tax-efficient account location advice.
---

# Core Portfolio Management

## Weekly Workflow

1. **Portfolio Overview**
   - Fetch current holdings (via Alpaca or manual input)
   - Calculate allocation by sector, market cap, style
   - Assess diversification metrics
   - Generate rebalancing recommendations

2. **Dividend Health Check**
   - Review dividend growth rates (target: 12%+ annual)
   - Check yield levels (target: 1.5%+ for growth, 3%+ for value)
   - Verify payout ratios are sustainable
   - Flag any dividend cuts or freezes

3. **Kanchi-Style Review**
   - T1-T5 anomaly detection:
     - T1: Yield dropped below purchase yield
     - T2: Dividend growth stalled
     - T3: Payout ratio exceeded 80%
     - T4: Credit rating downgrade
     - T5: Sector weight exceeded 15%
   - Convert anomalies to OK / WARN / REVIEW states
   - Generate review queue (no auto-selling)

4. **Screener Runs**
   - Value-Dividend: P/E <20, P/B <2, yield ≥3%, consistent growth
   - Dividend Growth Pullback: 12%+ growth, 1.5%+ yield, RSI ≤40
   - Quality filters: revenue/EPS trending up 3 years

5. **Tax & Account Location**
   - Qualified vs ordinary dividend classification
   - Account location advice (taxable vs tax-advantaged)
   - 1099-DIV preparation guidance

## Key Metrics

| Metric | Target | Alert |
|--------|--------|-------|
| Dividend Growth | ≥12%/year | <8% |
| Yield (Growth) | ≥1.5% | <1.0% |
| Yield (Value) | ≥3.0% | <2.5% |
| Payout Ratio | <80% | >90% |
| P/E Ratio | <20 | >25 |
| P/B Ratio | <2 | >3 |
| Sector Weight | <15% | >20% |

## Outputs

- `allocation_report`: current vs target allocation
- `rebalance_actions`: specific buy/sell/hold recommendations
- `review_queue`: T1-T5 anomalies requiring review
- `screener_results`: new candidates with scores
- `tax_report`: qualified/ordinary classification
