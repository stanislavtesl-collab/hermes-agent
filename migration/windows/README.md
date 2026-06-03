# Hermes Trader Bot Windows Migration Kit

Generated UTC: 2026-06-03T13:02:55.7283051Z

## GitHub sources

- Core Hermes repo: https://github.com/stanislavtesl-collab/hermes-agent
- Skills repo: https://github.com/stanislavtesl-collab/hermes-codex-skills

## Target Windows paths

- Hermes home: C:\Users\Administrator\AppData\Local\hermes
- Agent repo: C:\Users\Administrator\AppData\Local\hermes\hermes-agent
- Skills: C:\Users\Administrator\AppData\Local\hermes\skills
- FxPro MT5 terminal: C:\Users\Administrator\Desktop\FxPro\terminal64.exe
- Required MT5 account: 591712391

## Restore order for Cloud Code

1. Install Windows Server prerequisites: Git, Python 3.11, PowerShell, FxPro MT5 terminal.
2. Clone core repo and skills repo.
3. Run migration\windows\restore_new_windows_server.ps1 from the agent repo.
4. Create .env from migration\windows\env.example and fill real credentials manually.
5. Start/login FxPro MT5 terminal to account 591712391.
6. Copy runtime-only FxPro scripts if needed from current server backup or repo artifacts.
7. Run migration\windows\preflight_new_server.ps1.
8. Do not start live trading until preflight reports MT5_LINK OK for account 591712391.

## Security rules

- Do not commit real .env, API keys, Telegram tokens, SSH passwords, MT5 passwords.
- Runtime/trading must use only pinned FxPro terminal path and account 591712391.
- Do not use Atman Gibrid terminal for Hermes runtime.
- If live runtime conflicts with memory, live runtime wins.

## Current OPS snapshot

See migration/windows/OPS_STATE.snapshot.md.
