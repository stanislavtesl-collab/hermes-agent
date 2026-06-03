"""GOLD Market State Analysis — выбор стратегии под рынок"""
import MetaTrader5 as mt5

path = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"
mt5.initialize(path=path, timeout=15000)

# ===== M5 данные =====
m5 = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M5, 0, 30)
m15 = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M15, 0, 20)
h1 = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_H1, 0, 24)

if m5 is None or m15 is None or h1 is None:
    print("DATA_ERROR")
    mt5.shutdown()
    exit()

# M5 — ключевые метрики
c5 = [r[4] for r in m5]
h5 = [r[2] for r in m5]
l5 = [r[3] for r in m5]
v5 = [r[5] for r in m5]
cur = c5[-1]

# EMA20 M5
k = 2/21
ema20_5 = c5[0]
for c in c5: ema20_5 = c*k + ema20_5*(1-k)

# RSI5 на M5
g,l=0,0
for i in range(1,6):
    d=c5[-i]-c5[-i-1]
    if d>0: g+=d
    else: l-=d
rsi5 = 100 - 100/(1 + g/5/(max(l/5, 0.001)))

# RSI14 на M5
g14,l14=0,0
for i in range(1,15):
    d=c5[-i]-c5[-i-1]
    if d>0: g14+=d
    else: l14-=d
rsi14 = 100 - 100/(1 + g14/14/(max(l14/14, 0.001)))

# ATR14 M5
trs=[]
for i in range(1,min(15,len(c5))):
    hl=h5[-i]-l5[-i]
    hcp=abs(h5[-i]-c5[-i-1])
    lcp=abs(l5[-i]-c5[-i-1])
    trs.append(max(hl,hcp,lcp))
atr5 = sum(trs)/len(trs)

# Green/red count
gr5 = sum(1 for i in range(1,11) if c5[-i]>c5[-i-1])
rd5 = 10-gr5

# 20-bar high/low
ph5 = max(h5[-20:])
pl5 = min(l5[-20:])

print(f"Цена: {cur:.2f}")
print(f"EMA20 M5: {ema20_5:.2f} | Дист: {(cur-ema20_5)/0.01:.1f}pts")
print(f"RSI5: {rsi5:.1f} | RSI14: {rsi14:.1f}")
print(f"ATR14 M5: {atr5:.2f}")
print(f"Зел/Кр(10): {gr5}/{rd5}")
print(f"20-bar H/L: {ph5:.2f}/{pl5:.2f}")
print(f"Объём ср5: {sum(v5[-5:])//5} | посл: {v5[-1]}")

# M15 — тренд
c15 = [r[4] for r in m15]
k15 = 2/21
ema20_15 = c15[0]
for c in c15: ema20_15 = c*k15 + ema20_15*(1-k15)

g15,l15=0,0
for i in range(1,15):
    d=c15[-i]-c15[-i-1]
    if d>0: g15+=d
    else: l15-=d
rsi15 = 100 - 100/(1 + g15/14/(max(l15/14, 0.001)))
gr15 = sum(1 for i in range(1,11) if c15[-i]>c15[-i-1])

# MACD M15
ema12=c15[0]; k12=2/13
for c in c15: ema12=c*k12+ema12*(1-k12)
ema26=c15[0]; k26=2/27
for c in c15: ema26=c*k26+ema26*(1-k26)
macd=ema12-ema26
sig=macd; ks=2/10
for _ in range(9): sig=macd*ks+sig*(1-ks)
hist=macd-sig

print(f"\nM15 RSI14: {rsi15:.1f} | EMA20: {ema20_15:.2f}")
print(f"M15 Зел/Кр(10): {gr15}/{10-gr15}")
print(f"M15 MACD: {macd:.2f} | Гист: {hist:.2f}")
print(f"M15 Цена/EMA20: {(c15[-1]-ema20_15)/0.01:.1f}pts")

# H1 — глобальный тренд
c1h = [r[4] for r in h1]
h1h = [r[2] for r in h1]
l1h = [r[3] for r in h1]
k1h = 2/21
ema20_1h = c1h[0]
for c in c1h: ema20_1h = c*k1h + ema20_1h*(1-k1h)

g1h,l1h=0,0
for i in range(1, min(15, len(c1h))):
    d=c1h[-i]-c1h[-i-1]
    if d>0: g1h+=d
    else: l1h-=d
rsi1h = 100 - 100/(1 + g1h/min(14,len(c1h)-1)/(max(l1h/min(14,len(c1h)-1), 0.001)))

