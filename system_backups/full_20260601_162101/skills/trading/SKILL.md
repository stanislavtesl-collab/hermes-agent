---
name: trading
description: Trading tools — MT5, Twelve Data, technical analysis, and market data pipeline
---

# Hermes Trader Tools

## 🚀 V4.2 Multi-TF Scalper (M1+H1) — текущий чемпион

**Стратегия V4.2** — лучшая скальпинг-стратегия на данный момент (+$357/нед, 70.5% WR, DD $42).

### Архитектура — 2 процесса

```
Monitor v4.2 — каждые 8с → .gold_trade_signal.json ← Executor v4.2 (cmd-окно) — каждые 3с → MT5
```

**Monitor v4.2 (`_gold_monitor_v42.py`):**
- H1-фильтр: EMA50 с ATR×0.2 band → UP/DOWN/SIDEWAYS
- M1-вход: пробой M1 EMA20 (сверху вниз при DOWN, снизу вверх при UP)
- При SIDEWAYS — вход заблокирован
- heartbeat в `.monitor_v42_heartbeat.json`
- Пишет сигнал в `.gold_trade_signal.json`

**Executor v4.2 (`_gold_executor_v42.py`):**
- Читает сигнал каждые 3с
- SL: 15-bar high/low + 5pts
- Трейлинг: offset=30pts, step=10pts
- Partial close: 30% при +15pts
- Anti-contradict: проверка H1 тренда

### 📦 Статус стратегий (июнь 2026)
- **V4.2 Multi-TF Scalper** — ✅ **АКТИВНА**. Чемпион, торгуем сейчас.
- **V3.2 Trend-Following (H1)** — доступна, не запущена. 180d validation.
- **V1 EMA Reverts (M5)** — ❌ **АРХИВ**. Отключена по просьбе пользователя. Причина: DD $1,761 при счёте $1,550 — риск слить депозит. Лучше V4.2 по всем метрикам.

### ⚡ Windows-специфичный запуск (критически важно)

**Не использовать manager-wrapper (`_v42_manager.py` или subprocess.Popen).** subprocess.Popen с CREATENOWINDOW не работает для MT5-зависимых скриптов — init зависает.

**Git-Bash subprocess не может инициализировать MT5.** `mt5.initialize()` зависает из Popen или terminal(background=true), даже если MT5 работает.

**Единственный рабочий способ — cmd-окно через bat-файл:**

`run_executor_v42.bat` вызывает `_boot_executor_v42.py`, который делает MT5 init, проверяет соединение, потом запускает executor.

Пользователь кликает bat → открывается cmd-окно → executor живёт в нём. **Окно нельзя закрывать.**

### Когда будет сигнал (важно для пользователя)
- H1 должен быть UP или DOWN (не SIDEWAYS)
- При DOWN: цена пробивает M1 EMA20 вниз → SELL
- При UP: цена пробивает M1 EMA20 вверх → BUY
- **Всегда отвечать конкретными ценами**, когда пользователь спрашивает "в ценах именно"

### Параметры V4.2
```json
{
  "timeframe_entry": "M1",
  "timeframe_trend": "H1",
  "lot": 0.03,
  "trailing_offset_pts": 30,
  "trailing_step_pts": 10,
  "partial_close_pts": 15,
  "partial_close_fraction": 0.3,
  "no_rsi_filter": true,
  "no_atr_filter": true
}
```

### Урок: GEP (Gap) на открытии недели
1 июня 2026 GOLD открылось с микро-GEP ~$16 вниз. Пользователь ранее предположил, что GEP будет маленький — подтвердилось. Вывод: если пользователь даёт прогноз по GEP — доверять его оценке, микро-GEP не создаёт сильного импульса.

## Skill Orchestration (Hotfix)
Always apply `trading-orchestrator` routing first:
1. Decide intent: execution vs analysis vs self-learning vs cleanup.
2. Use exactly one primary route per turn; avoid parallel daemon control actions.
3. For daemon lifecycle, obey heartbeat-first rule and never mass-kill by name.


## 🚨 CRITICAL: Trading session focus discipline (Updated 1 June 2026)

**Базовый режим (по умолчанию):** торговля — единственная задача. Проверить → доложить → войти если сигнал.

**Режим параллельных исследований (с разрешения пользователя):** пользователь может сказать "делай всё сразу — торгуй и параллельно исследуй". В этом режиме:

- ✅ Живая торговля в приоритете — executor/monitor'ы работают
- ✅ Фоновые исследования (бэктесты, анализ, ML-модели) — через delegate_task или Codex/Qwen
- ✅ Self-check каждые 10-20 минут — не завис ли, жива ли система
- ❌ Не спамить в чат промежуточными результатами — только финальный отчёт
- ✅ Аварии (executor упал, ошибка в логе) — чинить немедленно, исследования на паузу

**Когда разрешено:** только когда пользователь явно сказал "делай параллельно", "я даю тебе волю на полное изучение", "торгуй дальше и параллельно думай над другими стратегиями".

**Когда НЕ разрешено:** пользователь просто сказал "торгуй" или "мониторь" без уточнения — тогда только рынок, никаких фоновых задач (ни delegate_task, ни Codex, ни Qwen).

**Правило «Один поток»**: если рынок открыт и мы в игре — я не отвлекаюсь ни на что другое, ПОКА пользователь явно не разрешил фоновые исследования. Не ждать напоминания — это жёсткое правило.
