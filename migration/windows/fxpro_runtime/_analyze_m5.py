#!/usr/bin/env python3
"""
Анализ GOLD на M5: характеристики, паттерны, лучшие настройки
Выясняем: какой SL, TP, трейлинг работают на M5
"""
import csv
from datetime import datetime
from collections import Counter

m1_rows = []
with open('_gold_m1_14d.csv') as f:
    for r in csv.DictReader(f):
        m1_rows.append({
            'time': datetime.fromisoformat(r['time']),
            'open': float(r['open']), 'high': float(r['high']),
            'low': float(r['low']), 'close': float(r['close']),
            'volume': int(float(r['volume']))
        })

h1_rows = []
with open('_gold_h1_14d.csv') as f:
    for r in csv.DictReader(f):
        h1_rows.append({
            'time': datetime.fromisoformat(r['time']),
            'open': float(r['open']), 'high': float(r['high']),
            'low': float(r['low']), 'close': float(r['close']),
            'volume': int(float(r['volume']))
        })

# Собираем M5 бары из M1
m5_bars = []
current = None
for r in m1_rows:
    if current is None:
        current = {'time': r['time'], 'open': r['open'], 'high': r['high'], 
                   'low': r['low'], 'close': r['close'], 'volume': r['volume']}
    elif (r['time'] - current['time']).total_seconds() < 300:
        current['high'] = max(current['high'], r['high'])
        current['low'] = min(current['low'], r['low'])
        current['close'] = r['close']
        current['volume'] += r['volume']
    else:
        m5_bars.append(current)
        current = {'time': r['time'], 'open': r['open'], 'high': r['high'],
                   'low': r['low'], 'close': r['close'], 'volume': r['volume']}
if current:
    m5_bars.append(current)

print(f"M5 баров: {len(m5_bars)}")
print(f"H1 баров: {len(h1_rows)}")

# === 1. ХАРАКТЕРИСТИКИ M5 ===
ranges = []
bodies = []
volumes = []
for bar in m5_bars:
    r = bar['high'] - bar['low']
    body = abs(bar['close'] - bar['open'])
    ranges.append(r / 0.01)  # в pts
    bodies.append(body / 0.01)
    volumes.append(bar['volume'])

avg_range = sum(ranges) / len(ranges)
avg_body = sum(bodies) / len(bodies)
avg_vol = sum(volumes) / len(volumes)
print(f"\n📊 ХАРАКТЕРИСТИКИ M5:")
print(f"  Средний range: {avg_range:.1f}pts")
print(f"  Среднее тело: {avg_body:.1f}pts")
print(f"  Средний объём: {avg_vol:.0f}")
print(f"  Медианный range: {sorted(ranges)[len(ranges)//2]:.1f}pts")
print(f"  90% баров имеют range < {sorted(ranges)[int(len(ranges)*0.9)]:.1f}pts")
print(f"  95% баров имеют range < {sorted(ranges)[int(len(ranges)*0.95)]:.1f}pts")

