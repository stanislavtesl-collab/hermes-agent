import json
import socket
from datetime import datetime, timezone
from pathlib import Path

host = "127.0.0.1"
port = 3111
status = {"ok": False, "host": host, "port": port, "checked_at": datetime.now(timezone.utc).isoformat()}
try:
    with socket.create_connection((host, port), timeout=3):
        status["ok"] = True
except Exception as exc:
    status["error"] = repr(exc)

Path(r"C:\Users\Administrator\AppData\Local\hermes\scripts\agentmemory_health.json").write_text(
    json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(status, ensure_ascii=False))
raise SystemExit(0 if status["ok"] else 1)
