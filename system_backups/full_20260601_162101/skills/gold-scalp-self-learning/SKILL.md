---
name: gold-scalp-self-learning
description: >-
  Self-learning GOLD scalper on M5/M1 with 4 strategies: V1 EMA-revert (range only), V2 Breakout, V3 VWAP-micro,
    plus V5 martingale recovery, and **V4 H1 Trend-Following (V3.2)** — the only strategy proven profitable on ANY market.
    V4 validated: +$445/180d, 52.8% WR, PF=1.09, DD=$584, 324 trades. Key: H1 EMA50 trend filter, SL capped at H1 ATR×1.5,
    TP=H1 ATR×1.5, NO partial close. V1 confirmed on range only (failed 7-variant week test: ALL configs negative).
    Alligator-gate (hard/off configurable), trailing 50/60/50, partial close 30%@150pts (V1 only).
    Updated 1 June 2026: executor v3 dual-mode (scalp magic=123462 + position magic=123463),
    M15 Position Swing (H4/H1/M15, NO partial close, TP=250pts, trailing from 30pts),
    SL-at-open fixed for all trades, H1 trend filter blocking trades against trend,
    FxPro 30pt minimum trailing confirmed.
tags: [scalping, gold, mt5, vwap, trailing, fibonacci, sre, v42, deployment, position-trading, m15-swing, ten-trade-autopsy]
related_skills: [strategy-backtest-optimization, windows-monitor-deployment, ten-trade-autopsy]
---

# GOLD Scalp — Self-Learning & Trade Analysis

## 📡 DATA SOURCE: MT5 ONLY — Never Twelve Data for monitors (Updated 1 June 2026)

**ALL monitors MUST use MT5 data directly.** Twelve Data causes:
- 3-5s delay on M1 bars → signals arrive late or are missed entirely
- HTTP 429 rate limits (8 req/min) → crashes
- Data inconsistency with MT5 terminal (different close prices)

**V4.2 and V5.0 monitors were migrated on 1 June 2026.** The old Twelve Data approach caused 3 missed signals in 10 minutes.

**Monitor switching Twelve Data→MT5: Both monitors STILL hang as background subprocess from Git-Bash** — confirmed 1 June 2026 even after MT5 migration. Workaround: V4.2 monitor runs via nohup, V5.0 monitor via nohup. But any MT5-dependent script launched via `terminal(background=true)` from Git-Bash hangs on `mt5.initialize()`.

**Architecture change (proved 1 June 2026):**
```
# WRONG — Twelve Data → delay + 429
raw = fetch_bars("1min", 100)  # HTTP API, 3-5s delay

# RIGHT — MT5 direct → real-time, no delay
import MetaTrader5 as mt5
rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M1, 0, 60)
```

**What this means for the monitor:**
1. Monitor process needs `mt5.initialize()` at startup (like executor)
2. Monitor runs in singe‑process mode (no separate MT5 connection per cycle)
3. Monitor no longer needs Twelve Data API key
4. Monitor runs via `terminal(background=true)` — this works **because the monitor is also MT5‑connected**. Bug confirmed: even V4.2/V5.0 monitors with MT5 init hang in background. **Workaround:** launch monitors before executors, users double‑click executor .bat files only.

**Rate-limit info (for reference, obsolete for monitors):**
- Free Twelve Data: 8 req/min
- V4.2 before migration: 2 calls/8s = 15 req/min → 429 every ~30s
- V5.0 before migration: 1 call/20s = 3 req/min → safe (but still delayed data)
- **Now: zero Twelve Data calls** — monitors use MT5 directly

**Import checklist for MT5‑based monitors (Python 3.12):**
```python
import sys
sys.path.insert(0, "/c/Program Files/Python312/Lib/site-packages")
import MetaTrader5 as mt5

MT5_PATH = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
if not mt5.initialize(path=MT5_PATH, timeout=15000):
    sys.exit("MT5 init failed")
mt5.symbol_select("GOLD", True)
```

**Monitor lifecycle:** The monitor initializes MT5 ONCE at startup, then reads `copy_rates_from_pos()` in a loop. No re‑init per cycle. Only `mt5.shutdown()` if the process is cleanly exiting.

## 🚀 UNIVERSAL EXECUTOR — V4.2 + V5.0 One Process (Added 1 June 2026)

**CRITICAL FIX:** Separate executors (one per strategy) fail because each calls `mt5.initialize()` — the second instance can't connect while the first holds the shared memory. Solution: **one process, one `mt5.initialize()`, both signal files checked every 2s.**

