# Trading Skill — Hermes Agent

## Purpose
This skill teaches the Hermes Gateway agent how to use the trading toolchain:
- **analyze_pipe.py** — full technical analysis pipeline
- **mt5_query.py** — MetaTrader 5 data (price, account, positions, bars)
- **twelvedata_query.py** — Twelve Data market data (quote, bars)

## Tool Usage

### analyze_pipe.py — Technical Analysis
```bash
python src/analyze_pipe.py EURUSD mt5 H1 100
```
- **symbol**: MT5 symbol (EURUSD) or Twelve Data symbol (EUR/USD)
- **source**: `mt5` or `twelvedata`
- **timeframe**: `M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1`, `W1`, `MN1`
- **bars**: number of bars (default 100)

Returns JSON with:
- `latest`: RSI, MACD, EMA9, EMA21, Bollinger Bands, price
- `signals`: derived buy/sell signals (overbought/oversold, bullish/bearish)

### mt5_query.py — MetaTrader 5
```
account_info()      → balance, equity, margin, etc.
open_positions()    → list of open trades
current_price()     → bid/ask for a symbol
bars()              → historical OHLCV numpy array
```

### twelvedata_query.py — Twelve Data
```
quote()             → real-time quote
time_series()       → historical OHLCV bars
```

## Constraints (STRICT)

**FORBIDDEN operations:**
- `pip install` — do NOT install any packages
- `from twelvedata import TDC` — use the local twelvedata_query.py only
- `curl` — use Python scripts, not shell commands
- `jq` — use Python JSON parsing, not jq

## Typical Workflow

1. User asks about a symbol → run `analyze_pipe.py` with appropriate source
2. If MT5 source fails → fall back to `twelvedata`
3. Present signals clearly: RSI state, MACD direction, EMA crossover, BB position
4. For account questions → use `mt5_query.account_info()` and `open_positions()`
