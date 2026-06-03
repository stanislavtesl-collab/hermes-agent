See separate file: `C:\Users\Administrator\Desktop\FxPro\hermes_trading_system_description.txt` (11.4 KB)

This document was written for the user to feed to another AI (Claude) so it can write a training/instruction document for Hermes Agent. It covers:

1. Who Hermes is — AI assistant, DeepSeek, Telegram interface, Russian language
2. Architecture — Monitor → Signal File → Executor → Daemon (3 processes)
3. 3 strategies — V1 scoring 0-6, V2 breakout, V3 VWAP micro-scalp
4. Alligator gate — hard block for direction
5. Contradict Close — auto-close contradictory trades
6. Partial Close — 50%@100pts with banker's rounding fix
7. Trailing — 80/100/80
8. Technical quirks — MT5, Git-Bash, Python, Windows
9. History of 8 key updates from 29-30 May 2026
10. Resolved problems — zombie PID, partial close bug, missing executor
