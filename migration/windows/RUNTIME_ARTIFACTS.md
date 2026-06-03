# Runtime Artifacts

These files were copied from the live Hermes Windows server for migration.
They intentionally exclude logs, lock files, heartbeats, .env files, API keys, Telegram tokens and SSH passwords.

- `fxpro_runtime`: MT5/FxPro helpers, monitors, executors, strategy JSON files.
- `user_scripts`: root user helper scripts used by Hermes skills.
- `hermes_home_scripts`: Hermes home operational scripts.
- `gateway-service`: sanitized Gateway starter template.

Before live trading on the new server:
1. Install and login FxPro MT5 to account 591712391.
2. Fill `.env` manually from `env.example`.
3. Run `preflight_new_server.ps1`.
4. Confirm MT5 pinned probe returns account 591712391.
