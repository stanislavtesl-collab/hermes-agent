# SRE Self-Heal Procedure — Hermes Agent System Audit

Performed on demand (trigger: "self-check", "SRE", "system audit").

## Phase 1: Read-Only Inventory

### gateway + cron
```python
cronjob(action='list')  # check for duplicates, zombie jobs
```

### processes
```python
process(action='list')
# bash:
tasklist //V | grep -i python  # identify all python processes
tasklist //V | grep -i -E "gold|terminal"  # trading-related
```

### gold daemon health
```bash
cat /c/Users/Administrator/Desktop/FxPro/.gold_daemon.lock  # PID
cat /c/Users/Administrator/Desktop/FxPro/.gold_heartbeat.json  # freshness
cat /c/Users/Administrator/Desktop/FxPro/.gold_state.json  # current state
```

### config audit (config.yaml)
Key sections to verify:
- `model.provider` — should be `custom` (DeepSeek)
- `memory.provider` — should be `holographic`
- `telegram.allowed_chats` — should be `'534151570'`
- `fallback_providers` — check for duplicates, ensure != primary
- `security.*` — owner-lock, tirith_fail_open
- `auxiliary.vision` — model provider for vision tasks
- `delegation.*` — orchestrator_enabled, max_spawn_depth

### config traps to detect
- `auxiliary.*.model: ''` + `provider: auto` = uses model.default, which is `deepseek-chat` with NO vision capabilty
- `fallback_providers` with same model via different endpoints = single point of failure
- `tirith_fail_open: true` = any TIRITH failure allows execution (low security)
- Empty `telegram.allowed_chats` = any user can interact

## Phase 2: Target State Comparison

| Check | Target | Finding → Action |
|-------|--------|------------------|
| owner-only | telegram.allowed_chats = '534151570' | Empty → FIX |
| fallback | 2+ different providers/models | Duplicates → REPORT |
| memory usage | < 80% of limit | Check memory_char_limit + current |
| notify channel | exactly 1 active 30s cron | 0 or 2+ → CLEAN |
| daemon process | exactly 1 gold_manager_daemon | 2+ → KILL duplicate |
| monitor process | exactly 1 _gold_monitor_v3 | Stale v2 → KILL |

## Phase 3: Safe Auto-Repair (no confirmation needed)

Safe to do:
- Kill duplicate daemon (PID in Hermes venv vs uv python — keep the one with lock)
- Kill old monitor versions (v2 if v3 is running)
- Remove dead cron jobs (completed/disabled — no next_run_at)
- Set `telegram.allowed_chats` to user's Telegram ID
- Restart monitor after cleanup

NOT safe without confirmation:
- Mass kill of python processes
- Edit trade logic (V1/V2/V3/V5 strategy code)
- Edit MT5 scripts or entry scripts
- Touch second project on :8000 (gold_ews)
- Change API keys
- Set `security.owner` (requires gateway restart)
- Toggle `tirith_fail_open` (risk of locking self out)

## Phase 4: Verification

After repairs:
1. ✅ Daemon alive (lock + heartbeat)
2. ✅ v3 monitor running
3. ✅ No duplicate processes
4. ✅ cron list clean
5. ✅ telegram.allowed_chats set
6. ✅ memory usage < 80%
7. Report status: GREEN / YELLOW / RED

## Full Process Trace (reference: 29 May 2026 session)

Found:
- 2 x gold_manager_daemon (PID 9060 + 9312) → killed 9060 (hermes venv, no lock)
- 1 x stale _gold_monitor_v2 (PID 8532) → killed (v3 already running)
- 2 dead cron jobs (completed/disabled) → removed
- telegram.allowed_chats empty → set to '534151570'
- 10 empty skill category folders (DESCRIPTION.md only) → noted, not cleaned
- TIRITH fail_open = true → reported, not changed
- Owner-only not configured → reported, needs /reset

Status: 🔶 YELLOW — 5 fixed, 2 pending user decision
