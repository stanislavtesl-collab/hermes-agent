# FxPro Symbol Name Mapping

On FxPro-MT5 Demo, many common symbols have different names than on other brokers.

## Key Symbols

| Common Name | FxPro Symbol | Type | Min Lot |
|-------------|-------------|------|---------|
| GOLD / XAU/USD | **GOLD** | Commodity/CFD | 0.01 |
| Bitcoin | **BITCOIN** | Crypto/CFD | 0.01 |
| Bitcoin Cash | **BITCOINCASH** | Crypto/CFD | 0.01 |
| EUR/USD | **EURUSD** | Forex | 0.01 |
| US Dow Jones 30 | **#US30** | Index CFD | 0.01 |
| US S&P 500 | **#USSPX500** | Index CFD | 0.01 |
| NASDAQ 100 | **#US100_M26** (June) / **#US100_U26** (Sept) | Futures | 0.01 |
| NASDAQ 100 Spot | **NDX365** | Index CFD | 0.01 |

## How to Discover Symbols

```python
import MetaTrader5 as mt5
mt5.initialize(path=r'C:\Users\Administrator\Desktop\FxPro\terminal64.exe', timeout=30000)

# Search by keyword
for sym in mt5.symbols_get():
    if 'btc' in sym.name.lower():
        print(f"{sym.name}: {sym.description} | minLot:{sym.volume_min}")
```

## Lot Sizes by Asset (Current Session)

| Asset | Lot | Reason |
|-------|-----|--------|
| GOLD | 0.03 | User explicitly increased after winning trades |
| BITCOIN | 0.01 | Smaller lot, crypto volatility |
| EURUSD | 0.01 | Smaller lot |
| #US30 | 0.01 | Smaller lot |
