import json
import subprocess
import time

HERMES = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\hermes.exe"
WORKDIR = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent"

CASES = [
    ("codex", "openai-codex", "gpt-5.4"),
    ("deepseek", "custom", "deepseek-chat"),
    ("qwen", "openrouter", "qwen/qwen3.7-max"),
]

PROMPTS = [
    ("latency_ping", "Ответь только: ОК"),
    (
        "mt5_realtime_plan",
        "Ты торговый ассистент MT5. Дай короткий план действий по XAUUSD на 5m при условиях: price=3348.2, RSI=62, MACD_hist=+0.8, EMA20>EMA50, spread=18 points. Формат: 1) bias 2) entry rule 3) stop 4) invalidation. Без дисклеймеров и воды.",
    ),
    (
        "risk_controls",
        "Для счёта 1560 USD и лота 0.03 по XAUUSD дай 3 жёстких правила risk-management intraday. Только 3 пункта, по 1 строке.",
    ),
]

results = []
for pname, prompt in PROMPTS:
    for name, provider, model in CASES:
        t0 = time.perf_counter()
        p = subprocess.run(
            [HERMES, "--provider", provider, "-m", model, "-z", prompt],
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=180,
        )
        elapsed = round(time.perf_counter() - t0, 2)
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        results.append(
            {
                "prompt": pname,
                "brain": name,
                "provider": provider,
                "model": model,
                "ok": p.returncode == 0,
                "rc": p.returncode,
                "elapsed_s": elapsed,
                "out_preview": out[:500],
                "out_len": len(out),
                "err_preview": err[:200],
            }
        )

print(json.dumps(results, ensure_ascii=False, indent=2))
