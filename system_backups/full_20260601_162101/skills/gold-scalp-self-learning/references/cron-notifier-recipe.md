# Cronjob-читатель .gold_state.json — реализация

Выбрано пользователем вместо апгрейда демона до v8. Крон раз в 30 секунд читает
.gold_state.json и доставляет уведомления о сделках в Telegram.

## Скрипт gold_state_reader.py

Сохранить в `~/AppData/Local/hermes/scripts/gold_state_reader.py`:

```python
"""Читает .gold_state.json и шлёт уведомление через Hermes, если событие новое."""
import json
import os
import hashlib

STATE_FILE = r"C:\Users\Administrator\Desktop\FxPro\.gold_state.json"
HASH_FILE = os.path.join(os.path.dirname(__file__), '.gold_last_hash.txt')

if not os.path.exists(STATE_FILE):
    print("NO_STATE_FILE")
    exit(0)

with open(STATE_FILE, 'r') as f:
    state = json.load(f)

# Хеш без _time (меняется каждую секунду — не информативно)
state_copy = dict(state)
state_copy.pop('_time', None)
current_hash = hashlib.md5(json.dumps(state_copy, sort_keys=True).encode()).hexdigest()

prev_hash = ""
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, 'r') as f:
        prev_hash = f.read().strip()

if current_hash == prev_hash:
    print("SAME")
    exit(0)

with open(HASH_FILE, 'w') as f:
    f.write(current_hash)

state_type = state.get('_type', 'unknown')
title = state.get('title', '')
body = state.get('body', '')

type_map = {
    'open': f"🆕 {title}\n{body}",
    'closed': f"✅ {title}\n{body}",
    'trail': f"🏃 {title}\n{body}",
    'ready': f"🟢 {title}\n{body}",
}
print(type_map.get(state_type, f"ℹ️ {title}\n{body}"))
```

## Cronjob (создать в Hermes)

```bash
hermes cron create \
  --name "gold-state-watcher" \
  --schedule "once in 30s" \
  --prompt "Прочитай вывод скрипта. Если не 'SAME' и не 'NO_STATE_FILE' — перешли сообщение пользователю как есть." \
  --script "~/AppData/Local/hermes/scripts/gold_state_reader.py" \
  --deliver "origin"
```

## Важные моменты

- Первый запуск всегда пришлёт текущее состояние — норм
- Хеш-файл `.gold_last_hash.txt` лежит в `~/AppData/Local/hermes/scripts/`
- Если демон упадёт и перезапустится — `_time` изменится, но хеш без `_time` не поменяется, если состояние то же самое. **Однако** при старте демон пишет `ready`, а хеш `ready`-сообщения уникален (содержит timestamp), так что перезапуск демона будет замечен.
- При `closed` событии — убедись что скрипт не выдаст повторно то же сообщение (хеш не должен совпадать с предыдущим `closed`)
