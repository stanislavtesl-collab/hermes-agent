# Background Research Mode — 1 June 2026

**Установлено:** пользователь разрешил параллельные исследования (бэктесты, новые стратегии, ML) во время живой торговли.

**Условие активации:** пользователь сказал "делай параллельно", "изучай", "думай над стратегиями" + "торгуй дальше".

## Когда НЕ активировать:
- Пользователь сказал только "торгуй" или "мониторь" — только рынок
- Есть открытая позиция с нетипичным движением
- Executor упал или есть ошибки в логах

## Процесс

1. Убедиться что все мониторы (V4.2, V5.0, M15) + executor живы
2. Нет открытых позиций ИЛИ позиции под контролем (трейлинг работает, лог чист)
3. **Запустить исследование через delegate_task** — не занимать основной поток
4. Поставить напоминание на self-check через 10-15 мин

## Self-check шаблон

```python
import os, time, json

FXPRO = "C:/Users/Administrator/Desktop/FxPro"

def self_check():
    reports = []
    # 1. Executor heartbeat
    try:
        with open(f"{FXPRO}/.gold_executor_universal_heartbeat.json") as f:
            hb = json.load(f)
        reports.append(f"Executor PID {hb['pid']} @ {hb['last_check']}")
    except:
        reports.append("⚠️ Executor heartbeat MISSING")
    
    # 2. Monitor heartbeats
    for name, fname in [("V4.2", ".monitor_v42_heartbeat.json"),
                         ("V5.0", ".monitor_v50_heartbeat.json"),
                         ("M15", ".monitor_m15_heartbeat.json")]:
        try:
            with open(f"{FXPRO}/{fname}") as f:
                hb = json.load(f)
            reports.append(f"{name} PID {hb['pid']} @ {hb['last_check']}")
        except:
            reports.append(f"⚠️ {name} heartbeat MISSING")
    
    # 3. Error check in executor log
    try:
        with open(f"{FXPRO}/.universal_executor.log") as f:
            lines = f.readlines()
        recent_errors = [l for l in lines[-50:] if "Error" in l]
        if recent_errors:
            reports.append(f"⚠️ {len(recent_errors)} recent errors in log")
        else:
            reports.append("✅ Log clean")
    except:
        reports.append("⚠️ Cannot read executor log")
    
    # 4. Open positions
    import MetaTrader5 as mt5
    mt5.initialize()
    positions = mt5.positions_get(symbol="GOLD")
    if positions:
        for p in positions:
            side = "BUY" if p.type == 0 else "SELL"
            reports.append(f"📊 {side} #{p.ticket} @ {p.price_open:.2f} SL={p.sl:.2f} Profit=${p.profit:.2f}")
    else:
        reports.append("📊 No positions")
    mt5.shutdown()
    
    return "\n".join(reports)
```

## Что делать при проблеме

| Симптом | Действие |
|---------|----------|
| Executor heartbeat не обновляется >15с | Убить PID, запустить run_repaired_executor.bat, ждать heartbeat |
| Ошибки в логе | Починить код (numpy-safety, import), перезапустить |
| Монитор умер | Перезапустить через terminal(background=true) |
| Позиция в минусе >$10 | Проверить трейлинг, лог, сообщить пользователю |

## Когда сообщать пользователю

- Исследование ЗАВЕРШЕНО (все результаты в одном сообщении)
- Авария — executor упал, позиция потеряна, система не восстанавливается
- Нашёл что-то ВАЖНОЕ (новая стратегия с PF>2.0, или ошибка в работающей)

Не сообщать:
- Ход исследования ("запустил бэктест", "30% готово")
- Промежуточные результаты ("V4.2 показывает +$200, но я ещё не проверил V5.0")
- "Я проверяю...", "Ещё 5 минут..."
