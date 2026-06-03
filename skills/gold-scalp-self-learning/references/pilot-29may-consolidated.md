# Pilot Results — 29 May 2026

**Command:** `hermes_self_learning.py --days 30 --population 50 --generations 2 --max-trials 50`
**Account:** 591712391 (FxPro Demo, Mykola Ievtushenko) $1556.52
**Symbol:** GOLD, Lot: 0.03

## Baseline (current params, V1+V2+V3, Alligator=hard)
| Metric | Value |
|--------|-------|
| Trades | 384 |
| Win Rate | 61.2% |
| Expectancy | $2.33/trade |
| Total PnL | +$892.81 |
| Max DD | $2,224.41 |

## Optimized V1 (best of 50 combos)
| Metric | Value |
|--------|-------|
| Score | 7.394 |
| Trades | 209 |
| Win Rate | 57.4% |
| Expectancy | **$15.35/trade** |
| Total PnL | +$3,209 |
| Max DD | **$760** |
| Profit Factor | 1.24 |

**Best params:** score_threshold=4, rsi5_strong_oversold=30, rsi5_mild_oversold=40, ema_distance_max=15pts, pullback_candles_min=4, fatigue_limit=6, fatigue_window=10, rsi15_buy_cap=55, rsi15_sell_floor=45, atr_sl_mult=0.7, atr_tp_mult=2.0

## Optimized MANAGEMENT
| Metric | Score | Exp | DD |
|--------|-------|-----|-----|
| Best | 14.825 | $15.35 | $759.57 |

**Best params:** trailing_activate=80, trailing_offset=100, trailing_step=80, partial_trigger=100, partial_fraction=0.5
→ **Identical to current daemon params** ✅

## A/B Alligator-gate
| Mode | Trades | WR | Exp | Total PnL |
|------|--------|----|------|-----------|
| **hard** ✅ | 209 | 57.4% | $15.35 | +$3,208.53 |
| off | 495 | 54.7% | $12.19 | +$6,034.12 |

**Winner:** hard (higher exp, better risk control)

## Final Combined (V1 opt + Mgmt opt + Alligator=hard)
| Metric | Value | Δ from baseline |
|--------|-------|-----------------|
| Trades | 209 | -45% (fewer, better quality) |
| Win Rate | 57.4% | -3.8pp |
| Expectancy | $15.35 | **+6.6x** |
| Total PnL | +$3,208.53 | +$2,345.74 (+260%) |
| Max DD | $759.57 | -66% |

## Real Deals Analysis (17 closed deals)
| Metric | Value |
|--------|-------|
| Total | 17 |
| Wins | 13 (76.5%) |
| Losses | 4 |
| PnL | +$11.77 |

**Patterns detected:**
- ASYMMETRIC_RISK (avg loss -$11.03 vs avg win $4.30 — TP too tight vs SL)
- TOXIC_HOURS (14:00 UTC = -$19.44)

## Discovered Regimes (6036 bars M5)
| Regime | Bars |
|--------|------|
| TREND_DOWN | 2,831 |
| TREND_UP | 2,381 |
| RANGE_VOLATILE | 441 |
| RANGE_QUIET | 326 |
| UNKNOWN | 49 |
| BREAKOUT_UP | 7 |
| BREAKOUT_DOWN | 1 |

## Known Bugs Fixed
1. **grid_mgmt too narrow** — old: 3×3×3×3×3=243. New: 4×4×4×4×2=512 (coarse), includes 50/120 ranges
2. **evolve() parameter name** — `generations` → `gens`. Function sig: `def evolve(df, seeds, gens, elite_k, off_elite)`. Caller used `generations=`. Fixed.

## Crash Recovery Chronology (29 May)
| Attempt | Command | Crashed at | Fix required |
|---------|---------|------------|-------------|
| #1 | --max-trials 200 | MANAGEMENT | grid_mgmt() too narrow |
| #2 | --mode analyze_deals --discover | Baseline only (wrong mode) | Запущен not grid mode |
| #3 | --max-trials 200 (restart) | PHASE 2 evolve() | generations→gens |
| #4 | --max-trials 50 (restart) | ✅ Done | — |

## Обновление стратегий 29 May

**Изменения после пилота:** параметры стратегий НЕ МЕНЯЛИСЬ — все лучшие параметры идентичны текущим в мониторе и демоне. Подтверждено обоими прогонами (score=14.8 и score=26.2).

Сохранены файлы для запуска полного прогона (180 дней, --discover), ожидается завершение пилота.