**Architecture (`_gold_universal_executor.py`):**
```python
mt5.initialize(path=MT5_PATH)  # ONE init at startup

while True:
    for signal_file, magic in [(".gold_trade_signal.json", 12345),
                               (".gold_trade_signal_v50.json", 123460)]:
        signal = read_signal(signal_file)
        if signal and not has_open_trade(magic=magic):
            open_trade(signal)
            clear_signal(signal_file)
    manage_trailing()  # per-trade config from signal
    time.sleep(2)
```

**Key benefits:**
1. Single MT5 init — no conflict, no "already initialized" errors
2. 2s loop — catches signals faster than separate 3s executors
3. Magic per source — V4.2=12345, V5.0=123460, each checked independently
4. Trailing config from signal — each strategy sets its own offset/step/partial

**Deployment:** User double-clicks `run_universal_executor.bat` after killing old executors.
**Verification:** `cat .gold_executor_universal_heartbeat.json`

**Reference:** `references/universal-executor-1jun.md` (numpy-array safety fix 1 June 2026)

## 🧮 NUMPY-SAFETY — CRITICAL EXECUTOR PATCH (1 June 2026)

**Проблема:** `mt5.positions_get()` возвращает поля (`sl`, `price_current`, `volume`, `tp`) как **numpy массивы** вместо float, когда терминал busy. `float(numpy_array)` падает с:
```
ValueError: The truth value of an array with more than one element is ambiguous.
```

**Этот баг крашит executor в бесконечный цикл ошибок:** каждые 2с — ошибка, сигналы потребляются/очищаются, сделки не открываются. PID висит живой в tasklist, но ничего не делает.

**Недостаточно:** `float(pos.sl) if pos.sl is not None else None` — numpy.array не None.

**Нужно: safe_val() везде где читается pos.field:**
```python
def safe_val(val):
    if val is None:
        return None
    try:
        v = float(val)
        return None if v > 1e10 or v < -1e10 else v
    except (TypeError, ValueError):
        return None
```

**Места применения (ВСЕ функции, где читается pos.*):**
1. `manage_trail()` — `pos.price_current`, `pos.sl`, `pos.ticket`
2. `try_average()` — `pos.price_current`, `pos.volume`, `pos.ticket`
3. `close_position()` — если есть
4. Любое сравнение `pos.ticket == trail["ticket"]` — ticket тоже может быть array

**СИМПТОМЫ если safe_val() не применён везде (опасный сценарий):**
- ✅ Heartbeat обновляется нормально ✅ — создаёт ложное чувство безопасности
- ❌ Сигналы потребляются и очищаются, сделки НЕ открываются ❌
- ❌ В логе `Error: The truth value of an array...` каждые 2-3с ❌
- PID висит живой в tasklist, но фактически мёртв
- **Тихая смерть — самый опасный сценарий.** Heartbeat может обновляться ещё 5-10 минут после потери функциональности, пока main loop крутится в Exception handler.

**1 June 2026 — дополнение: `manage_trail(pos)` vs `manage_trail(trail)`.** Ещё один баг: в main loop строка `manage_trail(pos)` передавала MT5 Position object вместо trail-словаря. Функция ожидает словарь с ключами `{"ticket", "action", "entry_price", ...}`. При передаче Position — падает с ошибкой при `trail["ticket"]`. **Исправлено:** теперь читает `.universal_trail.json` и сверяет тикет перед вызовом:
```python
for pos in positions:
    try:
        with open(TRAIL_FILE) as f:
            trail = json.load(f)
        if trail.get("ticket") == pos.ticket:
            manage_trail(trail)
    except:
        pass
```

**1 June 2026 — случай из практики (два эпизода):**

**Эпизод 1 (16:00):** safe_val() был применён к manage_trail(), но НЕ к try_average(). Executor падал с ошибкой когда появлялся кандидат на усреднение, при этом heartbeat обновлялся ещё 3 минуты. Потребовалось убить все PID и перезапустить с нуля.

**Эпизод 2 (16:05-16:16):** После полного применения safe_val() и перезапуска — executor **продолжал падать** с той же ошибкой. Причина: executor был перезапущен поверх старого лога, и в логе оставались старые ошибки от убитого процесса. `grep Error | tail -3` показывал старые ошибки, создавая ложное чувство, что проблема не решена. Решение: **проверять не только наличие ошибок, но и временную метку** — новые ошибки после последнего перезапуска? Или старые?

**Урок:** после каждого перезапуска executor'а — проверять timestamp ошибок (`grep "Error" .universal_executor.log | grep -E "$(date +%H:%M)"`), а не просто их наличие.

