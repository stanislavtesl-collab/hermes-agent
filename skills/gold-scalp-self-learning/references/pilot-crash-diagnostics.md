# Pilot Crash Diagnostics & Recovery

## Симптомы краша по этапам

### После "=== Optimizing MANAGEMENT ===" с пустым .hermes_learning.log

**Причина:** Функция `grid_mgmt()` не определена или пуста в `hermes_self_learning.py`.

**Как обнаружить:**
1. `.hermes_learning.log` заканчивается строкой `"=== Optimizing MANAGEMENT ==="`
2. `.hermes_failure_patterns.json` существует
3. `.hermes_optimal_params.json`, `.hermes_learning_report.md`, `.hermes_trades.csv` — НЕ существуют
4. `hermes_self_learning.py` содержит `grid_mgmt()` на строке ~495

**Диагностика:**
```python
# В execute_code:
search_files(path="/c/Users/Administrator/Desktop/FxPro/hermes_self_learning.py",
             pattern="def grid_mgmt")
# Если не найдена — это причина краша
```

**Фикс:**
Добавить `grid_mgmt()` в `hermes_self_learning.py`:

```python
def grid_mgmt(fine=False):
    if not fine:
        return [{"trailing_activate_pts":ta,"trailing_offset_pts":tof,"trailing_step_pts":ts,
                 "partial_close_trigger_pts":pt,"partial_close_fraction":pf}
                for ta in (50,80,100,120) for tof in (60,80,100,120) for ts in (50,60,80,100)
                for pt in (80,100,120,150) for pf in (0.3,0.5)]
    return [{"trailing_activate_pts":ta,"trailing_offset_pts":tof,"trailing_step_pts":ts,
             "partial_close_trigger_pts":pt,"partial_close_fraction":pf}
            for ta in (40,60,80,100,120,140) for tof in (50,70,90,110,130)
            for ts in (40,60,80,100,120) for pt in (60,80,100,120,150)
            for pf in (0.25,0.3,0.4,0.5,0.6)]
```

**Вставка:** после `grid_v3()`, перед `def optimize(df, ...)`.
Верификация: `python -m py_compile hermes_self_learning.py`

### После "=== Optimizing V3 ===" или во время V3

**Возможные причины:**
- V3 редко срабатывает (0 сделок на 30 днях) → `n=0` может вызвать деление на ноль в `evaluate()`
- Если `len(mc) == 0` — пустая функция `grid_v3()`

**Фикс:** Если V3 даёт 0 сделок, это нормально для 30-дневного окна. При `--days 180` результаты будут.

### После «PHASE 2: STRATEGY DISCOVERY» — краш после «Generating N strategies...»

**Симптом:** Лог доходит до «Generating 50 strategies...», генерируются 50 случайных стратегий, затем краш с TypeError: evolve() got an unexpected keyword argument «generations».

**Причина:** evolve(df, seeds, gens, elite_k, off_elite) в коде имеет параметр gens, но main() вызывает evolve(df, seeds, generations=args.generations, ...) — несоответствие имени параметра.

**Как обнаружить:**
1. Последняя строка в логе: «Generating N strategies...» (Фаза 2 запустилась, но не начала эволюцию)
2. .hermes_optimal_params.json и .hermes_learning_report.md уже существуют (grid и A/B прошли)
3. .hermes_strategy_library.json — отсутствует
4. Ошибка в stderr: TypeError: evolve() got an unexpected keyword argument 'generations'

**Фикс:**
В коде, строка ~948:
Было:
  survivors = evolve(df, seeds, generations=args.generations, ...)
Стало:
  survivors = evolve(df, seeds, gens=args.generations, ...)

Верификация: python -m py_compile hermes_self_learning.py

После фикса: можно не перезапускать всё — запустить --mode analyze_deals --discover (пересчитает базовые метрики и запустит только Фазу 2).

### Другие возможные краши после «PHASE 2»

**Причина:** df.regime пустой — attach_regime() не смогла классифицировать свечи. Обычно из-за недостаточного периода данных (< 500 свечей).

**Фикс:** Увеличить `--days`. Минимум 90 дней для осмысленной классификации режимов.

## Процедура полного восстановления

1. **Прочитать лог:** `read_file(path=".hermes_learning.log")` — найти последнюю строку
2. **Определить этап:** по последнему `=== * ===` маркеру
3. **Проверить файлы:** `.hermes_optimal_params.json`, `.hermes_failure_patterns.json`, `.hermes_trades.csv` — какие есть, каких нет
4. **Починить код:** применить фикс из секции выше
5. **Очистить старые файлы:**
```bash
rm -f .hermes_learning.log .hermes_failure_patterns.json .hermes_optimal_params.json .hermes_strategy_library.json .hermes_regime_router.json .hermes_learning_report.md .hermes_trades.csv
```
6. **Перезапустить:**
```bash
"/c/Program Files/Python312/python.exe" hermes_self_learning.py --days 30 --population 50 --generations 2
```
7. **Подождать уведомления** (notify_on_complete=true)
8. **Проверить .hermes_learning.log** на полное завершение (строка `DONE. Report:`)

## Метрики времени (на демо-машине)

| Этап | 30 дней | 180 дней |
|------|---------|----------|
| База + данные | ~2-3s | ~10s |
| Real deals | ~1s | ~3s |
| Grid V1 (50 trials) | ~60s | ~180-240s |
| Grid V2 (50 trials) | ~60s | ~40s (0 сделок = быстро) |
| Grid V3 (50 trials) | ~90s | ~150s |
| Grid MANAGEMENT (200 trials) | ~120-180s | ~300-600s |
| A/B Alligator | ~30s | ~120s |
| Фаза 2 (50 pop × 2 gen) | ~180s | ~600s |
| **Всего** | **~8-10 мин** | **~25-40 мин** |

## Файлы пилота

| Файл | Создаётся | Содержание |
|------|-----------|------------|
| `.hermes_learning.log` | Сразу | JSON-лог всех этапов |
| `.hermes_failure_patterns.json` | После analyze_real_deals | Паттерны из сделок |
| `.hermes_optimal_params.json` | После grid | Лучшие параметры |
| `.hermes_trades.csv` | После final run | Все сделки бэктеста |
| `.hermes_learning_report.md` | После write_report | Полный отчёт |
| `.hermes_strategy_library.json` | После Фазы 2 | Стратегии-выжившие |
| `.hermes_regime_router.json` | После Фазы 2 | Роутер по режимам |
