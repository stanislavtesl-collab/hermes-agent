# Пилот самообучения: краш на MANAGEMENT (29 May 2026)

## Симптом
Пилотный прогон (`hermes_self_learning.py --days 30 --population 50 --generations 2`) успешно завершил:
- V1 grid (score 7.27)
- V2 grid (0 сделок — нормально)
- V3 grid (score 96.206)

И упал на строке:
```
=== Optimizing MANAGEMENT ===
```
После чего лог обрывается. Выходные файлы `.hermes_optimal_params.json`, `.hermes_trades.csv`, `.hermes_learning_report.md` не созданы.

Созданы частичные: `.hermes_failure_patterns.json` (17 сделок, 76% WR, +$11.77)

## Причина
В коде `hermes_self_learning.py` отсутствует функция `optimize_management()` — вызывается в `main()` после optimize(V1/V2/V3), но не определена.

## Прошлые параметры MANAGEMENT (из DEFAULT_PARAMS)
```
"TRAIL_ACTIVATE": 80, "TRAIL_STEP": 80, "TRAIL_OFFSET": 100,
"PARTIAL_CLOSE_PTS": 100, "PARTIAL_CLOSE_PCT": 0.5,
"ALLIGATOR_GATE": "hard",
"MAX_SPREAD": 20, "MIN_VOLUME": 100
```

## Найденные параметры V1 (нуждаются в live-тесте)
- Score: 7.269
- Сделок: 208
- WR: 57.7%
- Ожидание: $8.187
- Profit Factor: 1.24
- DD: $837.05
- **Это в 3.6× лучше базовых $2.26 ожидания**

## Решение для следующего запуска
1. Добавить функцию `optimize_management()` в `hermes_self_learning.py`
2. Или заменить MANAGEMENT на управляемые константы (не оптимизируются)
3. Перезапустить с `--mode optimize` для получения полного отчёта
