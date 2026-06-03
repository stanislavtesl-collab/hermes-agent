"""Quick GOLD position status check.
Connects to FxPro Demo, shows balance, current price, and open position details."""
import MetaTrader5 as mt5
import time, json
from datetime import datetime

path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
symbol = "GOLD"

try: mt5.shutdown()
except: pass
time.sleep(0.3)

if not mt5.initialize(path=path, timeout=15000):
    print(json.dumps({"error": str(mt5.last_error())}))
    exit()

mt5.symbol_select(symbol, True)
acc = mt5.account_info()
si = mt5.symbol_info_tick(symbol)
positions = mt5.positions_get(symbol=symbol)

now = datetime.now().strftime("%H:%M:%S")
print(f"Time: {now}")
print(f"Balance: ${acc.balance:.2f}")
print(f"GOLD: Bid={si.bid} Ask={si.ask}")

if positions and len(positions) > 0:
    for pos in positions:
        ptype = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
        entry = pos.price_open
        current = pos.price_current
        profit = round(pos.profit, 2)
        sl = pos.sl
        tp = pos.tp
        ticket = pos.ticket
        
        if ptype == "BUY":
            points = round((current - entry) / 0.01, 1)
        else:
            points = round((entry - current) / 0.01, 1)
        
        print(f"Position #{ticket}: {ptype} @ {entry}")
        print(f"  Current: {current} | P&L: ${profit:.2f} ({points}pts)")
        print(f"  SL: {sl} | TP: {tp}")
else:
    print("No open GOLD positions")

mt5.shutdown()
