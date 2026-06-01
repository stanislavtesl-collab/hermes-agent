# Self-Learning Module — Full Instruction (from Claude, 30 May 2026)

Source: User asked another AI (Claude) to write a self-learning module for Hermes Agent.
Claude produced `hermes_self_learning.py` (~800 lines) with grid-search, evolutionary strategy discovery, and regime router.

## Core concept
The script does NOT open real trades. It:
1. Connects to MT5 (FxPro Demo, GOLD)
2. Fetches M1/M5/M15/H1 history for N days
3. Computes indicators (RSI, EMA, ATR, Alligator, VWAP, Fibo)
4. Backtests V1/V2/V3 with SL/TP/trailing/partial/Alligator-gate
5. Grid-search for optimal V1/V2/V3/MGMT parameters
6. Analyzes real deals for loss patterns
7. Phase 2: random strategy generation from DSL, evolutionary selection
8. Regime router: market phase → top strategies
9. Saves JSON reports + markdown report

## Launch (Windows Git-Bash)
```
"/c/Program Files/Python312/python.exe" hermes_self_learning.py --days 180 --discover
```

## Files produced
- `.hermes_optimal_params.json` — new params for _gold_monitor_v3.py and gold_manager_daemon.py
- `.hermes_learning_report.md` — full report with top results, A/B Alligator, patterns
- `.hermes_backtest_trades.csv` — every simulated trade
- `.hermes_failure_patterns.json` — real-deal loss patterns
- `.hermes_strategy_library.json` — evolved strategy library
- `.hermes_regime_router.json` — phase → top strategies
- `.hermes_learning.log` — full run log

## Integration into live system
1. Stop executor and monitor. Keep daemon alive.
2. Read `.hermes_learning_report.md`
3. Backup live files: `cp _gold_monitor_v3.py _gold_monitor_v3.py.bak_$(date +%Y%m%d_%H%M)`
4. Add OPT loader to `_gold_monitor_v3.py` and `gold_manager_daemon.py`
5. Replace hardcoded numbers with `OPT['V1']['...']` etc.
6. Compile check: `python -m py_compile _gold_monitor_v3.py`
7. Restart: daemon → executor → monitor
8. Observe first session (4-6 hours) — if 3 losses in a row, rollback

## Retraining cycle
Every 7 days (Monday 03:00 UTC recommended).
After 2-3 months: 50+ strategies expected, V4 monitor as ensemble.
