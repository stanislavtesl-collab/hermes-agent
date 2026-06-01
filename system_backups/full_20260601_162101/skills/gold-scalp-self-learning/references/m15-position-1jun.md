# M15 Position Swing — 1 June 2026 Deployment

## Что создано
- `_gold_monitor_m15.py` — монитор M15 (H4→H1→M15, трендовый фильтр, RSI, swing уровни)
- `_gold_executor_universal.py` v3 — dual-mode (scalp magic=123462 + position magic=123463)
- `strategy_library/_m15_position_swing.md` — полное описание стратегии

## Сигнальный файл
`.gold_trade_signal_m15.json` — пишется монитором, читается executor'ом

## Параметры
- SL: из сигнала (M15 swing low/high + 10pts буфер)
- TP: 250pts (передаётся в order_send)
- Partial close: НЕТ (в отличие от скальпинга)
- Трейлинг: offset=30pts (брокерский минимум), активируется при +100pts
- Лот: 0.03 (начальный)
- Magic: 123463

## Структура сигнала
```json
{
  "action": "BUY",
  "symbol": "GOLD",
  "price": 4450.00,
  "lot": 0.03,
  "sl": 4435.00,
  "tp": 4475.00,
  "sl_pts": 150,
  "tp_pts": 250,
  "trailing_offset": 30,
  "trailing_step": 10,
  "partial_close_pts": null,
  "partial_close_fraction": null,
  "reason": "H4=BULLISH H1=SIDEWAYS RSI=28 M15 разворот от 4435.00",
  "trend_h4": "BULLISH",
  "trend_h1": "SIDEWAYS",
  "swing_low_m15": 4435.00,
  "swing_high_m15": 4460.00,
  "rsi_m15": 28.3,
  "atr_m15": 8.5
}
```

## Фильтры входа (M15 монитор)
1. H4 BULLISH → только BUY (SELL заблокирован)
2. H4 BEARISH → только SELL (BUY заблокирован)
3. M15: разворот от поддержки/сопротивления + RSI экстремум (<35 для BUY, >65 для SELL)

## Важно
- Не открывает вторую позицию пока первая M15 активна
- Монитор проверяет magic=123463 среди открытых позиций
- Скальпинг V4.2/V5.0 продолжает работать независимо
