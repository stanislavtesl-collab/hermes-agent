# nohup Launch Pattern for MT5 Monitors — 1 June 2026

## The Problem

Monitors launched via `terminal(background=true)` **exit** when the Hermes agent's terminal session completes or the context switches. Even though the process is "started in background", Git-Bash kills child processes when the parent terminal tool call completes.

**Evidence:** Both V4.2 and V5.0 monitors (launched with `terminal(background=true, command="python -u _gold_monitor_v42.py &")`) showed exit code 0 after ~5 minutes, even though they should run indefinitely. Heartbeat files stopped updating.

## The Fix: nohup + redirect

```bash
nohup python -u /path/to/_gold_monitor_v42.py > /c/path/.v42_monitor.log 2>&1 &
```

Key differences from `terminal(background=true, command="... &")`:
1. **nohup** — ignores SIGHUP (the signal sent when parent shell exits)
2. **Output redirect** — explicit log file, not terminal stdout (which closes)
3. **Launched as one-shot** — terminal tool kicks the command and immediately returns, no managed process tracking

## How to use

In Hermes, use TWO separate background calls (no notify_on_complete — these are long-lived daemons):

```python
# First monitor
terminal(background=true, command="nohup python -u /path/FxPro/_gold_monitor_v42.py > /path/.v42_monitor.log 2>&1 &")

# Second monitor 
terminal(background=true, command="nohup python -u /path/FxPro/_gold_monitor_v50.py > /path/.v50_monitor.log 2>&1 &")
```

## Verification

Monitor heartbeat files should update within 8-20s:

```bash
cat /path/.monitor_v42_heartbeat.json
# {"last_check": "2026-06-01T12:00:10", "pid": 8880}
cat /path/.monitor_v50_heartbeat.json
# {"last_check": "2026-06-01T12:00:10", "pid": 6116}
```

These PIDs won't show in `ps aux` from Git-Bash (different process space). Don't use `ps aux` as a liveness check for nohup'd processes.

## Note: Not needed for Executors

Executors are launched by the user double-clicking `.bat` files (see `references/mt5-migration-1jun.md`). The nohup pattern only applies to monitors, which DO connect to MT5 but don't need terminal GUI access.

## Background processes don't survive reboots

If the machine reboots, all nohup'd processes die. Re-launch after reboot via: kill old → nohup again.
