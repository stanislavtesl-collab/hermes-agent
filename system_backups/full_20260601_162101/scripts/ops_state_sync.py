from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

HERMES_HOME = Path(r"C:\Users\Administrator\AppData\Local\hermes")
AGENT_HOME = HERMES_HOME / "hermes-agent"
CONFIG_PATHS = [HERMES_HOME / "config.yaml", AGENT_HOME / "config.yaml"]
ENV_PATHS = [HERMES_HOME / ".env", AGENT_HOME / ".env"]
OPS_STATE_PATH = HERMES_HOME / "OPS_STATE.md"
LAST_CHANGE_PATH = HERMES_HOME / "LAST_CHANGE.json"
PREFILL_PATH = HERMES_HOME / "prefill_ops_state.json"
GOLD_HEARTBEAT_PATH = Path(r"C:\Users\Administrator\Desktop\FxPro\.gold_heartbeat.json")
MT5_TERMINAL_EXPECTED = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"


def _read_env_var(name: str) -> str:
    for env_path in ENV_PATHS:
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    return ""


def _pick_first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _cfg(config_path: Path | None) -> dict[str, Any]:
    if not config_path or not config_path.exists():
        return {}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _as_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=20)
    except Exception:
        return ""


def _detect_terminal_paths() -> list[str]:
    out = _run("wmic process where \"name='terminal64.exe'\" get ExecutablePath /value")
    paths: list[str] = []
    for raw in out.splitlines():
        line = raw.strip()
        if not line.startswith("ExecutablePath="):
            continue
        p = line.split("=", 1)[1].strip()
        if p:
            paths.append(p)
    # dedupe keep order
    seen = set()
    uniq: list[str] = []
    for p in paths:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
    return uniq


def _daemon_count() -> int:
    out = _run("wmic process where \"CommandLine like '%gold_manager_daemon.py%' and (name='python.exe' or name='pythonw.exe')\" get ProcessId /value")
    return sum(1 for line in out.splitlines() if line.strip().startswith("ProcessId="))


