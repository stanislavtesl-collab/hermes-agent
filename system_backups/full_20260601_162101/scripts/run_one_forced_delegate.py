import os
import subprocess
import time
from datetime import datetime

ROOT = r"C:\Users\Administrator\AppData\Local\hermes"
PROJ = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
PY = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
LOG = os.path.join(ROOT, "logs", f"forced_delegate_one_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
PROMPT = "Сложная задача по XAUUSD: multi-timeframe M5/M15/H1/H4 + RSI/MACD/EMA/BB + риск и 2 сценария. Обязательно соблюдай trading-orchestrator protocol и выдай блок Subagent summary."

with open(LOG, "w", encoding="utf-8") as f:
    f.write(f"START_TS={datetime.now().isoformat(timespec='seconds')}\n")
    f.write(f"PROMPT={PROMPT}\n\n")
start = time.time()
try:
    p = subprocess.run(
        [PY, "-m", "hermes_cli.main", "-z", PROMPT],
        cwd=PROJ,
        env={**os.environ, "HERMES_HOME": ROOT},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=210,
    )
    out = p.stdout or ""
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(out)
        f.write(f"\nEXIT={p.returncode}\n")
except subprocess.TimeoutExpired as e:
    out = (e.stdout or "")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(out)
        f.write("\nEXIT=TIMEOUT\n")
finally:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"DURATION_SEC={round(time.time()-start,2)}\n")
        f.write(f"END_TS={datetime.now().isoformat(timespec='seconds')}\n")
print(LOG)
