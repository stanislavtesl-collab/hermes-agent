---
name: ten-trade-autopsy
description: After every 10 closed trades (any sign, any volume) — automatic self-analysis with improvement recommendations. Runs in background, result in chat compact.
---

# Ten-Trade Autopsy

**Trigger:** every 10 closed GOLD trades (any direction, any volume).

## Procedure

1. **Collect data for last 10 trades:**
   - From `.universal_executor.log` — grep all `✅ V42`, `✅ V50`, `💰 PARTIAL`, `🎯 TRAIL`
   - From MT5 via `history_deals_get()` — exact PnL, entry/exit price, time
   - Symbol: GOLD

2. **Analysis (3 axes):**

   **A. Entry quality**
   - How many trades went immediately profitable (before first trailing)?
   - How many went negative first (20+pts)?
   - Which strategy (V42 vs V50) gives better entries?
   - Any time-of-day pattern relative to H1 trend?

   **B. Exit quality**
   - Average profit per closed trade (in pts)
   - Average loss per SL (in pts)
   - How many partial closes helped vs hurt?
   - Trailing: how many times did it exit too early?

   **C. Averaging**
   - Any trades where price went against us >20pts?
   - If yes — did it touch a strong level (round $X.00, H1 swing, M15 swing)?
   - Would averaging have worked? (simulate: add 0.03 at the level, recalc PnL)

3. **Conclusion (max 3 points):**
   - What works well (+)
   - What can be improved (↑)
   - 1 specific recommendation for next 10 trades

## Output format

```
📊 AUTOPSY #X (trades Y-Z)

✅ Good: [1 sentence]
↑ Improve: [1 sentence]
🎯 Tip: [1 specific action]

Net: +$X.XX over 10 trades
```

## Related skill
- **gold-scalp-self-learning** — umbrella skill for GOLD scalping. Trade data and context live there.
- **Reference:** `references/first-autopsy-1jun.md` — first real-world run, 33 trades, analysis template validated.

## Real-world notes (1 June 2026 — first autopsy completed)
- MT5 `history_deals_get()` часто возвращает None (shared memory занята executor'ом). **Fallback:** парсить `.universal_executor.log` — grep `✅ V42`, `✅ V50` для подсчёта сделок, `💰 PARTIAL.*\\(+(\\d+)pts\\)` для профита partial close, `TRAIL` для трейлингов.
- SELL сделки при H1 downtrend **не требуют усреднения** — цена идёт по тренду, сделки выходят в плюс. Усреднение нужно только для контртрендовых входов (BUY в downtrend).
- 33+ сделок за день все прибыльные (SELL по тренду). Аутопсия должна фокусироваться на **качестве входа/выхода**, а не только на PnL.
- После аутопсии сохранять новые уроки в gold-scalp-self-learning.
- **Важно:** счётчик сделок `.ten_trade_counter.json` должен считать ТОЛЬКО сделки с ✅ V42 / ✅ V50 из лога executor'а. Не учитывать PARTIAL или закрытия — только открытия.
- **Второй аудит (ещё не сделан):** после сделки #237689842 (последняя перед падением executor'а) закрыта вручную. Счётчик не обновлён — нужно вручную инкрементировать.

## Rules
- Keep it short — no wall of text
- If user doesn't reply — don't repeat
- Run in background, don't block trading
- Counter file: `.ten_trade_counter.json` (auto-created on first autopsy, format: `{"trades_since_last_autopsy": 10, "autopsy_number": 1}`)

## Pitfalls
- **MT5 history_deals_get() может вернуть None** когда executor занят shared memory. В этом случае — парсить `.universal_executor.log`.
- **Не делать аудит если в системе 0 сделок** — подождать накопления данных.
- **Приоритет торговли:** если во время аудита пришёл сигнал — прервать аудит, открыть сделку, потом вернуться к анализу.
