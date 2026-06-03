from __future__ import annotations
import hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

HERMES_HOME = Path(r"C:\Users\Administrator\AppData\Local\hermes")
AGENT_HOME = HERMES_HOME / "hermes-agent"
USER_HERMES_HOME = Path(r"C:\Users\Administrator\.hermes")
CONFIG_PATHS = [USER_HERMES_HOME / "config.yaml", HERMES_HOME / "config.yaml", AGENT_HOME / "config.yaml"]
ENV_PATHS = [HERMES_HOME / ".env", AGENT_HOME / ".env"]
OPS_STATE_PATH = HERMES_HOME / "OPS_STATE.md"
LAST_CHANGE_PATH = HERMES_HOME / "LAST_CHANGE.json"
HB_PATH = Path(r"C:\Users\Administrator\Desktop\FxPro\.gold_heartbeat.json")
MT5_QUERY = Path(r"C:\Users\Administrator\mt5_query.py")
EXPECTED_LOGIN = "591712391"
EXPECTED_MONITORS = [
    ("v43", "_gold_monitor_v43.py", Path(r"C:\Users\Administrator\Desktop\FxPro\.monitor_v42_heartbeat.json"), 90),
    ("v50", "_gold_monitor_v50_direct.py", Path(r"C:\Users\Administrator\Desktop\FxPro\.gold_monitor_hb_v50.json"), 90),
    ("m15", "_gold_monitor_m15_direct.py", Path(r"C:\Users\Administrator\Desktop\FxPro\.gold_monitor_hb_m15.json"), 120),
]
EXECUTOR_SCRIPT = "_gold_universal_executor.py"
EXECUTOR_HEARTBEAT = Path(r"C:\Users\Administrator\Desktop\FxPro\.gold_executor_heartbeat.json")
NOTIFY_HEARTBEAT = Path(r"C:\Users\Administrator\AppData\Local\hermes\logs\gold_state_notify_30s.hb.json")
TRADING_PAUSED_PATH = Path(r"C:\Users\Administrator\Desktop\FxPro\.trading_paused")
TRADING_PAUSED_JSON = Path(r"C:\Users\Administrator\Desktop\FxPro\.trading_paused.json")

def run(cmd: str, timeout: int = 20) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=timeout)
    except Exception:
        return ""

def first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None

