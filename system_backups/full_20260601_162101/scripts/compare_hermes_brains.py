import json
import subprocess
import time
from pathlib import Path

HERMES = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\hermes.exe"
WORKDIR = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
PROMPT = "Дай 3 коротких пункта risk-management для XAUUSD intraday."

CASES = [
    {"name": "deepseek_custom", "provider": "custom", "model": "deepseek-chat"},
    {"name": "openrouter_qwen", "provider": "openrouter", "model": "qwen/qwen3.7-max"},
    {"name": "openrouter_openai", "provider": "openrouter", "model": "openai/gpt-4o-mini"},
    {"name": "openai_codex", "provider": "openai-codex", "model": "gpt-5.4"},
]

results = []
for c in CASES:
    cmd = [HERMES, "--provider", c["provider"], "-m", c["model"], "-z", PROMPT]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=WORKDIR, capture_output=True, text=True, timeout=180)
        dt = round(time.perf_counter() - t0, 2)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        results.append({
            "name": c["name"],
            "provider": c["provider"],
            "model": c["model"],
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "elapsed_s": dt,
            "stdout_preview": out[:220],
            "stderr_preview": err[:220],
        })
    except Exception as e:
        dt = round(time.perf_counter() - t0, 2)
        results.append({
            "name": c["name"],
            "provider": c["provider"],
            "model": c["model"],
            "ok": False,
            "elapsed_s": dt,
            "error": str(e),
        })

print(json.dumps(results, ensure_ascii=False, indent=2))