**Диагностика (каждые 10-20 мин):**
```bash
# 1. Heartbeat жив?
cat .gold_executor_universal_heartbeat.json

# 2. Есть ли ошибки в логе?
grep "Error" .universal_executor.log | tail -3

# 3. Сколько сделок открыто за последние 5 мин?
grep "✅ V" .universal_executor.log | tail -5

# 4. MT5 positions (есть ли открытые позиции?)
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(len(mt5.positions_get(symbol='GOLD') or [])); mt5.shutdown()"
```

**Готовый модуль:** `scripts/safe_val.py` (можно импортировать в executor).

**Вывод:** при любом новом коде, который читает `pos.*` поля — safe_val() обязателен с первого коммита.

## 🛡️ FIRST LAW: SL MUST BE SET AT OPEN (Updated 1 June 2026 — ИСПРАВЛЕНО В EXECUTOR V2)

**1 June 2026 — МАСШТАБНАЯ ОШИБКА: 5/5 сделок без SL при открытии.**

| Сделка | SL при открытии | Результат |
|--------|:-:|:-:|
| #237487560 V50 SELL @ $4,499.67 | 0.0 ❌ | **-$13.57** |
| #237503398 V42 SELL @ $4,504.22 | 0.0 ❌ | +$6.20 (трейлинг спас) |
| #237511476 V50 SELL @ $4,496.46 | 0.0 ❌ | **-$8.00** |
| #237521776 V50 SELL @ $4,493.63 | 0.0 ❌ | +$31.34 (крупное везение) |
| #237530728 V50 SELL @ $4,476.09 | 0.0 ❌ | **-$30.23** |

**Корневая причина:** Executor.open_trade() не ставил SL при открытии — полагался на трейлинг, который активируется только когда сделка в плюсе.

**Исправление в executor v2 (14:00 1 June 2026):**
```python
if action == "SELL":
    sl_price = round(price + SL_DISTANCE, 2)  # SL_DISTANCE = 8.00 (800pts)
else:
    sl_price = round(price - SL_DISTANCE, 2)
request = { ..., "sl": sl_price, ... }
```

**Правило (железное, без исключений):**
1. SL ставится В ТОМ ЖЕ order_send() — не после открытия отдельной SLTP операцией
2. SL_DISTANCE = $8.00 (800pts) — минимальное расстояние FxPro для GOLD
3. Если брокер не принимает SL (retcode=10016) — сделка не открывается
4. Трейлинг — дополнительная защита, а не замена SL
- **ПРОВЕРЯТЬ SL ПОСЛЕ order_send()** — 1 June 2026 executor поставил SL=50.29pts вместо 8.00 из-за numpy contamination. Читать обратно: `mt5.positions_get(ticket=N)[0].sl` и логарифмировать если SL не совпадает с ожидаемым.

**1 June 2026 — дополнение: SL от M15 сигнала защищён проверкой.** Если M15 монитор передаёт SL дальше чем 1500pts от цены — executor игнорирует его и ставит стандартный 800pts. Исправлено в `open_trade()` с проверкой `sl_diff = abs(sig_sl - price) * 100`, при `sl_diff > 1500` → автозамена.

## 🎯 Контртрендовые сделки: BUY в downtrend, SELL в uptrend (Добавлено 1 June 2026)

**Данные сессии 1 June 2026 — 33 сделки:**

| Тип сделки | Кол-во | Профит | Комментарий |
|:--|:-:|:-:|:--|
| SELL в downtrend (по тренду) | 17 | 100% в плюс | ✅ Все прибыльные |
| BUY в downtrend (контртренд) | 5 | ~0 (микропрофит) | ⚠️ Около нуля |

**Вывод:** BUY в H1 downtrend дают 0 полезного профита. Средний профит = $0.03 за сделку против $5+ за SELL.

**Actionable правило:**
- H1 BEARISH → V4.2 BUY сигналы = блокировать или SL ставить в 2x уже (400pts вместо 800pts)
- H1 BULLISH → V4.2 SELL сигналы = блокировать
- V5.0 монитор по умолчанию не даёт контртрендовых сигналов — это его преимущество

**Когда всё же можно BUY в downtrend:**
1. RSI(14) < 25 — экстремальная перепроданность
2. Цена коснулась H1 поддержки (20-bar swing low) + отскок
3. Двойное дно на H1 (цена протестировала уровень 2 раза и отскочила)

**Реализация:** H1 trend filter в executor v3 блокирует BUY при BEARISH и SELL при BULLISH. Это уже есть в коде, но может быть опционально отключено пользователем.

