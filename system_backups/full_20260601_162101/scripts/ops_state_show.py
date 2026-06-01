from __future__ import annotations

import json
from pathlib import Path

HERMES_HOME = Path(r"C:\Users\Administrator\AppData\Local\hermes")
OPS_STATE_PATH = HERMES_HOME / "OPS_STATE.md"
LAST_CHANGE_PATH = HERMES_HOME / "LAST_CHANGE.json"


def main() -> int:
    print("=== HERMES STATE ===")
    if LAST_CHANGE_PATH.exists():
        try:
            data = json.loads(LAST_CHANGE_PATH.read_text(encoding="utf-8", errors="ignore"))
            p = data.get("primary") or {}
            fbs = data.get("fallbacks") or []
            print(f"Updated UTC: {data.get('updated_utc', '')}")
            print(f"Config hash: {data.get('config_hash', '')}")
            print(f"Primary: {p.get('provider','')}/{p.get('model','')}")
            if fbs:
                for fb in fbs:
                    print(f"Fallback {fb.get('order','?')}: {fb.get('provider','')}/{fb.get('model','')}")
            tg = data.get("telegram") or {}
            print(f"Owner ID: {tg.get('owner_id','')}")
            print(f"Allowed chats: {tg.get('allowed_chats','')}")
        except Exception as exc:
            print(f"LAST_CHANGE parse error: {exc}")
    else:
        print("LAST_CHANGE.json not found")

    print("--- OPS_STATE.md ---")
    if OPS_STATE_PATH.exists():
        txt = OPS_STATE_PATH.read_text(encoding="utf-8", errors="ignore")
        print(txt[:3500].strip())
    else:
        print("OPS_STATE.md not found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
