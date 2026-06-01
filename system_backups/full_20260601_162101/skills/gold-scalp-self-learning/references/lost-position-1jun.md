# Lost Position & SL Bug — 1 June 2026

## Timeline

**15:56** — Last logged trade open (BUY #237678047 @ $4,457.86). Heartbeat updates until ~15:57.

**16:05** — User reports seeing a position on the chart. I check `positions_get(symbol='GOLD')` → **None** (empty). I tell user "позиций нет".

**16:07** — User insists "выпутывайся из той сделки, которую ты потерял". I check again — `positions_get(ticket=237687234)` → **Found! SELL @ $4,458.26, PnL=-$13.35.**

**Why batch query returned None:** MT5 shared memory was busy with executor process. `positions_get(symbol='GOLD')` returns None when shared memory contention occurs. Ticket-specific `positions_get(ticket=N)` bypasses this and reads the position directly.

**SL was wrong (executor bug):** SL was set to $4,513.03 instead of $4,470.26 (800pts). That's **50.29pts** above entry — completely ineffective. Root cause: executor's `order_send()` used `sl=` with a numpy-influenced calculation.

**16:08** — Close SELL #237687234 with -$13.98.

**16:09** — New SELL #237689842 was opened by executor (racing condition — opened same cycle as close). SL even worse: $4,513.03 for entry $4,462.74.

**16:10** — Close #237689842 with -$3.03.

## Diagnosis

1. **Executor died silently after 15:56** — heartbeat kept updating for ~3 more minutes (Exception handler still cycled), but no new trades or trail updates.

2. **Batch positions_get() is unreliable** under shared memory contention. Always fall back to ticket-specific or loop all positions.

3. **SL bug persisted** even after safe_val() patch — means not all code paths were covered.

## Root Causes

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| `positions_get(symbol='GOLD')` = None | MT5 shared memory contention | Check ticket-specific as fallback |
| SL = 50.29pts instead of 8.00pts | `SL_DISTANCE * 0.01` calc with numpy array | Verify SL before order_send() |
| Executor alive but not trading | safe_val() not applied to try_average() | Apply safe_val() everywhere |

## Lessons for Tooling

1. When checking for open positions, **never trust** `positions_get(symbol='X')` alone. If it returns None and balance implies there should be positions → try `positions_get()` without filter or iterate tickets.

2. After any executor restart, clear the log file (`> .universal_executor.log`) so old errors don't confuse diagnostics.

3. **Always verify SL before and after order_send()** — read it back with `positions_get(ticket=N)[0].sl` to confirm it's reasonable.
