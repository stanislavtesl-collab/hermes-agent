# MT5 Windows Launch: Git-Bash subprocess bug

## Проблема

`mt5.initialize()` НЕ РАБОТАЕТ из Git-Bash subprocess'ов:
- `terminal(background=True)` → Python Popen → init зависает
- `python _script.py &` → то же
- `subprocess.Popen(... CREATE_NO_WINDOW)` → то же

**Причина:** Git-Bash (MSYS) создаёт дочерние процессы с другим контекстом RDP-сессии. MT5 использует IPC pipe, привязанный к конкретному пользовательскому сеансу (RDP-Tcp#X). Subprocess'ы из Git-Bash теряют эту привязку.

**Доказательство:** `python -c "import MetaTrader5 as mt5; print(mt5.initialize(path='...'))"` напрямую в Git-Bash — работает. Тот же код из Popen — нет.

## Решение

**Способ 1 — bat + cmd-окно (надёжнее всего):**
1. Создать `.bat` файл с полным путём к Python:
   ```bat
   @echo off
   cd /d C:\Users\Administrator\Desktop\FxPro
   "C:\Program Files\Python312\python.exe" _script.py
   pause
   ```
2. Пользователь кликает по bat → открывается cmd-окно (тот же RDP-сеанс) → init проходит
3. Окно должно оставаться открытым — процесс живёт внутри

**Способ 2 — блокирующий foreground-запуск:**
```bash
cd "C:/Users/Administrator/Desktop/FxPro"
"C:/Program Files/Python312/python.exe" _script.py
```
Не background, а foreground с большим timeout в terminal tool.

## V4.2 — конкретные файлы

Все в `C:\Users\Administrator\Desktop\FxPro\`:
- `_gold_monitor_v42.py` — монитор
- `_gold_executor_v42.py` — executor
- `_boot_executor_v42.py` — загрузчик (MT5 check → exec executor)
- `run_executor_v42.bat` — bat для запуска executor
- `_v42_manager.py` — менеджер

Сигнал: `.gold_trade_signal.json` с `source: "monitor_v42"`, `action: "BUY"/"SELL"`
Трейлинг: `.v42_trail.json`

Проверка: `.monitor_v42_heartbeat.json`, `.gold_executor_v42.log`
