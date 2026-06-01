import os
import subprocess
import time
from datetime import datetime

ROOT = r"C:\Users\Administrator\AppData\Local\hermes"
PROJ = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent"
PY = r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
LOG = os.path.join(ROOT, "logs", f"multiagent_3tests_py_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

TESTS = [
    ("T1_SIMPLE", "Коротко объясни RSI в 3 пунктах без торговли и без кода."),
    ("T2_COMPLEX_MTF", "Сделай multi-timeframe анализ XAUUSD (M5/M15/H1/H4), сравни RSI/MACD/EMA/BB, оцени риск и предложи 2 сценария входа с инвалидацией и RR."),
    ("T3_COMPLEX_POSTMORTEM", "Сделай пост-трейд разбор: если long XAUUSD дал -0.8R, разложи причины по технике/риску/данным и дай corrective actions на следующий вход."),
]

def w(s: str):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(s + "\n")


def run_test(name: str, prompt: str, timeout_sec: int = 180):
    w(f"\n=== {name} ===")
    w(f"PROMPT: {prompt}")
    start = time.time()
    try:
        p = subprocess.run(
            [PY, "-m", "hermes_cli.main", "-z", prompt],
            cwd=PROJ,
            env={**os.environ, "HERMES_HOME": ROOT},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_sec,
        )
        w(p.stdout.strip())
        w(f"EXIT={p.returncode}")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "").strip()
        if out:
            w(out)
        w("EXIT=TIMEOUT")
    finally:
        w(f"DURATION_SEC={round(time.time()-start,2)}")


if __name__ == "__main__":
    w(f"START_TS={datetime.now().isoformat(timespec='seconds')}")
    for n, p in TESTS:
        run_test(n, p)
    w(f"END_TS={datetime.now().isoformat(timespec='seconds')}")
    print(LOG)
