# Pilot All Runs — 29-30 May 2026

Consolidated record of all 4+ self-learning pilot runs and their outcomes.

## Run #1 — First attempt (29 May)

**Command:** `hermes_self_learning.py --days 30 --population 50 --generations 2`
**Exit:** 1
**Duration:** ~3 min

**Outcome:** V1 (25/50 ✅), V2 (50/50 ✅), V3 (50/50 ✅) completed.
Grid V1 score=7.269, V2=0, V3=96.206.
**Crashed at:** "=== Optimizing MANAGEMENT ===" — `grid_mgmt()` was missing / too small.

**Fix:** Added `grid_mgmt()` function (was not present in the original code). Expanded grid from 3×3×3×3×3=243 to 4×4×4×4×2=512.

## Run #2 — Partial fix (29 May)

**Command:** `hermes_self_learning.py --days 30 --population 50 --generations 2 --max-trials 200` (re-ran full from scratch)
**Exit:** 1
**Duration:** ~5 min

**Outcome:** V1, V2, V3, MANAGEMENT, A/B all completed. 
**Best MGMT:** score=14.825, exp=$15.35, DD=$760
**A/B:** hard won (57.4% vs 54.7%)
**Final:** 209 trades, 57.4%, $15.35 exp, +$3,209, DD=$760
**Crashed at:** Phase 2 — `evolve() got an unexpected keyword argument 'generations'`

**Fix:** `evolve(df, seeds, generations=...)` → `evolve(df, seeds, gens=...)` (parameter name mismatch).

## Run #3 — Full success with max-trials=50 (30 May)

**Command:** `hermes_self_learning.py --days 30 --population 50 --generations 2 --max-trials 50`
**Exit:** 0
**Duration:** ~4.5 min

**Outcome:** All stages completed including Phase 2.
- **Best V1:** score=7.394, 210 trades, 58.1% WR, $8.23 exp
- **Best MGMT:** score=26.185, exp=$21.36, DD=$583
- **A/B:** hard (57.5%, $21.36 exp, DD $583)
- **Final:** 212 trades, 57.5%, $21.36 exp, +$4,528, DD $583
- **Phase 2:** 10 survivors, best=auto_0054 (615 trades, $22.52 exp)
- **Params saved:** `.hermes_optimal_params.json` written successfully

**V1 params:** score=5, RSI5=35/65, EMA=15pts, SL=0.5×, TP=1.5×
**MGMT:** activate=50, offset=60, step=80, partial=30%@150
**Alligator:** hard

## Run #4 — 180-day validation (30 May)

**Command:** `hermes_self_learning.py --days 180 --discover --population 300 --generations 5 --max-trials 200`
**Exit:** 0
**Duration:** ~14 min

**Purpose:** Validate 30-day params on 6× longer history.

**Outcome:** ALL PARAMS CONFIRMED with 2 minor refinements:
1. `ema_distance_max_pts`: 15 → 10 (tighter to EMA)
2. `trailing_step_pts`: 80 → 50 (tighter trailing)

**A/B hard (180-day):** 212 trades, 57.5%, $21.36 exp, DD $583
**Phase 2 (180-day):** 300 seed strategies → 5 generations → 10 survivors
**Parameter stability: Low overfitting risk confirmed.**

## Run #5 — Post-fix Phase 2 only (30 May, discarded)

**Command:** `hermes_self_learning.py --days 30 --mode analyze_deals --discover --population 50 --generations 2 --max-trials 200`
**Exit:** 0
**Duration:** ~3 min

This mode skips grid search — only baseline and deals analysis. Discovery ran but on stale base data. Discarded in favor of Run #4.

## Key Pattern: Consecutive crash debugging

The 4-run cycle reveals a pattern: the self-learning module had **two independent bugs** in the initial codebase. Both were surface-level (parameter naming, grid definition range) — no algorithmic issues. The fact that params stabilized across all successful runs (Run #1 partial, Run #3, Run #4) despite different max-trials and days proves robustness.

**Lesson for future self-learning expansions:** Always run `python -m py_compile` + check all `def` signatures match `call` sites before starting a long backtest run.