# === 2. ДВИЖЕНИЕ ЗА N СВЕЧЕЙ ===
print(f"\n📊 ДВИЖЕНИЕ ЗА N СВЕЧЕЙ M5:")
for n in [3, 6, 12, 24, 48]:  # 15мин, 30мин, 1ч, 2ч, 4ч
    moves = []
    for i in range(n, len(m5_bars)):
        move = abs(m5_bars[i]['close'] - m5_bars[i-n]['close']) / 0.01
        moves.append(move)
    avg_m = sum(moves) / len(moves)
    med_m = sorted(moves)[len(moves)//2]
    p90 = sorted(moves)[int(len(moves)*0.9)]
    print(f"  {n} свечей ({n*5}мин): avg={avg_m:.0f}pts, med={med_m:.0f}pts, 90%={p90:.0f}pts")

# === 3. EMA20 на M5: как часто цена её пересекает ===
def ema(vals, p):
    if len(vals) < p: return [None]*len(vals)
    k = 2/(p+1); r = [None]*(p-1)
    r.append(sum(vals[:p])/p)
    for v in vals[p:]: r.append(v*k + r[-1]*(1-k))
    return r

closes = [b['close'] for b in m5_bars]
e20 = ema(closes, 20)

crosses = 0
above = None
for i in range(20, len(m5_bars)):
    if e20[i] is None: continue
    pos = 'ABOVE' if m5_bars[i]['close'] > e20[i] else 'BELOW'
    if above is not None and pos != above:
        crosses += 1
    above = pos

test_bars = sum(1 for b in m5_bars if datetime(2026,5,26) <= b['time'] <= datetime(2026,6,3))
print(f"\n📊 EMA20 CROSSES на M5:")
print(f"  Пересечений за 14 дней: {crosses}")
print(f"  В тестовом окне: ~{crosses * test_bars // len(m5_bars)}")
print(f"  Среднее между пересечениями: {len(m5_bars)//crosses if crosses else 0} свечей")

# === 4. КАК ЧАСТО ЦЕНА ПРОХОДИТ N PTS ПОСЛЕ ПЕРЕСЕЧЕНИЯ EMA20 ===
print(f"\n📊 ДВИЖЕНИЕ ПОСЛЕ ПЕРЕСЕЧЕНИЯ EMA20 (breakout):")
test_start = datetime(2026,5,26)
test_end = datetime(2026,6,3)

for sl_pts in [30, 50, 80, 120, 200]:
    wins = 0; losses = 0; total_pts = 0
    for i in range(20, len(m5_bars)-1):
        bar = m5_bars[i]; ts = bar['time']
        if ts < test_start or ts > test_end: continue
        if e20[i] is None or e20[i-1] is None: continue
        
        # Breakout: пересечение EMA20
        prev_above = m5_bars[i-1]['close'] > e20[i-1]
        now_above = bar['close'] > e20[i]
        
        if prev_above != now_above:
            # Вошли на open следующей
            if i+1 >= len(m5_bars): break
            entry = m5_bars[i+1]['open']
            action = 'BUY' if now_above else 'SELL'
            
            # Смотрим следующие 12 свечей (1 час)
            max_profit = 0; max_loss = 0
            for j in range(i+2, min(i+2+12, len(m5_bars))):
                jbar = m5_bars[j]
                if action == 'BUY':
                    profit_pts = (jbar['high'] - entry) / 0.01
                    loss_pts = (entry - jbar['low']) / 0.01
                else:
                    profit_pts = (entry - jbar['low']) / 0.01
                    loss_pts = (jbar['high'] - entry) / 0.01
                max_profit = max(max_profit, profit_pts)
                max_loss = max(max_loss, loss_pts)
            
            if max_loss >= sl_pts and max_profit >= sl_pts:
                # Кто первый?
                pass  # сложно понять без временной шкалы
            
            if max_loss >= sl_pts:
                losses += 1
                total_pts -= sl_pts
            elif max_profit >= sl_pts:
                wins += 1
                total_pts += sl_pts
    
    if wins + losses > 0:
        wr = wins / (wins+losses) * 100
        print(f"  SL={sl_pts:3d}pts: {wins+losses:4d} сделок, WR={wr:5.1f}%, PnL={total_pts:+5d}pts")

# === 5. АНАЛИЗ: ТРЕНДОВОСТЬ M5 ===
print(f"\n📊 ТРЕНДОВОСТЬ M5 (свечи одного направления подряд):")
max_streak = 0; current_streak = 1; direction = 0
streaks = []
for i in range(1, len(m5_bars)):
    d = 1 if m5_bars[i]['close'] > m5_bars[i-1]['close'] else (-1 if m5_bars[i]['close'] < m5_bars[i-1]['close'] else 0)
    if d == direction and d != 0:
        current_streak += 1
    else:
        if direction != 0:
            streaks.append(current_streak)
        direction = d
        current_streak = 1
    max_streak = max(max_streak, current_streak)

print(f"  Максимальная серия: {max_streak} свечей")
print(f"  Средняя серия: {sum(streaks)/len(streaks):.1f} свечей")
print(f"  Серий >= 3: {sum(1 for s in streaks if s >= 3)}")
print(f"  Серий >= 6: {sum(1 for s in streaks if s >= 6)} (30+ минут тренда)")
print(f"  Серий >= 12: {sum(1 for s in streaks if s >= 12)} (1+ час тренда)")

# === 6. ВОЛАТИЛЬНОСТЬ ПО ЧАСАМ ДНЯ ===
print(f"\n📊 ВОЛАТИЛЬНОСТЬ ПО ЧАСАМ (GMT):")
hour_ranges = {}
for bar in m5_bars:
    h = bar['time'].hour
    if h not in hour_ranges:
        hour_ranges[h] = {'sum': 0, 'count': 0}
    hour_ranges[h]['sum'] += bar['high'] - bar['low']
    hour_ranges[h]['count'] += 1

for h in sorted(hour_ranges.keys()):
    avg_r = hour_ranges[h]['sum'] / hour_ranges[h]['count'] / 0.01
    bars = hour_ranges[h]['count']
    print(f"  {h:2d}:00 — {avg_r:.0f}pts avg range ({bars} баров)")

# === 7. КОРРЕЛЯЦИЯ ОБЪЁМА И ДВИЖЕНИЯ ===
print(f"\n📊 ОБЪЁМ VS ДВИЖЕНИЕ:")
vols_sorted = sorted(volumes)
top10_vol = vols_sorted[-len(vols_sorted)//10:]  # top 10% по объёму
bottom50_vol = vols_sorted[:len(vols_sorted)//2]  # bottom 50%
# Средний range для high-volume баров
high_vol_ranges = []
low_vol_ranges = []
for i, bar in enumerate(m5_bars):
    r = bar['high'] - bar['low']
    if i < len(volumes) and volumes[i] >= top10_vol[0]:
        high_vol_ranges.append(r/0.01)
    elif volumes[i] <= bottom50_vol[-1]:
        low_vol_ranges.append(r/0.01)

print(f"  High-volume бары (top10%): avg range={sum(high_vol_ranges)/len(high_vol_ranges):.1f}pts" if high_vol_ranges else "")
print(f"  Low-volume бары (bottom50%): avg range={sum(low_vol_ranges)/len(low_vol_ranges):.1f}pts" if low_vol_ranges else "")