## 📐 H1 Trend Priority (Updated 1 June 2026 — executor v2)

**H1 trend имеет приоритет над всеми M5/M1 сигналами.** Executor v2 проверяет H1 trend ДО открытия сделки и блокирует сигналы против тренда.

**H1 trend определение:** SMA20 vs SMA50 на H1 баре (50 свечей). Если SMA20 > SMA50 = BULLISH.

**1 June 2026 — доказательство: 5 сделок SELL при H1 BULLISH. Результат: -$14 за день вместо +$30.**

**Правило (абсолютное, без исключений):**
- H1 BULLISH → ТОЛЬКО BUY
- H1 BEARISH → ТОЛЬКО SELL
- H1 SIDEWAYS → обе стороны разрешены

**Как проверять когда MT5 занят executor'ом:**
```python
import yfinance as yf
gold = yf.download("GC=F", interval="1h", period="5d", progress=False)
closes = gold["Close"].values.astype(float)
sma20 = sum(closes[-20:])/20
sma50 = sum(closes[-50:])/50
# GC=F ~ $28-30 выше GOLD спота — нормально, тренд тот же
```

## 🎚️ TREND FILTER — Optional (Updated 1 June 2026)

**Both V4.2 and V5.0 had trend filters removed on user request when the market was in SIDEWAYS.**

Before:
- V4.2: H1 EMA50 trend filter — only trade WITH trend
- V5.0: M15 EMA50 trend filter — only trade WITH trend

After user request:
- V4.2: ANY M1 EMA20 breakout
- V5.0: ANY M5 swing high/low breakout

**When to use / not use trend filter:**

| Condition | With filter | Without filter |
|-----------|-------------|----------------|
| Clear H1 trend | ✅ Fewer, better entries | Mixed quality |
| SIDEWAYS / choppy | ⏸️ No trades at all | ✅ Catches micro-moves |
| User wants action | ❌ Nothing happens | ✅ More signals |

**Rule:** Default = trend filter ON. Remove only on user request or market SIDEWAYS >2h.

## 🔴 FxPro Platform Constraints (Updated 1 June 2026)

**1. Minimum stop distance = 30pts (confirmed 1 June 2026)**
- Попытка поставить SL на 8pts выше входа → retcode=10016 Invalid stops
- 30pts (= $3.00) → OK
- Трейлинг offset=30 — не настройка а ТРЕБОВАНИЕ БРОКЕРА
- executor v2 использует SL_DISTANCE=800pts = $8.00 (запас)

**2. `order_send()` с `sl=0` или `tp=0` → ошибка (-2, 'Invalid "sl" argument')**
- Не передавать sl/tp ключи когда не нужны. Не передавать 0.

**3. MT5 shared memory — только один процесс инициализируется нормально**
- Второй экземпляр hang'ит на mt5.initialize()
- Решение: один executor на все стратегии

**4. Git-Bash subprocess environment ломает mt5.initialize()**
- `terminal(background=true)` для MT5-скриптов НЕ РАБОТАЕТ
- `terminal(foreground)` с `python -c` — работает
- bat-файлы (пользователь кликает) — ЕДИНСТВЕННЫЙ надёжный способ для долгих процессов

## 🐕 Watchdog — Executor Auto-Restart (Added 1 June 2026)

**Проблема:** Executor упал дважды за день 1 June 2026:
1. После partial close #237521776 — завис, трейлинг не обновлялся
2. Пришлось убивать PID 8132 и перезапускать вручную

**Решение:** `watchdog.sh` в рабочей папке:
- Проверяет heartbeat каждые 15с
- Если heartbeat не обновлялся >15с — убивает зависший процесс
- Запускает новый executor
- Пишет лог в `.watchdog.log`

**Запуск:** через `terminal(background=true)` — watchdog не использует MT5, поэтому работает.

**Важно:** watchdog не запущен на этой сессии. Запустить при следующем развёртывании.

## 📊 GOLD H1 Analysis — Quick Methodology (Added 1 June 2026)

When user asks for GOLD H1 analysis, always compute:

| Metric | Source | Interpretation |
|--------|--------|---------------|
| SMA20 vs SMA50 | H1 closes | BULLISH/BEARISH/SIDEWAYS |
| RSI(14) | H1 closes | <30 oversold, >70 overbought |
| ATR(14) | H1 H/L/C | Volatility measure |
| MACD vs Signal | H1 closes | Momentum direction |
| Last 3-5 candles | H1 OHLC | Pattern |
| 20-bar swing H/L | H1 highs/lows | Support/Resistance |

