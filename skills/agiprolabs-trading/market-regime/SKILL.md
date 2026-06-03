---
name: market-regime
description: >
  Market regime detection and daily market posture assessment for US equities.
  Use when analyzing market breadth, uptrend participation, distribution days,
  follow-through days, macro regime transitions, or determining daily exposure posture.
  Essential pre-trade risk layer for swing trading decisions.
---

# Market Regime Detection

## Daily Workflow

1. **Market Breadth Analysis**
   - Load S&P 500 breadth data (200-Day MA based)
   - Calculate composite breadth score
   - Assess participation breadth

2. **Uptrend Analysis**
   - Load uptrend stock ratio data
   - Calculate uptrend composite score
   - Identify trend strength/weakness

3. **Distribution Day Monitor**
   - Check QQQ/SPY for distribution days (close down ≥0.2% on higher volume)
   - Track 25-session expiration and 5% invalidation
   - Count d5/d15/d25 clusters
   - Classify risk: NORMAL / CAUTION / HIGH / SEVERE

4. **Market Top Detection**
   - Monitor O'Neil distribution days
   - Track leading stock deterioration
   - Watch defensive sector rotation
   - Calculate composite top probability score

5. **Follow-Through Day Detection**
   - Monitor QQQ/SPY for FTD signals
   - Confirm market bottom using O'Neil methodology
   - Validate with volume and breadth

6. **Macro Regime Detection**
   - Analyze cross-asset ratios (growth/value, cyclicals/defensives)
   - Monitor yield curve data
   - Detect structural regime transitions (1-2 year horizon)

7. **Exposure Decision**
   - Synthesize all signals into posture: allow / restrict / cash-priority
   - Generate one-page Market Posture summary
   - Include net exposure ceiling and growth-vs-value bias

## Key Thresholds

- Distribution Day: close down ≥0.2% on higher volume than prior session
- FTD: Day 4+ of rally attempt, close up ≥1.7% on higher volume
- RSI Oversold: ≤40 (for dividend pullback screening)
- Uptrend ratio deterioration: significant drop from recent highs

## Outputs

- `exposure_decision`: allow / restrict / cash-priority + ceiling
- `breadth_composite_score`: 0-100 scale
- `distribution_day_count`: d5/d15/d25 clusters
- `ftd_signal`: present/absent + confidence
- `macro_regime`: description + transition probability
