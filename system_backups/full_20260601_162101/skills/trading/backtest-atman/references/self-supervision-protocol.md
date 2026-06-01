# Self-Supervision Protocol for Overnight Optimization Runs

When the user grants "full freedom" overnight (or for extended periods), follow this protocol to avoid getting stuck.

## Pre-Flight Checklist

Before starting any long optimization:

1. **Estimate runtime:**
   - Small grid (<500 configs): ~2-3 min
   - Medium grid (500-3000 configs): ~5-15 min
   - Large grid (>3000): 15-60+ min
   
2. **Precompute indicators ONCE** — never inside the grid loop. If indicators/ATR/swings are recomputed per-config, multiply runtime by 100x.

3. **Kill any leftover processes** — stale PID 6396-like processes from old sessions can keep log files locked.

## Self-Check Every 10-15 Minutes

Use `process(action="poll")` to check the running process. If:

- **Process running but no output file for >2× estimated time** — kill and debug
- **Process exited with error** — read the error, fix, restart (don't wait for user)
- **Process exited with code 0** — read results, proceed to next task

## Common Pitfalls to Self-Catch

| Symptom | Cause | Fix |
|---------|-------|-----|
| Grid runs 30+ min with no output | Indicators recomputed per-config | Precompute indicators once in parent scope |
| `too many values to unpack` | Hours tuple stored as string | `hs_int, he_int = int(hs), int(he)` or keep as tuple in config |
| `operands could not be broadcast together` | Kaufman ER slice-vectorization | Use element-wise loop for change[] and noise[] |
| `FileNotFoundError` for data file | File was cleaned up between sessions | Redownload data (MT5 takes 30-60s) |
| Process exits instantly code 1 | Python syntax/lint error | Read traceback and fix immediately |
| Process running >40 min for <3000 configs | Each iteration calls slow O(n) indicator calc | Must restructure to precompute |

## Log File Monitoring

If the job writes to a log file (`.log`, `.txt`), tail it to check progress:

```bash
tail -5 /path/to/job.log
```

Key signs of progress:
- "X/Y configs done" or "Config 500/1440"
- "Best PF = " changing upward
- Timestamps advancing every 5-60s

## If Truly Stuck for >20 Minutes

1. Kill the process
2. Check what was produced so far (partial results file?)
3. If partial results exist → read them, document, move on
4. If nothing produced → simplify the grid, restart
5. If same failure repeats 2x → write a simpler standalone version

## After Completion

1. Read the top-5 results
2. Write a one-paragraph summary per result
3. If optimization found something useful, update the skill
4. Proceed to the next item on the plan

## Key Principle

**Never block waiting for a long process without running parallel work.** While one grid search runs, prepare the next item (download data, write the next script, review existing results). Parallelism is the only way to get through 6-8 hours of autonomous work.
