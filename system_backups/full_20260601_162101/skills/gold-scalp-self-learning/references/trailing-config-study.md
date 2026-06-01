# Trailing Stop Tuning — сессия 29.05.2026

## Проблема (сделка #236820560)

- Вход BUY @ 4562.67, трейлинг 100/50/60
- Цена выросла на +135pts (4564.02), трейлинг активировался
- Отступ 50pts → SL=4563.52
- Цена скорректировалась на -50pts → SL сработал → +$1.66
- **После закрытия цена ушла до 4566.97 (+430pts)**

## Симуляция 80/100/80

| Параметр | 100/50/60 (было) | 80/100/80 (стало) |
|----------|------------------|-------------------|
| Активация | +100pts | +80pts (раньше) |
| Отступ | 50pts | 100pts (дышит) |
| Шаг | 60pts | 80pts |
| Итог на сделке | +$1.66 | **+$9.90** |
| Шагов трейлинга | 0 (одно касание) | 5 |

## v8: Partial Close 50%@100pts (DESIGNED, NOT IMPLEMENTED 29 May 2026)

**⚠️ CRITICAL NOTE:** The partial close logic was described in the skill but **never written into the daemon code.**

The daemon (`gold_manager_daemon.py`) has:
- Docstring says "v8" with partial close
- Actual code is pure v7 — no `partial_closed`, `PARTIAL_CLOSE_PTS`, or `PARTIAL_CLOSE_PCT`

**Design intention:**

In addition to the 80/100/80 trail, the daemon should close 50% of lot (0.015) when price reaches +100pts from entry.

**Why +100pts:**
- This is always after trail activation (+80pts)
- Guarantees ~$1.50 profit on the closed half
- The remaining 0.015 trails freely with 80/100/80
- Even if the remaining half hits SL at break-even, the trade is net profitable

**Code to add** — in `check()`, right after new-ticket detection block:
```python
if not partial_closed and trail_active and bar_high >= entry_price + 100:
    pos = mt5.positions_get(ticket=last_ticket)
    if pos and pos[0].volume > 0.01:
        close_vol = round(pos[0].volume * 0.5, 2)
        if close_vol > 0.01:
            req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": "GOLD",
                   "volume": close_vol,
                   "type": mt5.ORDER_TYPE_SELL if pos[0].type == 0 else mt5.ORDER_TYPE_BUY,
                   "position": last_ticket,
                   "price": mt5.symbol_info_tick("GOLD").bid if pos[0].type == 0 else mt5.symbol_info_tick("GOLD").ask,
                   "deviation": 20, "magic": 123456, "comment": "partial_close"}
            result = mt5.order_send(req)
            if result and result.retcode == 10009:
                partial_closed = True
```

**Flag:** `partial_closed` — ensures it fires once per ticket.
**Estimated impact with 80/100/80 + partial:** ~$11.40 ($1.50 from 0.015@+100pts + $9.90 from remaining 0.015)

## Вывод

Отступ 50pts слишком мал для M5 GOLD — коррекция 50-80pts за минуту нормальна. 100pts даёт пространство. Старые параметры подходят для H1-трейдинга (меньше шума), но не для M5-скальпинга.
