# Grid Config Dictionary Key Errors

**Bug discovered during 29 May 2026 optimization run.**

## The Bug

The optimizer grid loop uses a `cfg` dict to pass parameters to `run()`. If the dict keys in the loop body *creating* `cfg` don't match the keys *read* inside `run()`, you get `KeyError` at runtime.

## Symptom

```
File "atman_v04_final_v2.py", line 128, in run
    hs, he = cfg["hours"]
KeyError: 'hours'
```

or:

```
KeyError: 'dow'
```

## Root Cause

In the grid loop, configs are stored as:

```python
cfg = {"tp": tp, "sl": sl, "be": be, "trail": trail,
       "h": f"{hs}-{he}",  # "h" not "hours"
       "d": d}              # "d" not "dow"
```

But `run()` reads them as:

```python
hs, he = cfg["hours"]  # WRONG — should be cfg["h"]
dow_f = cfg["dow"]     # WRONG — should be cfg["d"]
```

## The Fix

```python
def run(cfg):
    hs, he = [int(x) for x in cfg["h"].split("-")]
    dow_f = cfg["d"]
```

Or in the grid loop, store with matching keys:

```python
cfg = {"tp": tp, "sl": sl, "be": be, "trail": trail,
       "hours": (hs, he),   # tuple, not string
       "dow": dow_f}
```

The first approach (string split) is preferred because it makes the serialized JSON output cleaner and avoids tuple/list ambiguity.

## Prevention

When writing a new optimizer, immediately create `cfg` and `run()` stubs side-by-side, then verify key names match before running:

```python
# Before writing the grid loop, verify:
def run(cfg):
    hs, he = cfg["h"].split("-")
    assert len(hs) == 2  # "13-20" style
    d = cfg["d"]

# Grid loop
cfg = {"h": "13-20", "d": "not_mon"}  # ← must match exactly
```
