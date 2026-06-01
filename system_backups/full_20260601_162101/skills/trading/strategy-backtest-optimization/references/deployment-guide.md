## Deployment

### Три независимых процесса
- **V4.2 Monitor** (M1 EMA20 breakout) — скальпинг, magic=123462
- **V5.0 Monitor** (M5 swing breakout) — скальпинг, magic=123462
- **M15 Position Monitor** (H4→H1→M15) — позиционка 200-250pts, magic=123463, NO partial close

**Один Universal Executor** читает все 3 сигнала и обрабатывает с разным magic. Скальп-сделки получают partial close 30%@+15pts и трейлинг. M15-сделки — без partial close, TP=250pts.

### Параметры трейлинга (настраиваемые)

| Параметр | Ослабленный (позиционка) | Агрессивный | По умолчанию |
|----------|-------------------------|-------------|-------------|
| Активация (когда включается) | 60pts | 15pts | 30pts |
| Offset (SL от цены) | 60pts | 20pts | 30pts |
| Step (шаг подтяжки) | 20pts | 5pts | 10pts |

Увеличение всех параметров в 2x даёт сделке больше пространства. Уменьшение — фиксирует профит быстрее.

### SL при открытии — критичное исправление

**Проблема:** Executor V1 не ставил SL при открытии (SL=0.0 во всех сделках). Трейлинг бесполезен когда сделка идёт против.

**Исправление:** SL ставится в ордере открытия:
```python
request = {"action": mt5.TRADE_ACTION_DEAL, ..., "sl": sl_price}
```
SL_DISTANCE = 8.00 (800pts) для скальпинга. Для M15 — из сигнала.

**numpy-safety:** pos.sl от MT5 может быть numpy array. Явное приведение:
```python
current_sl = float(pos.sl) if pos.sl is not None else None
```

### Ссылки по теме
- references/m15-position-swing.md — стратегия позиционной торговли на M15
- references/averaging-rules.md — усреднение (1 раз, ждёт сильный уровень)
- references/champion-v42-config.md — V4.2 champion config
- references/deployment-guide.md — live deployment на Windows Git-Bash