**Data source priority:** MT5 direct > yfinance GC=F (fallback)

**⚠️ GC=F vs GOLD spread:** GC=F consistently trades **$28-30 above** GOLD spot. Formula: `GOLD_spot ≈ GC=F_close - 29`.

**H1 analysis template (concise — user wants numbers, not prose):**
```
📊 H1 | Price $4536 | SMA20 $4556 > SMA50 $4538 | RSI 29.2 | ATR $14.73
Trend: BULLISH (price below MAs = pullback)
MACD -4.64 (below signal)
Support $4518 | Resistance $4604
```

## 📍 Эволюция торговли: скальпинг 0.03 → позиционка 0.5 лота (Added 1 June 2026)

**Концепция обсуждалась 1 June 2026:** Переход от M5 скальпинга (0.03 лота, 15-30pts) к **M15 позиционной торговле** (200-300pts цель, постепенный рост до 0.5 лота).

### Executor v3 — Dual-mode (Создан 1 June 2026)

Executor v3 поддерживает **два типа сделок параллельно:**

| Тип | Magic | Файл сигнала | Partial close | Трейлинг | TP |
|:--|:-:|:--|:-:|:-:|:-:|
| **Скальпинг** (V4.2/V5.0) | 123462 | `.gold_trade_signal.json`, `.gold_trade_signal_v50.json` | ✅ 30%@+15pts | от 30pts | Нет |
| **Позиционка** (M15) | 123463 | `.gold_trade_signal_m15.json` | ❌ НЕТ | от 30pts | ✅ 250pts |

**Ключевые особенности позиционки:**
- НЕТ partial close — стратегия требует полного выхода (200-300pts одним куском)
- SL из сигнала (M15 swing low/high), а не фиксированный 800pts
- TP = 250pts, передаётся прямо в `order_send()` как параметр
- Трейлинг работает как доп. защита после +100pts
- Обе системы не мешают друг другу — разный magic, разные сигнальные файлы

**Проверка позиции в executor:** вместо `has_position = len(positions) > 0` — теперь раздельный:
```python
scalp_positions = [p for p in positions if p.magic == MAGIC_SCALP]
m15_positions = [p for p in positions if p.magic == MAGIC_M15]
```

**M15 монитор** (`_gold_monitor_m15.py`): смотрит H4→H1→M15, блокирует сделку если нет подтверждения тренда.

### M15 Position — стратегия (создана 1 June 2026)

Файл: `strategy_library/_m15_position_swing.md`

**Три ТФ для входа:**
1. H4 — глобальный тренд (SMA20 > SMA50 = BULLISH, иначе BEARISH)
2. H1 — среднее подтверждение
3. M15 — точка входа (разворот от поддержки/сопротивления + RSI экстремум)

**Возвращает в приоритет SELL при H4 BEARISH.** Все 5 сделок 1 June 2026 были SELL при H4 BULLISH — ошибка, учтена в новых фильтрах.

**Стратегия шагового роста лота от 0.03 до 0.5:**

| Этап | Лот | Цель | Условие перехода |
|:--|:--:|:--:|:--|
| Сейчас | 0.03 | Отработка | Текущий |
| Шаг 1 | 0.10 | $100+ | 5+ прибыльных сделок 0.03 |
| Шаг 2 | 0.30 | $150+ | Баланс >$2,000 |
| Цель | 0.50 | 200-300pts = $100-150 | Баланс >$3,000 |

### Путь роста лота

| Этап | Лот | Цель | Риск (2% = $31) | Условие перехода |
|:--|:--:|:--:|:--:|:--|
| Сейчас | 0.03 | Отработка системы | $0.9-3 | Текущий |
| Шаг 1 | 0.10 | $100+ счета | $8-15 | 5+ прибыльных сделок 0.03 |
| Шаг 2 | 0.30 | $150+ | $15-24 | Баланс >$2,000 |
| Цель | 0.50 | 200-300pts = $100-150 | $25-30 | Баланс >$3,000 |

### М15 позиционная стратегия (реализована 1 June 2026)

**НЕТ частичного закрытия.** Пользователь явно указал: "не будем закрывать частично профит, а просто ловить 200-300 пунктов движения". Полный выход по TP (250pts) или трейлингу.

**Трендовая структура:**
- H4: определяет глобальное направление
- H1: точка входа
- M15: точный вход

