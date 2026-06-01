---
name: trade-memory
description: >
  Trade journaling, thesis tracking, and performance analytics.
  Use when tracking investment theses, recording trade outcomes,
  generating trade hypotheses, conducting postmortems, or performing
  monthly performance reviews.
---

# Trade Memory & Journaling

## Thesis Lifecycle Tracking

### States
1. **IDEA** → Screener or research identifies candidate
2. **RESEARCH** → Deep analysis and strategy development
3. **STAGED** → Order placed, awaiting entry
4. **OPEN** → Position active, monitoring
5. **CLOSE_CANDIDATE** → Hit target or stop approaching
6. **CLOSED** → Position exited
7. **POSTMORTEM** → Analysis complete, lessons recorded

### Required Fields per Thesis
- Ticker, entry_date, entry_price, thesis_summary
- Stop_price, target_price, position_size, risk_amount
- Exit_date, exit_price, pnl_amount, pnl_percent
- Exit_reason: target/stop/trailing_stop/manual/earnings
- Lessons_learned, would_trade_again: yes/no/maybe

## Trade Hypothesis Generation

From market data and journal snippets:
1. Extract observations and patterns
2. Formulate falsifiable hypotheses
3. Rank by evidence strength
4. Export to `strategy.yaml` for backtesting

## Signal Postmortem

For closed theses:
1. What was the original thesis?
2. Did the thesis play out as expected?
3. What were the key decision points?
4. What would you do differently?
5. Update edge concepts based on findings

## Monthly Performance Review

1. Win rate (number and dollar-weighted)
2. Average winner vs average loser
3. Profit factor (gross wins / gross losses)
4. Maximum drawdown
5. Sharpe ratio approximation
6. Strategy attribution (which setups worked)
7. Skill gaps and improvement areas

## Outputs

- `thesis_record`: full lifecycle data
- `journal_entry`: narrative + metrics
- `hypothesis_cards`: ranked hypotheses
- `postmortem_findings`: lessons + pattern updates
- `monthly_report`: performance metrics + attribution
