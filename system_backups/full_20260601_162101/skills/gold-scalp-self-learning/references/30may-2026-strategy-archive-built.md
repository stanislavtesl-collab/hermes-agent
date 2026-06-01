# 30 May 2026 — Strategy Library Archive Built + Run #6 (утренний прогон)

## Что сделано
1. Запущен третий 180-дневный прогон `hermes_self_learning.py` в 07:32 → завершён ~09:38
2. Создан архив стратегий `C:\Users\Administrator\Desktop\FxPro\strategy_library\`
3. В архив сохранены: V1 основная, топ-5 эволюционных, регим-роутер
4. Создана утилита `read_strategy.py` для просмотра

## Результаты Run #6

### Baseline vs Final
| Метрика | Baseline | Final | Δ |
|---------|----------|-------|---|
| Сделок | 2,254 | 1,385 | -39% |
| Win Rate | 59.9% | 53.6% | -6.3pp |
| Expectancy | $1.12 | **$39.70** | ×35 |
| Profit Factor | 1.02 | **1.79** | +75% |
| Max DD | $5,150 | **$2,435** | -53% ✅ |

### V1 top-1 (score=14.25)
- n=556, WR=57.0%, exp=$19.73, PF=1.43, DD=$1,761
- RSI5: oversold 30 / overbought 70, EMA=20pts, TP=×2.5

### A/B Alligator-gate
- Hard: n=557, WR=57.1%, exp=$41.91, PF=1.93, DD=$1,764
- Off: n=1,385, WR=53.6%, exp=$39.70, PF=1.79, DD=$2,435
- **System chose: off** (higher total PnL due to 2.4× more trades)
- Consistency note: Run #4/#5 chose hard, Run #6 chose off. The scoring formula favors total PnL.

### MANAGEMENT (score=30.3)
- Trail: 50/60/50, Partial: 30%@150pts — **unchanged from previous runs**

### Phase 2 — Evolutionary Strategies
- 5 generations, 300 initial pop → 30 survivors
- Top-1: auto_0630 — n=24, WR=75%, exp=$226.85, PF=4.41, DD=$365
- Top by regime: auto_0894 (TREND_DOWN $378, RANGE_VOLATILE $507)

### Real deals analysis
- 25 trades, WR=76%, PnL=$10.18
- ASYMMETRIC_RISK pattern — fixed by TP ×1.5→×2.5
- TOXIC_HOURS: 14:00 (−$19.44), 20:00 (−$8.06) — needs time-filter

## Структура архива
```
strategy_library/
├── _v1_strategy.md           # V1 с полным описанием
├── _regime_router.md         # Роутер
├── _index.json               # Индекс 30 стратегий
├── read_strategy.py          # CLI просмотр
├── README.md
├── auto_0630/                # Топ-1 (WR 75%, exp $227)
├── auto_0894/                # Топ по RANGE_VOLATILE
├── auto_0633/                # RANGE_VOLATILE
├── auto_0658/                # TREND_UP
└── auto_0800/                # RANGE_QUIET
```