**Условия входа:**
1. H4/H1 тренд совпадают (оба BULLISH или оба BEARISH)
2. M15: откат к EMA20 или зона перепроданности/перекупленности
3. SL = M15 swing low/high или ATR×1.5
4. TP = 250pts (жёсткий TP в order_send)
5. Partial close: ОТСУТСТВУЕТ. Полный выход одним ордером.

**Соотношение риск/прибыль при росте лота:**

| Лот | SL pts | Риск $ | R:R (200pts) |
|:--:|:--:|:--:|:--:|
| 0.03 | 100 | $3 | 1:2 |
| 0.10 | 80 | $8 | 1:2.5 |
| 0.30 | 50 | $15 | 1:4 |
| 0.50 | 30 | $15 | 1:6.7 |

**Реализовано 1 June 2026:** M15 монитор (PID 7724), executor v3. Торгуется live параллельно скальпингу.

### 📊 Усреднение (Averaging) — добавлено 1 June 2026

**Правило:** максимум 1 усреднение на сделку. Добавляем лот того же объёма, когда:
1. Сделка в минусе **> 30pts**
2. H1 тренд **подтверждает** направление (BUY при BULLISH/SIDEWAYS, SELL при BEARISH/SIDEWAYS)
3. Цена на **круглом уровне** ($X.X0, $X.X5)
4. Усреднение ещё не делали (`trail["averaged"]` не установлен)

**Механика в executor v3:**
```python
try_average(pos, positions_list, magic, h1_trend)
  # если не averaged, loss>20pts, цена на сильном уровне, тренд подтверждает
  # → открывает второй лот того же объёма
  # → пересчитывает среднюю цену
  # → ставит SL на ОБЕ позиции от средней
```

**Правило:** максимум 1 усреднение на сделку. Добавляем лот того же объёма.

**ВАЖНО: НЕ усреднять сразу при 20pts — ждать самую выгодную точку.** Executor проверяет каждый цикл (2с), но усредняет ТОЛЬКО когда цена касается **сильного уровня**:

1. Сделка в минусе > 20pts (выход из зоны шума)
2. H1 тренд подтверждает направление (BUY при BULLISH/SIDEWAYS, SELL при BEARISH/SIDEWAYS)
3. Цена на ОДНОМ из сильных уровней:
   - Круглый уровень ($X.X0, $X.X5, $X.50) — приоритет
   - H1 swing low/high — предыдущее касание поддержки/сопротивления
   - M15 swing low/high — предыдущий разворот
4. Усреднение ещё не делали (trail["averaged"] не установлен)

**Логика:** executor НЕ усредняет на каждом цикле где loss>20pts — он ждёт пока цена дойдёт до одного из сильных уровней. Если цена пробила все уровни — SL сработает без усреднения.

**Пример:**
```
BUY 0.03 @ $4,470 → цена упала до $4,458 (убыток -$12)
H4 BULLISH, H1 откат → усреднение
BUY 0.03 @ $4,458 (второй вход)
Средняя: ($4,470 + $4,458) / 2 = $4,464
SL на обе: от средней +800pts = $4,456
Цена развернулась до $4,474 → профит 0.06 × ($4,474 - $4,464) = +$6.00
(Без усреднения: -$12)
```

**Когда НЕ усреднять:**
- H4/H1 тренд развернулся против направления — ждём SL
- Усреднение уже сделано (1 раз максимум)
- Риск > 2% баланса с учётом двух лотов

## 📊 Profit Calculation Reference (Added 1 June 2026)

| Лот | 100pts | 200pts | 300pts |
|:--:|:--:|:--:|:--:|
| 0.03 | $3 | $6 | $9 |
| 0.10 | $10 | $20 | $30 |
| 0.30 | $30 | $60 | $90 |
| 0.50 | $50 | $100 | $150 |
| 1.00 | $100 | $200 | $300 |

Risk (2% of $1,550 = $31) допустимый для:
- 0.03 лота: SL до 1000pts ($30)
- 0.10 лота: SL до 300pts ($30)
- 0.30 лота: SL до 100pts ($30)
- 0.50 лота: SL до 60pts ($30)

## Troubleshooting: MT5 copy_rates не работает из subprocess

**Проблема (1 June 2026):** Когда executor v2 держит MT5, второй экземпляр не может вызвать `copy_rates_from_pos()` — возвращает None или пустой массив. `symbol_info_tick()` работает, но OHLCV данные не доступны.

**Причина:** MT5 shared memory — только один процесс может читать историю котировок.

**Решения:**
1. Использовать `symbol_info_tick()` для текущей цены — всегда работает
2. Для H1/M15 контекста — yfinance GC=F как fallback
3. Для мониторов — свой экземпляр MT5 (свой терминал или отдельное подключение)

