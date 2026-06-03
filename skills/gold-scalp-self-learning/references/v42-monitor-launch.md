# V4.2 Multi-TF Scalper Monitor — Launch Notes (1 June 2026)

## Architecture (v42 vs old triple pattern)

Old: Monitor → Signal → Executor (opens) → Daemon v9 (trailing + partial close)
V4.2: Monitor → Signal → **Executor v4.2 (opens + trailing + partial close)** — executor is self-contained

Executor v4.2 (`_gold_executor_v42.py`) handles everything post-open:
- SL/TP calculation (dynamic from M1 15-bar swing)
- Trailing stop (offset=30, step=10)
- Partial close (30%@+15pts) — tracked via `.v42_trail.json`
- H1 trend contradiction check (closes position if trade goes against H1 EMA50 trend)

No daemon v9 needed — the executor IS the daemon for V4.2.

## Deploy from Hermes (agent tools)

When deploying V4.2 FROM the Hermes agent's `terminal` tool (not from Windows command line), use this exact sequence:

```bash
# 1. First verify MT5 connectivity
cd "C:/Users/Administrator/Desktop/FxPro"
python -c "
import MetaTrader5 as mt5
path = r'C:\Users\Administrator\Desktop\FxPro\terminal64.exe'
ok = mt5.initialize(path=path, timeout=30000)
print('MT5 OK:', ok)
if ok: mt5.shutdown()
"

# 2. Kill all stale processes + locks
taskkill /F /IM python.exe 2>/dev/null
rm -f ".gold_executor_v42.lock" ".gold_executor.lock" ".gold_trade_signal.json"

# 3. Start monitor via PowerShell (not terminal background!)
powershell -Command "Start-Process -WindowStyle Hidden -FilePath python -ArgumentList '-u', 'C:\Users\Administrator\Desktop\FxPro\_gold_monitor_v42.py' -WorkingDirectory 'C:\Users\Administrator\Desktop\FxPro'"

# 4. Start executor via PowerShell
powershell -Command "Start-Process -WindowStyle Hidden -FilePath python -ArgumentList '-u', 'C:\Users\Administrator\Desktop\FxPro\_gold_executor_v42.py' -WorkingDirectory 'C:\Users\Administrator\Desktop\FxPro'"

# 5. Verify
cat .monitor_v42_heartbeat.json
tail -5 .gold_executor_v42.log
```

⚠️ **CRITICAL (1 June 2026):** `terminal(background=true)` from Hermes spawns a subprocess that may not inherit the same environment as a normal Python process. Even though a foreground test via `python -c "..."` connects to MT5 fine, the same executor script started in background mode will hang on `mt5.initialize()` indefinitely. Always use PowerShell `Start-Process` from the terminal tool instead.

**The `_v42_manager.py` wrapper (subprocess.Popen inside Python) also failed** — same environment limitation. Direct PowerShell Start-Process is the only reliable method on this Windows/Git-Bash setup.

## VERIFICATION protocol (after deployment)

```bash
# Check monitor heartbeat (written every 8s)
cat .monitor_v42_heartbeat.json
# → {"last_check": "2026-06-01T08:31:02", "pid": 8768}

# Check executor log
tail -5 .gold_executor_v42.log
# → 🚀 EXECUTOR v4.2 STARTED (new entry with current time)

# Identify which IPython processes are which (via PowerShell)
powershell -Command "Get-Process python* | Select-Object Id, @{N='Cmd';E={$_.CommandLine}} | Format-Table -AutoSize -Wrap"
```

## Key differences from monitor_v3

Executor v4.2 requires MT5 running. If MT5 is closed:
- `mt5.initialize()` returns False
- Executor will log "MT5 init failed, retry in 10s" every cycle
- Start MT5 manually from desktop: `C:\Users\Administrator\Desktop\FxPro\terminal64.exe`

After MT5 starts, the executor auto-connects within 10s on the retry cycle.

## V4.2 Signal format

```json
{
  "action": "SELL",
  "symbol": "GOLD",
  "price": 4494.78,
  "lot": 0.03,
  "sl": null,
  "tp": null,
  "trailing_offset": 30,
  "trailing_step": 10,
  "partial_close_pts": 15,
  "partial_close_fraction": 0.3,
  "reason": "M1 пробой EMA20 вниз (4501.1→4494.8)",
  "trend_h1": "DOWN",
  "source": "monitor_v42"
}
```

Executor v4.2 reads this signal, calculates SL from M1 swing, opens trade, then writes `.v42_trail.json` for ongoing trailing management. When signal action is "SELL" or "BUY" (not "V1_SELL"/"V1_BUY" from monitor_v3).

## Key differences from monitor_v3

| Aspect | monitor_v3 | monitor_v42 |
|--------|-----------|-------------|
| Entry timeframe | M5 | **M1** |
| Trend filter | M15 Alligator | **H1 EMA50 ± ATR×0.2** |
| Entry trigger | Scoring (0-6) with RSI/EMA/candle count | **M1 EMA20 breakout + volume > avg** |
| RSI filter | Yes (hard gate) | **No RSI filter** |
| Partial close | 30%@150pts (daemon) | **30%@+15pts (in signal)** |
| Trailing | MANAGEMENT 50/60/50 | **offset=30, step=10** |
| Direction | Alligator hard gate | **H1 trend filter only** |
| Trades/week | ~45-63 | ~651 |
| WR | ~57% | ~70.5% |

## Partial close on V4.2

CRITICAL: Unlike V3.2 where partial close destroys PnL, on V4.2 it's **essential** (+$174 → +$357, 2× boost). The difference:
- V3.2 = 2 trades/day, each $30 avg win → partial steals $15 from winners  
- V4.2 = 130 trades/day, $1.90 avg win → partial captures $0.57 on EVERY trade while trail catches extended moves

Do NOT disable partial_close_pts or partial_close_fraction on V4.2.

## Known issues

- **Git Bash (MINGW64) background mode doesn't show stdout.** Don't rely on terminal output to confirm liveliness — use heartbeat file or PowerShell.
- **Duplicate processes:** Bash can spawn multiple Python processes for the same script. Always check `.monitor_v42_heartbeat.json` PID vs `tasklist`.
- **Heartbeat PID mismatch:** The heartbeat is written by the actual python process, while `terminal(background=true)` returns the bash wrapper PID. They will differ. Trust the heartbeat file.
- **API 401 on Twelve Data:** If subagent parallel tests fire simultaneously — free tier limits. Monitor handles this gracefully with try/except.
* **Executor needs MT5 running:** Without MT5, executor logs retry every 10s but does nothing.
* **Hermes tool-call limit may interrupt deployment mid-sequence:** The `terminal(background=true)` killed after tool-call limit may actually keep the target PID alive, but then a second launch finds the lock file. Always do `taskkill` + `rm -f *.lock` before relaunching.
* **Heartbeat PID differs from Hermes-reported PID:** The Hermes `terminal(background=true)` returns the PID of the bash wrapper (/bin/bash), not the actual Python process. The heartbeat file contains the real Python PID. Don't be confused when they differ.
* **bat file method for executor:** On this Windows setup, the ONLY reliable method to run MT5-connected executor is a `.bat` file that the user double-clicks. `_boot_executor_v42.py` does MT5 pre-check, then `exec(open('_gold_executor_v42.py').read())`. User keeps the console window open. All other methods (terminal background, PowerShell Start-Process, cmd start /B, _v42_manager.py subprocess) fail to connect to MT5 from Git-Bash subprocess.
