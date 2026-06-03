# Grid-Search Performance Optimization

## The Problem

Grid-search backtesting loops are deceptively expensive. A naive implementation that recomputes indicators for every parameter combination can explode runtime:

```
1,440 configs × O(n) per config = 42+ minutes
vs
1 pass O(n) + 1,440 O(1) configs = 3-4 minutes
```

## The Fix: Precompute Once, Vary Only Entry/Exit Params

### Architecture

```
┌─────────────────────────────────────────────┐
│ Phase 1: PREPARE (one-time, O(n))           │
│  • Load & clean data                        │
│  • Compute ALL indicators (ADX, ATR, ER...) │
│  • Detect regimes                           │
│  • Precompute swing levels                  │
│  • Save to DataFrame columns                │
└─────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────┐
│ Phase 2: GRID LOOP (n-configs, O(1) each)   │
│  for each config:                           │
│    simulate_fast(df_prepared, params)       │
│     → only adjusts SL/TP/BE price points    │
│     → one pass over bars                    │
│     → no indicator recalculation            │
└─────────────────────────────────────────────┘
```

### Good Implementation Pattern

```python
# === PHASE 1: PREPARE ===
df = load_data()
df = add_indicators(df)          # ADX, ATR, ER — once
df = detect_regime(df)           # TRENDING/RANGING labels — once
df = precompute_swings(df)       # H4 swing levels assigned to each bar — once

def simulate_fast(df, tp, sl, be, hours, filter):
    """Fast backtest. df already has all indicators."""
    for i in range(200, len(df)):
        if df.iloc[i]["regime"] != "TRENDING": continue
        if df.iloc[i]["hour"] not in hours: continue
        # ... use precomputed levels, no indicator calls
```

### What NOT to Do

```python
# WRONG — recreates indicators for every config
def grid_search(df_raw):
    results = []
    for tp in TP_VALS:
        for be in BE_VALS:
            df = add_indicators(df_raw.copy())   # ← O(n) each time!
            trades = simulate(df, params)
            ...
```

### Verification

Check speed by timing the prepare phase vs grid phase:
```python
t0 = time.time()
df = prepare()    # one-time
t1 = time.time()
print(f"Prepare: {t1-t0:.0f}s")

for config in configs:
    trades = simulate_fast(df, config)
t2 = time.time()
print(f"Grid: {(t2-t1)/len(configs):.1f}s per config")
```

If grid phase is >5s per config on 10k+ bars, you're recomputing something.
