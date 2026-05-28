# Hermes Agent — AI-Powered Trading Bot

**Hermes Agent** connects Telegram, DeepSeek AI, MetaTrader 5, and Twelve Data
into a unified trading assistant. Users interact via Telegram chat; the AI agent
fetches market data, runs technical analysis, and responds with trading insights.

## Architecture

```
Telegram  →  Hermes Gateway  →  DeepSeek API (LLM)
                             →  MT5 (MetaTrader 5, FxPro Demo)
                             →  Twelve Data (market quotes)
                             →  analyze_pipe.py (RSI, MACD, EMA, BB)
```

## Project Structure

```
hermes-agent/
├── config.yaml              # Hermes Gateway configuration
├── .env.example             # Environment variables template
├── .gitignore
├── Hermes_Gateway.cmd       # Windows Scheduled Task startup script
├── README.md
├── src/
│   ├── indicators.py        # RSI, MACD, EMA, Bollinger Bands (numpy)
│   ├── twelvedata_query.py  # Twelve Data REST API client
│   ├── mt5_query.py         # MetaTrader 5 terminal client
│   └── analyze_pipe.py      # Technical analysis pipeline
└── skills/
    └── trading/
        └── SKILL.md         # AI agent skill definition
```

## Requirements

| Component | Version |
|-----------|---------|
| Python | 3.11+ |
| MetaTrader 5 | Terminal installed + logged in |
| numpy | Latest |
| MetaTrader5 | `pip install MetaTrader5` (Windows only) |

## Quick Start

### 1. Clone
```bash
git clone https://github.com/stanislavtesl-collab/hermes-agent.git
cd hermes-agent
```

### 2. Environment
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS

pip install numpy MetaTrader5
```

### 3. Configure
```bash
copy .env.example .env
# Edit .env — add your API keys:
#   DEEPSEEK_API_KEY=sk-...
#   TELEGRAM_BOT_TOKEN=...
#   TWELVEDATA_API_KEY=...
```

### 4. Run Analysis (standalone test)
```bash
python src/analyze_pipe.py EURUSD twelvedata 1h 100
```

### 5. Run Gateway
```bash
python -m hermes_cli.main gateway run
```

## API Keys

| Service | Key Env Var | Free Tier |
|---------|------------|-----------|
| DeepSeek | `DEEPSEEK_API_KEY` | 500 req/day |
| Telegram | `TELEGRAM_BOT_TOKEN` | Unlimited |
| Twelve Data | `TWELVEDATA_API_KEY` | 800 req/day |
| MT5 | None (auto-detect) | Depends on broker |

Get free keys:
- DeepSeek: https://platform.deepseek.com
- Twelve Data: https://twelvedata.com/apikey
- Telegram Bot: https://t.me/BotFather

## Deployment

The system runs on **Windows Server 2019** with:
- MetaTrader 5 terminal always open (logged into FxPro Demo)
- Scheduled Task `Hermes_Gateway` triggers `Hermes_Gateway.cmd` at boot
- Gateway runs via `pythonw.exe` (no console window, background process)

## Security Notes

- `.env` is git-ignored — never commit real API keys
- `GATEWAY_ALLOW_ALL_USERS=true` is **development only** — restrict in production
- API keys have daily rate limits; monitor usage to avoid lockout
- Consider moving API keys to Windows Credential Manager or environment variables

## License

Proprietary. All rights reserved.
