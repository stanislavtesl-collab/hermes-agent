"""Reads .gold_state.json and prints notification text only when state changed."""
import hashlib
import json
import os
import sys

STATE_FILE = r"C:\Users\Administrator\Desktop\FxPro\.gold_state.json"
FALLBACK_STATE_FILE = r"C:\Users\Administrator\AppData\Local\hermes\scripts\.gold_state.json"
HASH_FILE = os.path.join(os.path.dirname(__file__), ".gold_last_hash.txt")


def load_state(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    state_path = STATE_FILE if os.path.exists(STATE_FILE) else FALLBACK_STATE_FILE
    if not os.path.exists(state_path):
        print("NO_STATE_FILE")
        return 0

    try:
        state = load_state(state_path)
    except Exception:
        print("NO_STATE_FILE")
        return 0

    state_copy = dict(state)
    state_copy.pop("_time", None)

    current_hash = hashlib.md5(
        json.dumps(state_copy, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    prev_hash = ""
    if os.path.exists(HASH_FILE):
        try:
            with open(HASH_FILE, "r", encoding="utf-8") as f:
                prev_hash = f.read().strip()
        except Exception:
            prev_hash = ""

    if current_hash == prev_hash:
        print("SAME")
        return 0

    with open(HASH_FILE, "w", encoding="utf-8") as f:
        f.write(current_hash)

    state_type = str(state.get("_type", "unknown"))
    title = str(state.get("title", "")).strip()
    body = str(state.get("body", "")).strip()

    if state_type == "open":
        print(f"🆕 {title}\n{body}".strip())
    elif state_type == "closed":
        print(f"✅ {title}\n{body}".strip())
    elif state_type == "trail":
        print(f"🏃 {title}\n{body}".strip())
    elif state_type == "ready":
        print(f"🟢 {title}\n{body}".strip())
    else:
        print(f"ℹ️ {title}\n{body}".strip())

    return 0


if __name__ == "__main__":
    sys.exit(main())