def _gold_ews_state() -> str:
    out = _run("schtasks /query /tn GoldEWS /v /fo list")
    for raw in out.splitlines():
        line = raw.strip()
        if line.lower().startswith("scheduled task state:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _mt5_account_login() -> str:
    mt5_py = Path(r"C:\Users\Administrator\mt5_query.py")
    venv_py = AGENT_HOME / ".venv" / "Scripts" / "python.exe"
    if not mt5_py.exists() or not venv_py.exists():
        return ""
    out = _run(f'"{venv_py}" "{mt5_py}" account')
    try:
        obj = json.loads(out.strip())
        login = obj.get("login")
        return str(login) if login is not None else ""
    except Exception:
        return ""


def main() -> int:
    config_path = _pick_first_existing(CONFIG_PATHS)
    cfg = _cfg(config_path)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    model = cfg.get("model") or {}
    primary_model = _as_str(model.get("default"))
    primary_provider = _as_str(model.get("provider"))
    primary_base_url = _as_str(model.get("base_url"))

    fallbacks = cfg.get("fallback_providers") or []
    fb_rows: list[str] = []
    fb_json: list[dict[str, str]] = []
    for i, fb in enumerate(fallbacks, start=1):
        if not isinstance(fb, dict):
            continue
        p = _as_str(fb.get("provider"))
        m = _as_str(fb.get("model"))
        b = _as_str(fb.get("base_url"))
        row = f"{i}. provider={p} model={m}"
        if b:
            row += f" base_url={b}"
        fb_rows.append(row)
        fb_json.append({"order": str(i), "provider": p, "model": m, "base_url": b})

    tg_cfg = cfg.get("telegram") or {}
    allowed_chats = _as_str(tg_cfg.get("allowed_chats"))
    owner_id = _read_env_var("TELEGRAM_OWNER_ID")

    cfg_hash = ""
    if config_path and config_path.exists():
        cfg_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()[:16]

    ops_md = [
        "# Hermes OPS State",
        "",
        f"Updated (UTC): {now}",
        f"Config hash: {cfg_hash}",
        "",
        "## Locked Brain Order",
        f"Primary: provider={primary_provider} model={primary_model} base_url={primary_base_url}",
        "Fallbacks:",
    ]
    if fb_rows:
        ops_md.extend([f"- {x}" for x in fb_rows])
    else:
        ops_md.append("- (none)")

    ops_md.extend(
        [
            "",
            "## Access Scope",
            f"Telegram owner id: {owner_id or '(not set)'}",
            f"Telegram allowed_chats: {allowed_chats or '(not set)'}",
            "",
            "## Runtime Notes",
            "- This file is generated by scripts/ops_state_sync.py.",
            "- Use /state to view active state and /statesync after config changes.",
        ]
    )

    OPS_STATE_PATH.write_text("\n".join(ops_md).strip() + "\n", encoding="utf-8")

    last_change = {
        "updated_utc": now,
        "config_hash": cfg_hash,
        "primary": {
            "provider": primary_provider,
            "model": primary_model,
            "base_url": primary_base_url,
        },
        "fallbacks": fb_json,
        "telegram": {
            "owner_id": owner_id,
            "allowed_chats": allowed_chats,
        },
        "source": "ops_state_sync.py",
        "config_path": str(config_path) if config_path else "",
    }
    LAST_CHANGE_PATH.write_text(json.dumps(last_change, ensure_ascii=False, indent=2), encoding="utf-8")

    terminals = _detect_terminal_paths()
    daemon_count = _daemon_count()
    gold_ews_state = _gold_ews_state()
    mt5_login = _mt5_account_login()
    heartbeat_pid = ""
    if GOLD_HEARTBEAT_PATH.exists():
        try:
            heartbeat_pid = _as_str(json.loads(GOLD_HEARTBEAT_PATH.read_text(encoding="utf-8")).get("pid"))
        except Exception:
            heartbeat_pid = ""

    prefill = [
        {
            "role": "system",
            "content": (
                "Always align with current runtime state from OPS_STATE.md and LAST_CHANGE.json. "
                "If user asks about current configuration, use /state output as source of truth."
            ),
        },
        {
            "role": "system",
            "content": (
                f"Locked brains: primary={primary_provider}/{primary_model}; "
                + (
                    "fallback1=" + f"{fb_json[0]['provider']}/{fb_json[0]['model']}" if len(fb_json) > 0 else "fallback1=none"
                )
                + "; "
                + (
                    "fallback2=" + f"{fb_json[1]['provider']}/{fb_json[1]['model']}" if len(fb_json) > 1 else "fallback2=none"
                )
                + f"; state_version={cfg_hash}; updated_utc={now}."
            ),
        },
        {
            "role": "system",
            "content": (
                "Trading runtime invariants (must preserve): "
                f"MT5 terminal should be single and bound to {MT5_TERMINAL_EXPECTED}; "
                f"observed_terminals={terminals if terminals else ['(none)']}; "
                f"MT5 account login={mt5_login or '(unknown)'}; "
                f"gold_daemon_process_count={daemon_count}; "
                f"gold_daemon_heartbeat_pid={heartbeat_pid or '(unknown)'}; "
                f"GoldEWS_task_state={gold_ews_state}. "
                "Do not drift from these invariants without explicit owner approval."
            ),
        },
    ]
    PREFILL_PATH.write_text(json.dumps(prefill, ensure_ascii=False, indent=2), encoding="utf-8")

    print("STATE_SYNC_OK")
    print(f"PRIMARY={primary_provider}/{primary_model}")
    if fb_rows:
        print("FALLBACKS=" + " | ".join(fb_rows))
    else:
        print("FALLBACKS=(none)")
    print(f"CONFIG_HASH={cfg_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