**yfinance как fallback для анализа:**
```python
import yfinance as yf, pandas as pd
gold = yf.download("GC=F", interval="1h", period="5d", progress=False)
if isinstance(gold.columns, pd.MultiIndex):
    gold.columns = [c[0] for c in gold.columns]
closes = gold["Close"].values.astype(float)
# GC=F ~ $29 выше GOLD спота
```

## Трейлинг: только когда сделка в прибыли (исправление 1 June 2026)

**Было:** executor подтягивал SL от current_price всегда, даже когда сделка была в убытке. Это давало SL на уровне entry ± 8pts при цене далеко — бесполезно, не защищало.

**Стало:** трейлинг подтягивает SL ТОЛЬКО когда profit_pts >= offset (30pts для SELL/BUY). Пока сделка в убытке или микропрофите — SL не трогаем.

```python
# SELL
if profit_pts >= off:  # off = 30
    new_sl = round(current + off * 0.01, 2)
    if new_sl < entry:
        if pos.sl is None or pos.sl > new_sl + step * 0.01:
            mt5.order_send(... modify SL)
```

## 👁️ Слепые зоны: потеря сделок и висение позиций (Добавлено 1 June 2026 — урок)

**Проблема (1 June 2026, 16:05):** Пользователь сообщил что сделка #237687234 SELL @ $4,458.26 висит с убытком. Я проверил `positions_get(symbol='GOLD')` — вернул None (пусто). **HО сделка была жива** — `positions_get(ticket=237687234)` работала. Причина: MT5 shared memory была занята executor'ом, и batch-запрос `positions_get(symbol='GOLD')` вернул None, а ticket-specific запрос прошёл.

**Корневая причина:** проверка только `len(positions_get(symbol='GOLD'))` — ненадёжна. MT5 может вернуть None для batch-запроса даже при живых позициях.

**Исправление в диагностике:** всегда проверять через оба метода:
```python
# НЕДОСТАТОЧНО:
pos = mt5.positions_get(symbol='GOLD')  # может вернуть None даже при живых позициях

# ДОСТАТОЧНО:
pos = mt5.positions_get(symbol='GOLD')
if pos is None:  # shared memory занята — альтернативная проверка
    # попробовать через account_info или ticket-specific
    acc = mt5.account_info()
    print(f'Баланс: ${acc.balance:.2f}')  # если меняется — сделки есть
    # ИЛИ: пробовать инициализировать второй раз
```

**Практический чек-лист для диагностики "жива ли сделка?":**
1. `positions_get(symbol='GOLD')` — если None, не значит что сделок нет
2. `positions_get()` без фильтра — может показать позиции по другим символам
3. `account_info().balance` — если баланс меняется, сделки есть/были
4. `history_deals_get()` — история за сегодня, отфильтровать GOLD
5. Лог executor'а — `grep "✅ V" .universal_executor.log | tail -5` — последние открытия
6. Если ничего не помогло — **переинициализировать MT5** или проверить второй терминал

**Когда позиция "исчезает" из поля зрения executor'а (выводы):**
- Executor открывает сделку → записывает в trail_file
- Executor падает/перезапускается → trail_file жив, executor не знает про позицию
- Позиция висит без управления → убыток растёт
- При перезапуске executor читает trail_file → не может найти позицию → игнорирует

**Решение для executor'а (TO-DO):** При старте executor должен сканировать `positions_get()` и сверять с trail_file. Если есть позиция без трейла — взять её под управление.

**Урок:** `positions_get()` с фильтром symbol может вернуть None когда shared memory занята — это НЕ означает "нет позиций". Всегда проверять несколькими методами.

**Reference:** `references/lost-position-1jun.md` (full timeline and root cause analysis).

При создании файлов >300 строк: первый `write_file` = чистый заголовок. Каждый последующий `patch()` добавляет блок. `old_string` = уникальная строка.

## ⏹ Session End Protocol

When user says "закончили":
1. Kill ALL python + terminal64.exe processes
2. Clean state files (.gold_daemon.*, .gold_state.*, .gold_*.json)
3. Clean temp training artifacts
4. Confirm nothing alive
5. Report final summary

## 🚫 Banned Phrases

Never say: "too late", "missed", "didn't notice", "overlooked".
Never say a feature works without verifying code + process + log.

## 🔴 FACT-CHECK BEFORE REPORTING