def cfg() -> tuple[Path|None, dict[str,Any]]:
    p = first_existing(CONFIG_PATHS)
    if not p: return None, {}
    try: return p, (yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    except Exception: return p, {}

def env_var(name: str) -> str:
    for p in ENV_PATHS:
        if not p.exists(): continue
        for raw in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k,v = line.split("=",1)
            if k.strip() == name: return v.strip().strip('"').strip("'")
    return ""

def cfg_hash(path: Path|None) -> str:
    if not path or not path.exists(): return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

def task_state(task_name: str) -> str:
    out = run(f'schtasks /query /tn "{task_name}" /v /fo list')
    for ln in out.splitlines():
        s = ln.strip().lower()
        if s.startswith("scheduled task state:"):
            return ln.split(":",1)[1].strip()
    return "NOT_FOUND"

def proc_count(pattern: str) -> int:
    q = f'wmic process where "CommandLine like \'%{pattern}%\' and (name=\'python.exe\' or name=\'pythonw.exe\')" get ProcessId /value'
    out = run(q)
    return sum(1 for ln in out.splitlines() if ln.strip().startswith("ProcessId="))

def file_age_seconds(path: Path) -> float | None:
    try:
        if not path.exists():
            return None
        return max(0.0, datetime.now().timestamp() - path.stat().st_mtime)
    except Exception:
        return None

def monitor_info() -> tuple[str, str]:
    details = []
    ok_all = True
    running_total = 0
    for label, script, hb_path, max_age in EXPECTED_MONITORS:
        count = proc_count(script)
        running_total += count
        age = file_age_seconds(hb_path)
        fresh = age is not None and age <= max_age
        ok = count == 1 and fresh
        if not ok:
            ok_all = False
        age_s = "missing" if age is None else f"{age:.1f}s"
        details.append(f"{label}:pid_count={count},hb_age={age_s},max={max_age}s")
    status = "OK" if ok_all else "FAIL"
    return status, f"expected={len(EXPECTED_MONITORS)} running={running_total} " + " | ".join(details)

def executor_info() -> tuple[str, str]:
    count = proc_count(EXECUTOR_SCRIPT)
    age = file_age_seconds(EXECUTOR_HEARTBEAT)
    fresh = age is not None and age <= 90
    status = "OK" if count == 1 and fresh else "FAIL"
    age_s = "missing" if age is None else f"{age:.1f}s"
    return status, f"pid_count={count} hb_age={age_s} max=90s"

def mt5_login() -> str:
    py = AGENT_HOME / ".venv" / "Scripts" / "python.exe"
    if not py.exists() or not MT5_QUERY.exists(): return ""
    out = run(f'"{py}" "{MT5_QUERY}" account', timeout=25).strip()
    try:
        obj = json.loads(out)
        v = obj.get("login")
        return "" if v is None else str(v)
    except Exception:
        return ""

def heartbeat_info() -> tuple[str,str]:
    if not HB_PATH.exists(): return "FAIL","NO_FILE"
    try:
        obj = json.loads(HB_PATH.read_text(encoding="utf-8"))
        ts = str(obj.get("_time") or obj.get("time") or "")
        return ("OK", ts if ts else "NO_TS")
    except Exception:
        return "FAIL","PARSE_ERR"

def pause_info() -> tuple[bool, str]:
    if not TRADING_PAUSED_PATH.exists() and not TRADING_PAUSED_JSON.exists():
        return False, ""
    reason = "manual"
    try:
        if TRADING_PAUSED_JSON.exists():
            obj = json.loads(TRADING_PAUSED_JSON.read_text(encoding="utf-8"))
            reason = str(obj.get("reason") or reason)
            ts = str(obj.get("ts") or "")
            if ts:
                reason = f"{reason},ts={ts}"
    except Exception:
        pass
    return True, reason

def memory_info() -> tuple[str, str]:
    out = run('powershell -NoProfile -Command "try { (Invoke-RestMethod -Uri \'http://127.0.0.1:3111/agentmemory/health\' -TimeoutSec 5).status } catch { \'FAIL\' }"', timeout=10).strip()
    if "healthy" in out.lower():
        return "OK", "agentmemory healthy 127.0.0.1:3111"
    return "FAIL", out or "agentmemory unavailable"

def main() -> int:
    path, c = cfg()
    h = cfg_hash(path)
    model = c.get("model") or {}
    primary = f'{model.get("provider","")}/{model.get("default","")}'.strip("/")
    fb = c.get("fallback_providers") or []
    fb_rows = []
    for i, item in enumerate(fb, start=1):
        if isinstance(item, dict):
            fb_rows.append(f'{i}. provider={item.get("provider","")} model={item.get("model","")}')
    fallbacks = " | ".join(fb_rows) if fb_rows else "(none)"

    daemon_n = proc_count("gold_manager_daemon.py")
    mon_ok, mon_detail = monitor_info()
    exe_ok, exe_detail = executor_info()
    wd_tasks = ["GoldEWS-Watchdog","Gold_Daemon_Watchdog","Hermes_Gold_State_Notify_30s","Hermes_Gold_Navigation_Supervisor","Hermes_AgentMemory_Watchdog"]
    wd_states = [f"{t}:{task_state(t)}" for t in wd_tasks]
    notify_age = file_age_seconds(NOTIFY_HEARTBEAT)
    notify_fresh = notify_age is not None and notify_age <= 90
    notify_age_s = "missing" if notify_age is None else f"{notify_age:.1f}s"
    wd_states.append(f"notify_hb_age={notify_age_s}")

    mt5 = mt5_login()
    hb_ok, hb_ts = heartbeat_info()
    mem_ok, mem_detail = memory_info()
    paused, pause_reason = pause_info()

    mt5_ok = (mt5 == EXPECTED_LOGIN and mt5 != "")
    mt5_line = f'{"OK" if mt5_ok else "FAIL"} account={mt5 or "(none)"} expected={EXPECTED_LOGIN}'
    memory_line = f'{mem_ok} {mem_detail}'

    if paused:
        daemons_line = f"PAUSED count={daemon_n}"
        monitors_line = f"PAUSED expected={len(EXPECTED_MONITORS)} running={sum(proc_count(x[1]) for x in EXPECTED_MONITORS)} reason={pause_reason}"
        executor_line = f"PAUSED pid_count={proc_count(EXECUTOR_SCRIPT)} reason={pause_reason}"
        watchdogs_line = "PAUSED " + ", ".join(wd_states)
        heartbeat_line = f"PAUSED last_ts={hb_ts}"
        issues = []
        if not mt5_ok: issues.append("MT5_ACCOUNT_MISMATCH")
        if mem_ok != "OK": issues.append("MEMORY_FAIL")
        open_issues = "none" if not issues else ";".join(issues)
        status = "STATE_SYNC_PAUSED" if open_issues == "none" else "STATE_SYNC_FAIL"
        trading_line = f"PAUSED {pause_reason}"
    else:
        daemons_line = f'{"OK" if daemon_n>0 else "FAIL"} count={daemon_n}'
        monitors_line = f"{mon_ok} {mon_detail}"
        executor_line = f"{exe_ok} {exe_detail}"
        wd_ok = all(any(x in s for x in ("Ready","Running","Enabled")) for s in wd_states if ":" in s) and notify_fresh
        watchdogs_line = f'{"OK" if wd_ok else "FAIL"} ' + ", ".join(wd_states)
        heartbeat_line = f'{hb_ok} last_ts={hb_ts}'
        issues = []
        if daemon_n <= 0: issues.append("DAEMONS_DOWN")
        if mon_ok != "OK": issues.append("MONITORS_DOWN")
        if exe_ok != "OK": issues.append("EXECUTOR_DOWN")
        if not wd_ok: issues.append("WATCHDOGS_DEGRADED")
        if not mt5_ok: issues.append("MT5_ACCOUNT_MISMATCH")
        if hb_ok != "OK": issues.append("HEARTBEAT_FAIL")
        if mem_ok != "OK": issues.append("MEMORY_FAIL")
        open_issues = "none" if not issues else ";".join(issues)
        status = "STATE_SYNC_OK" if open_issues == "none" else "STATE_SYNC_FAIL"
        trading_line = "LIVE"

    now = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    ops = [
        "# Hermes OPS State",
        f"Updated (UTC): {now}",
        f"Config hash: {h}",
        f"Primary: {primary}",
        f"Fallbacks: {fallbacks}",
        f"DAEMONS: {daemons_line}",
        f"MONITORS: {monitors_line}",
        f"EXECUTOR: {executor_line}",
        f"WATCHDOGS: {watchdogs_line}",
        f"MT5_LINK: {mt5_line}",
        f"HEARTBEAT: {heartbeat_line}",
        f"MEMORY: {memory_line}",
        f"TRADING: {trading_line}",
        f"OPEN_ISSUES: {open_issues}",
    ]
    OPS_STATE_PATH.write_text("\n".join(ops) + "\n", encoding="utf-8")
    LAST_CHANGE_PATH.write_text(json.dumps({
        "updated_utc": now, "config_hash": h, "primary": primary, "fallbacks": fallbacks,
        "daemons": daemons_line, "monitors": monitors_line, "executor": executor_line, "watchdogs": watchdogs_line,
        "mt5_link": mt5_line, "heartbeat": heartbeat_line, "memory": memory_line, "trading": trading_line, "open_issues": open_issues
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(status)
    print(f"PRIMARY={primary}")
    print(f"FALLBACKS={fallbacks}")
    print(f"CONFIG_HASH={h}")
    print(f"DAEMONS={daemons_line}")
    print(f"MONITORS={monitors_line}")
    print(f"EXECUTOR={executor_line}")
    print(f"WATCHDOGS={watchdogs_line}")
    print(f"MT5_LINK={mt5_line}")
    print(f"HEARTBEAT={heartbeat_line}")
    print(f"MEMORY={memory_line}")
    print(f"TRADING={trading_line}")
    print(f"OPEN_ISSUES={open_issues}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

