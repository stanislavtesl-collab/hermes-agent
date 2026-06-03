# OPS + Trading Long Memory

Use this skill whenever the user asks about system changes, trading readiness, repeated failures, daemon/executor/monitor state, MT5 account binding, or lessons from previous trades.

Rules:
- Long memory is advisory context, not runtime truth.
- Runtime truth always comes from `/statesync`, MT5 live account, heartbeat files, process list, scheduled tasks, and current positions.
- The only approved MT5 trading account is `591712391`.
- Before live trading, recall OPS memory, then run strict preflight: DAEMONS, EXECUTOR, MONITORS, WATCHDOGS, MT5_LINK, HEARTBEAT, DRIFT, and optional smoke trade.
- After a fix, outage, trade, or strategy change, save a short memory with the cause, action, result, and next check.
- Never save API keys, Telegram tokens, passwords, SSH secrets, raw private logs, or credentials.

Memory categories:
- OPS memory: configs, brain order, fallback behavior, watchdog rules, recurring bugs, recovery procedures.
- Trading memory: setup, reason for entry, result, TP/SL/trailing behavior, market lesson, next adjustment.
- Recovery memory: monitor down, executor stale, duplicate process, wrong MT5 account, stale heartbeat, invalid API key.

When uncertain:
- Search memory first.
- Verify live state second.
- Act only if live state confirms the memory is still valid.

## Trading Pause Mode
- If `C:\Users\Administrator\Desktop\FxPro\.trading_paused` exists, trading is intentionally paused by owner/Codex.
- In pause mode `/statesync` may return `STATE_SYNC_PAUSED`; this is not a failure if `OPEN_ISSUES=none`.
- Do not repair, restart, or auto-enable executor/monitors/manager while pause flag exists.
- To resume trading, use the controlled resume script only after owner approval: `C:\Users\Administrator\AppData\Local\hermes\scripts\hermes_trading_resume.ps1`.

## MT5 Hard Guard
- The only allowed account is `591712391`.
- Active runtime scripts must initialize MT5 with explicit path `C:\Users\Administrator\Desktop\FxPro\terminal64.exe` and must reject any other account.
- Never use bare `mt5.initialize()` for trading/runtime decisions because it may attach to another terminal/account.
