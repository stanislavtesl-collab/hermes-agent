---
name: strategy-research
description: >
  Systematic trading strategy research, edge detection, and backtesting.
  Use when developing new trading strategies, analyzing edge candidates,
  designing backtests, reviewing strategy performance, or synthesizing
  multi-signal conviction scores. Includes Druckenmiller-style synthesis,
  scenario analysis, and strategy pivot design.
  MANDATORY: Apply Triple-Check Protocol before deploying any new strategy.
---

# Strategy Research Pipeline

## Edge Research Workflow

### Phase I: Candidate Detection
1. Generate edge tickets from EOD observations
2. Identify anomalies and market inefficiencies
3. Export pipeline-ready candidate specs

### Phase II: Hint Extraction
1. Extract edge hints from observations/news
2. Canonical `hints.yaml` output
3. LLM-assisted ideation (optional)

### Phase III: Concept Synthesis
1. Abstract tickets + hints into edge concepts
2. Define thesis, invalidation signals, strategy playbooks
3. Validate conceptual soundness

### Phase IV: Strategy Design
1. Convert concepts into strategy draft variants
2. Define rules, parameters, entry/exit logic
3. Export `strategy_drafts.yaml`

### Phase V: Strategy Review
1. Review for edge plausibility
2. Check overfitting risk
3. Validate sample size adequacy
4. Assess execution realism
5. Verdict: PASS / REVISE / REJECT

### Phase VI: Backtest & Export
1. Historical backtesting
2. Performance metrics calculation
3. Walk-forward validation
4. Export final strategy

## Druckenmiller-Style Synthesis

Integrate 8 upstream signals into unified conviction score (0-100):
1. Market Breadth composite
2. Uptrend Analysis composite
3. Market Top probability
4. Macro Regime assessment
5. FTD signal confidence
6. VCP Screener output
7. Theme Detector heat scores
8. CANSLIM Screener output

Weight and synthesize with exposure decision overlay.

## Scenario Analysis

From news headlines:
1. Primary impact analysis (direct effects)
2. Secondary impact (supply chain, competitors)
3. Tertiary impact (macro, sentiment)
4. Stock picks for each scenario
5. Strategy-reviewer second opinion

## Strategy Pivot Design

When backtest stagnation detected:
1. Analyze iteration history
2. Identify local optimum trap
3. Generate structurally different proposals
4. Include parameter regime changes
5. Validate new concepts independently

## 🔁 Triple-Check Protocol (MANDATORY before deploying any strategy)

Before committing to any new strategy or modifying entry/exit rules:

**Pass 1 — Initial Design:** Write the full logic. All conditions, all filters, all indicators.

**Pass 2 — Second Look (30s pause):** Re-read every condition critically. Ask: "Does this condition actually block a bad entry, or is it just decoration?" Mark candidates for removal. If a condition duplicates another (e.g. "price near EMA20" + "distance < 15pts from EMA20"), merge them.

**Pass 3 — Final Trim (another 30s pause):** Count the conditions. If >5-6, you are overfitting. The best strategies have 4 load-bearing conditions. Strip everything that isn't essential. Keep indicators that directly tell you something about price action (oversold/overbought, trend direction, exhaustion). Move everything else (Fib levels, fractals, Alligator, cross-confirmations that fire every 2 hours) to an **information layer** — log them for learning, but do NOT let them block entries.

**Golden rule:** 4 clean conditions beat 8 decorated ones. The extra 4 conditions reduce entry frequency by 80% while eliminating only 5% of the bad entries you'd catch with a simpler filter. The other 75% missed good trades.

**Real-world example from GOLD scalp session:** V1 strategy started with 8 conditions (RSI5, EMA distance, Fibo proximity, fractal confirmation, Alligator state, candlestick count, M15 RSI, volume threshold). After triple-check: 4 conditions (RSI5 oversold, EMA20 proximity, candlestick exhaustion, M15 overbought guard). Entry quality unchanged. Frequency improved 3x.

## Outputs

- `edge_concepts.yaml`: thesis + invalidation + playbook
- `strategy_drafts.yaml`: rules + parameters + logic
- `review_yaml`: plausibility + risk assessment + verdict
- `druckenmiller_report`: conviction score + synthesis
- `scenario_report`: impacts + stock picks
- `pivot_proposals`: alternative strategy designs
