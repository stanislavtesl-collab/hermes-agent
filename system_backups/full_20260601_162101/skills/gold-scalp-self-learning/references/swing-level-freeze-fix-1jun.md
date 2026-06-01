# Swing Level Freeze Fix — 1 June 2026

## The Bug

V5.0 monitor (`_gold_monitor_v50.py`) recalculated swing levels from live M5 data on EVERY loop cycle (every 8-15s). When price was in a gradual downtrend (e.g. $4,501 → $4,499 over 4 bars), the swing low kept updating every cycle. The breakout condition `prev_c >= swing_low and last_c < swing_low` **never triggered** because the reference level moved down with the price.

**Result:** Price dropped $4,501 → $4,497, but V5.0 monitor never saw a "breakout" and never emitted a SELL signal. The swing low simply followed the price down.

This was observed on 1 June 2026 session: swing low was $4,501.23 at 15:15, then price went to $4,498.91 at 15:20 (new swing low $4,497.44). Monitor kept seeing $4,497, $4,496 as swing lows — no breakout detected.

## The Fix

**Save swing levels to a state file: `.v50_levels.json`**

Levels are only updated (re-calculated from live data) when one of these conditions is true:
1. **No saved levels exist** — first run, force refresh
2. **Signal was triggered** — trade opened, levels must be fresh for next entry
3. **Price has moved 50+pts away from the saved level** — level is no longer relevant (trend reversal / fakeout recovered)

## Signal Detection (Updated)

```python
saved = load_levels()  # from .v50_levels.json
fixed_high = saved["high"]
fixed_low = saved["low"]

# BUY: breakout of FIXED swing high
if prev_c <= fixed_high and last_c > fixed_high:
    signal = BUY

# SELL: breakout of FIXED swing low
if not signal and prev_c >= fixed_low and last_c < fixed_low:
    signal = SELL

# After signal: refresh levels
if signal:
    update_levels(force=True)
```

## find_swings() Simplification

Original function used a complex neighbor-comparison loop to find "true swing" pivot points:

```python
for j in range(1, lookback):
    if highs[i-j] >= highs[i] or highs[i+j] >= highs[i]:
        is_high = False
```

This **returned None, None on trending data** because every bar in a strong trend has a neighbor with a higher high / lower low. On 1 June 2026 test data, this returned `None` for ALL 60 bars.

**Fix:** replaced with simple `max(highs[-lookback:]) / min(lows[-lookback:])`. This is less elegant but always returns a usable level.

## Default Levels (set at monitor startup)

Monitor prints at startup:
```
[Monitor V5.0] MT5 connected, account: 591712391
Initial levels: high=4512.93 low=4499.84
```

## Verification

After fix, levels stayed at `high=4512.93 low=4499.84` for the entire session — they didn't drift down with the price. The monitor was ready for a breakout signal.

## Files Changed

- `_gold_monitor_v50.py` — full rewrite of `find_swings()` and `check_signal()`, added `load_levels()`/`save_levels()`/`update_levels()` functions

## V5.0 Executor Heartbeat (Also Added 1 June 2026)

V5.0 executor had no heartbeat file initially. User saw "🚀 EXECUTOR V5.0 STARTED" but there was no way to verify it was alive from Git-Bash. Added:

```python
HEARTBEAT_FILE = os.path.join(WORKDIR, ".gold_executor_v50_heartbeat.json")

# In main loop:
hb = {"last_check": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()}
with open(HEARTBEAT_FILE, "w") as f:
    json.dump(hb, f)
```

## Side Note: V4.2 Executor Signal Check Fix

Monitor V4.2 generated signals with `"source": "monitor_v42"` but executor checked for `sig.get("data_source") == "MT5_ONLY"` — a field that never existed. This meant **executor never acted on signals**. Fixed: removed the `data_source` check.

Also added heartbeat to V4.2 executor using same pattern as V5.0.
