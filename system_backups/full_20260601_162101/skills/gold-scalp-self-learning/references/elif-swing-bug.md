# Swing find_swings bug — `elif` blocks SELL

## Discovery (1 June 2026)

In V5.0 monitor (`_gold_monitor_v50.py`), the signal detection used:

```python
if nearest_high:
    # BUY: пробой swing high
    if prev_c <= nearest_high and last_c > nearest_high:
        signal = {"action": "BUY", ...}

elif nearest_low:
    # SELL: пробой swing low
    if prev_c >= nearest_low and last_c < nearest_low:
        signal = {"action": "SELL", ...}
```

## Bug

`elif` means: if `nearest_high` is truthy (any swing high exists), the `elif nearest_low` branch is NEVER evaluated.
A swing high always exists if the lookback window has at least one high. So SELL signals are **always blocked** as long as there's any swing high in the data.

The condition `if nearest_high` is about **existence**, not **proximity**. Even if the nearest swing high is +15pts away (far from current price), it's still truthy → SELL never fires.

## Fix

```python
if nearest_high:
    if prev_c <= nearest_high and last_c > nearest_high:
        signal = {"action": "BUY", ...}

if not signal and nearest_low:
    if prev_c >= nearest_low and last_c < nearest_low:
        signal = {"action": "SELL", ...}
```

## General rule

When two conditions both depend on **data existence** (not mutually exclusive states like up/down), use two `if` blocks with a `not signal` guard.

✅ Good for `elif`:
```python
if trend == "UP":
    ...
elif trend == "DOWN":
    ...
```
(Mutually exclusive states — only one can be true)

❌ Bad for `elif`:
```python
if nearest_high:
    ...  # barrier or level exists ABOVE
elif nearest_low:
    ...  # level BELOW — NEVER REACHED if above exists
```
(Independent conditions — both can be true simultaneously)