1. Read the actual code file
2. Verify process alive via PowerShell, NOT ps aux
3. Check the log for the feature's log line
4. Check all three processes (monitor + executor + watchdog)
5. If in SKILL.md but NOT in code → say "designed, not implemented"

## 🧠 Параллельные исследования (Background Research Mode)

**Установлено 1 June 2026 — поведение пользователя:** исследования в фоне, отчёт только по готовности.
**Подтверждено 15:51 1 June 2026:** пользователь явно указал раз в 10-20 минут проверять что не завис.

**Self-check каждые 10-20 минут — ЖЁСТКОЕ ПРАВИЛО (код для копирования в терминал):**
```
cat .gold_executor_universal_heartbeat.json
cat .monitor_v42_heartbeat.json
cat .monitor_v50_heartbeat.json
cat .monitor_m15_heartbeat.json
grep Error .universal_executor.log | tail -3
grep '✅ V' .universal_executor.log | tail -3
```

**Формальная проверка каждого чекпоинта:**
1. Heartbeat executor'a обновляется (проверить last_check - текущее время < 15с)
2. Heartbeat всех мониторов обновляются (V4.2, V5.0, M15)
3. Ошибок в логе = 0 или только старые (до последнего перезапуска)
4. Сделки открываются (проверить count за последние 5 мин vs last_check)
5. Баланс не просел более чем на 30% от текущего пика

**Если любой чек FAIL:**
- Остановить исследование немедленно
- Починить executor/monitor
- Перезапустить
- Только потом вернуться к исследованию

**Правила параллельной работы:**
1. **Не спамить в чат** — промежуточные результаты, ход мысли, статус выполнения НЕ писать. Только финальный отчёт.
2. **Self-check каждые 10-20 мин** — проверять что не завис, что executor/monitor'ы живы, что нет упавших процессов.
3. **Приоритет: живая торговля > исследования** — если executor упал или монитор умер, сначала починить, потом вернуться к исследованиям.
4. **Использовать delegate_task** для исследования — основной поток свободен для онлайн-мониторинга.
5. **Финальный отчёт** — одним сообщением: метрики, вывод, рекомендация по внедрению или отказу.

**Запуск исследования:**
```python
# delegate_task — рекомендуется (не блокирует основной поток)
delegate_task(
    goal="Запустить бэктест стратегии X на 180 днях",
    context="...пути к данным, параметры...",
    toolsets=["terminal", "file", "web"]
)
```

## 📈 Цикл самообучения

Модуль `hermes_self_learning.py` в рабочей папке. Запускается в изолированном режиме.

**Запуск:**
```bash
python hermes_self_learning.py --days 30 --population 50 --generations 2
python hermes_self_learning.py --days 180 --discover
```

**Выходные файлы:** `.hermes_optimal_params.json`, `.hermes_learning_report.md`

## 🎯 Трейлинг — смягчённый (Установлено 1 June 2026)

**Текущие параметры (смягчённый в 2 раза, подтверждён 1 June 2026):**
- Активация: при прибыли ≥ 60pts
- Offset (дистанция SL от цены): 60pts
- Step (шаг подтягивания): 20pts

**История изменений:**
1. Было: 30/30/10 (стандартный)
2. Пользователь попросил смягчить в 2 раза → 60/60/20
3. Результат: сделки дышат дольше, меньше преждевременных выходов

**Когда какой использовать:**
- Стандартный (30/30/10): для позиционки M15 (200-300pts цель) — даёт пространство для дыхания
- Смягчённый (60/60/20): для скальпинга — текущий, смягчает влияние шума
- Агрессивный (15/20/5): только по явному запросу пользователя

**Принцип:**
```python
# Смягчённый: трейлинг стартует позже (60pts), SL дальше (60pts)
if profit_pts >= 60:  # активация
    new_sl = round(current - 60 * 0.01, 2)  # offset 60pts
    if new_sl > entry:
        if safe_val(pos.sl) is None or safe_val(pos.sl) < new_sl - 20 * 0.01:  # step 20pts
            modify_sl(new_sl)
```

**Влияние на результат (расчёт для GOLD 0.03 лота):**
- Стандартный (30/30/10): при развороте отдаём 30pts = $0.90
- Смягчённый (60/60/20): при развороте отдаём 60pts = $1.80
- **Плюс:** меньше преждевременных выходов, больше сделок добирают до 200-300pts
- **Минус:** при резком развороте теряем $0.90 дополнительно

Archive at `C:\Users\Administrator\Desktop\FxPro\strategy_library\`.
Active strategies: V4.2 (M1 scalper), V5.0 (M5 breakout).
Archived: V1 (EMA-revert).

---