gr1h = sum(1 for i in range(1, min(11, len(c1h))) if c1h[-i] > c1h[-i-1])

ph1h = max(h1h[-24:])
pl1h = min(l1h[-24:])

print(f"\nH1 RSI14: {rsi1h:.1f} | EMA20: {ema20_1h:.2f}")
print(f"H1 Цена/EMA20: {(c1h[-1]-ema20_1h)/0.01:.1f}pts")
print(f"H1 24-bar H/L: {ph1h:.2f}/{pl1h:.2f}")
print(f"H1 Зел/Кр(10): {gr1h}/{10-gr1h}")

# ===== Определение режима рынка =====
print(f"\n=== ДИАГНОСТИКА РЕЖИМА ===")

# Тренд H1
h1_trend = "UP" if c1h[-1] > ema20_1h and rsi1h > 50 else "DOWN" if c1h[-1] < ema20_1h and rsi1h < 50 else "SIDEWAYS"
print(f"H1 тренд: {h1_trend}")

# Волатильность
volatility = "HIGH" if atr5 > 8 else "MEDIUM" if atr5 > 5 else "LOW"
print(f"Волатильность M5: {volatility} (ATR={atr5:.2f})")

# Импульс M15
momentum = "BULLISH" if macd > sig and hist > 0 else "BEARISH" if macd < sig and hist < 0 else "NEUTRAL"
print(f"M15 импульс: {momentum}")

# Fatigue
fatigue_buy = gr5 >= 7
fatigue_sell = rd5 >= 7
print(f"M5 усталость BUY: {'ДА' if fatigue_buy else 'НЕТ'} ({gr5}/10 зел)")
print(f"M5 усталость SELL: {'ДА' if fatigue_sell else 'НЕТ'} ({rd5}/10 красных)")

# Рекомендация стратегии
if volatility == "HIGH" and not fatigue_buy and not fatigue_sell:
    rec = "Вариант 2 — Импульсный (высокая вола, свежий рынок)"
elif h1_trend != "SIDEWAYS" and not fatigue_buy and not fatigue_sell:
    rec = "Вариант 1 — Откаты к EMA (чёткий тренд, нет усталости)"
elif fatigue_buy or fatigue_sell:
    rec = "Вариант 1 — Откаты к EMA (рынок разгружается, ждать откат)"
elif volatility == "LOW":
    rec = "Вариант 1 — Откаты к EMA (низкая вола, мелкие движения)"
else:
    rec = "Вариант 1 — Откаты к EMA"

print(f"Рекомендуемая: {rec}")

# BUY/SELL сигнал сейчас
print(f"\n=== СИГНАЛ СЕЙЧАС ===")
# Условия для Варианта 1 (откаты к EMA)
v1_buy = rsi5 < 40 and cur > ema20_5 and (cur-ema20_5)/0.01 < 10 and rd5 >= 4
v1_buy_strong = rsi5 < 30 and cur > ema20_5 and rd5 >= 5

v1_sell = rsi5 > 60 and cur < ema20_5 and (ema20_5-cur)/0.01 < 10 and gr5 >= 4
v1_sell_strong = rsi5 > 70 and cur < ema20_5 and gr5 >= 5

# Условия для Варианта 2 (импульсный)
v2_buy = cur > ph5 and v5[-1] > sum(v5[-5:])//5 * 1.5
v2_sell = cur < pl5 and v5[-1] > sum(v5[-5:])//5 * 1.5

print(f"V1 (Откаты) BUY: {'✅' if v1_buy else '❌'} (RSI5={rsi5:.1f} < 40? {'ДА' if rsi5<40 else 'НЕТ'}, цена у EMA20? {'ДА' if (cur-ema20_5)/0.01 < 10 else 'НЕТ'})")
print(f"V1 (Откаты) BUY strong: {'✅' if v1_buy_strong else '❌'}")
print(f"V1 (Откаты) SELL: {'✅' if v1_sell else '❌'}")
print(f"V2 (Импульс) BUY: {'✅' if v2_buy else '❌'}")
print(f"V2 (Импульс) SELL: {'✅' if v2_sell else '❌'}")

print(f"\nПрорыв 20-bar HIGH: {(ph5-cur)/0.01:.1f}pts вверх")
print(f"Прорыв 20-bar LOW: {(cur-pl5)/0.01:.1f}pts вниз")

mt5.shutdown()
