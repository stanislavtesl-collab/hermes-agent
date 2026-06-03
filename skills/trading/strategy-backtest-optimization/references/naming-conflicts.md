# Python Backtest Script Naming Conflicts

## The Problem
When writing Python backtest scripts, the variable name `ts` is dangerously overloaded:

1. **`ts` as timestamp** — e.g. `ts = test['time'].values[idx]` → produces `numpy.datetime64`
2. **`ts` as trail step** — e.g. `ts=10` → produces `int` or `float`
3. **`ts` as trade struct key** — e.g. `ot['ts']` or `trades.append({'ts': ...})`

## Symptom
```
numpy._core._exceptions._UFuncBinaryResolutionError: ufunc 'multiply' cannot use operands 
with types dtype('<M8[s]') and dtype('float64')
```

This appears when numpy tries to multiply a datetime64 (from `ts`) by a float (assuming it's the trail step).

## Fix
| What | Name | Example |
|---|---|---|
| Timestamp variable | `ts_now` or `ts_time` | `ts_now = test['time'].values[idx]` |
| Trail step parameter | `trail_step` or `ts_step` | `def run(..., trail_step=10):` |
| Trail offset parameter | `trail_off` or `offset` (not `to`) | `def run(..., trail_off=30):` |
| Trade struct keys | full names | `{'time':..., 'dir':'B', 'entry':..., 'sl':...}` |

## Other Common Failure Patterns

### `pd.Series.ewm().values`
**Wrong:** `ema = pd.Series(c5).ewm(span=20, adjust=False).values`
**Fix:** Add `.mean()` → `pd.Series(c5).ewm(span=20, adjust=False).mean().values`

### `searchsorted` returning len(arr)
```python
gi = d5['time'].searchsorted(test['time'].values[idx])
gi = min(gi, len(r5v) - 1)  # ALWAYS clamp
```

### RSI array shorter than source
`rsi()` with min_periods=N returns an array N elements shorter than input (first N-1 values are NaN). 
When mapping indicators across TFs, always clamp to `min(j, len(rsi_arr)-1)`.

### ATR array construction
```python
# WRONG: h1_tr has shape (N-1,) and h1_atr ends up (N-1,)
h1_tr = np.maximum(hh1[1:]-lh1[1:], ...)
h1_atr = pd.Series(h1_tr).rolling(14).mean().values  # SHORTER THAN EXPECTED

# CORRECT: pad the first element
h1_tr = np.maximum(...)
h1_tr = np.concatenate([[h1_tr[0]], h1_tr])
h1_atr = pd.Series(h1_tr).rolling(14).mean().values  # SAME LENGTH AS INPUT
```
