# Atman-v04 FINAL v4 — Confirmed Results (30 May 2026)

## Run Details
- **Script:** `atman_v04_final_v4.py` (vectorized batch simulation, 8,307 bars)
- **Grid:** 2,560 configs (8 TP × 5 SL × 5 BE × 4 Trail × 4 Hours × 2 DOW)
- **Duration:** 14 seconds (94× faster than v3's 22 minutes)
- **Patterns:** A (TRENDING), C (daily range breakout)
- **Exit:** 0 (normal completion)
- **Output:** `results/atman_v04_final_v4_results.json`

## 🏆 TOP 20 (min 15 trades)

```
#1:  PF=60.40  WR=80%  +$104  DD=$1  n=25  SH=134.96
     TP=650 SL=120 BE=0.25 Trail=20 H=13-20 D=not_mon  A:n=25 PF=60.40 +$104

#2:  PF=59.78  WR=80%  +$103  DD=$1  n=25  SH=134.96
     TP=650 SL=120 BE=0.30 Trail=30 H=13-20 D=not_mon  A:n=25 PF=59.78 +$103

#3:  PF=59.78  WR=80%  +$103  DD=$1  n=25  SH=134.96
     TP=650 SL=120 BE=0.35 Trail=30 H=13-20 D=not_mon  A:n=25 PF=59.78 +$103

#4:  PF=59.50  WR=80%  +$102  DD=$1  n=25  SH=133.54
     TP=650 SL=120 BE=0.25 Trail=40 H=13-20 D=not_mon  A:n=25 PF=59.50 +$102

#5:  PF=59.50  WR=80%  +$102  DD=$1  n=25  SH=133.54
     TP=650 SL=120 BE=0.30 Trail=40 H=13-20 D=not_mon  A:n=25 PF=59.50 +$102

#6:  PF=58.35  WR=84%  +$95   DD=$1  n=25  SH=153.65
     TP=555 SL=120 BE=0.30 Trail=20 H=13-20 D=not_mon  A:n=25 PF=58.35 +$95
```

## Key Findings

### Pattern A Only
- **100% of top-20 configs rely exclusively on Pattern A.**
- Pattern C produced 0 trades in any top-performing config.

### Parameter Stability
- **SL=120** — dominates ALL top-20. Wider SL never wins.
- **H=13-20** — ALL top-20 use this hour window. No other hours appear.
- **DOW=not_mon** — ALL top-20. Monday is toxic.
- **TP=650** — wins at the very top; TP=555 close behind.
- **BE=0.25-0.50** — minor variation, all produce similar results.

### Scaling to Real Account
- 0.01 lot → +$104 over 5 months (+6.7% on $1,550)
- 0.03 lot → **+$312** over 5 months (+20% on $1,550)
- Per month: ~5 trades, +$20 (0.01 lot) or +$62 (0.03 lot)

## v4 Architecture (95× Speedup)

The critical breakthrough that made this analysis possible. Instead of calling `run_params()` 2,560 times iterating 8,000 bars each, the script runs **one pass over bars** tracking state for ALL configs simultaneously in numpy arrays.

**Implementation tips for future runs:**
1. Convert configs to parallel numpy arrays (tp_arr, sl_arr, be_arr, trail_arr, hs_arr, he_arr)
2. Use `np.int8` for direction (0=none, 1=long, -1=short)
3. Vectorize bar-level filters with `(hh[i] >= hs_arr) & (hh[i] <= he_arr)`
4. Only iterate active configs with `np.where(active)[0]`
5. Only entry-check configs with `~active & bar_ok`
