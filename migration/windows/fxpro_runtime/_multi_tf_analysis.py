#!/usr/bin/env python3
"""Multi-TF technical analysis + intraday correlation for XAUUSD, BTC, ETH"""
import numpy as np
import pandas as pd
import json, warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

# === LOAD intraday data via yfinance multi-TF ===
# yfinance only supports 1d/1wk/1mo for daily, but we can get 5m/15m/30m/1h/4h for recent period
# 5m: max 60 days
# 15m: max 60 days
# 1h: max 730 days
# 4h: same as 1h

import yfinance as yf

end = datetime.now()

def fetch_intraday(ticker, interval, period='60d'):
    """Fetch intraday data with proper interval"""
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False, multi_level_index=False)
        if df.empty:
            # Try with explicit start/end
            s = end - timedelta(days=30)
            df = yf.download(ticker, start=s.strftime('%Y-%m-%d'), end=end.strftime('%Y-%m-%d'),
                           interval=interval, auto_adjust=True, progress=False, multi_level_index=False)
        return df
    except:
        return pd.DataFrame()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

def calc_bb(series, period=20):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    bb_width = ((sma + 2*std) - (sma - 2*std)) / sma * 100
    upper = sma + 2*std
    lower = sma - 2*std
    return upper.iloc[-1], lower.iloc[-1], bb_width.iloc[-1], sma.iloc[-1]

def calc_ema(series, period):
    return series.ewm(span=period).mean().iloc[-1]

def calc_atr(df, period=14):
    if len(df) < period + 1:
        return None
    high, low, close = df['High'], df['Low'], df['Close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    return atr

ticker_map = {'XAUUSD': 'GC=F', 'BTC': 'BTC-USD', 'ETH': 'ETH-USD'}
intervals = [('5m', '5d'), ('15m', '15d'), ('1h', '30d'), ('4h', '60d')]

results = {}
for asset_name, ticker in ticker_map.items():
    results[asset_name] = {}
    for interval, period in intervals:
        df = fetch_intraday(ticker, interval, period)
        if df.empty or len(df) < 20:
            print(f"  {asset_name} {interval}: no data")
            continue
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        vol = df['Volume'] if 'Volume' in df.columns else None
        
        rsi_val = float(calc_rsi(close).iloc[-1])
        macd_line, signal_line = calc_macd(close)
        macd_val = float(macd_line)
        macd_signal = float(signal_line)
        macd_hist = float(macd_line - signal_line)
        
        upper_bb, lower_bb, bb_width, bb_sma = calc_bb(close)
        upper_bb_pct = float(((close.iloc[-1] - lower_bb) / (upper_bb - lower_bb)) * 100) if upper_bb != lower_bb else 50.0
        
        ema20 = float(calc_ema(close, 20))
        ema50 = float(calc_ema(close, 50)) if len(close) >= 50 else None
        ema200 = float(calc_ema(close, 200)) if len(close) >= 200 else None
        
        atr_val = float(calc_atr(df)) if calc_atr(df) else None
        
        # Price position vs EMAs
        cur_price = float(close.iloc[-1])
        above_ema20 = cur_price > ema20
        above_ema50 = cur_price > ema50 if ema50 else None
        
        # Green candle percentage (last 20)
        recent = df.tail(20)
        green_pct = float((recent['Close'] > recent['Open']).mean() * 100) if len(recent) >= 20 else None
        
        # Volume comparison vs 20-period avg
        vol_ratio = float(vol.iloc[-1] / vol.tail(20).mean()) if vol is not None and len(vol) >= 20 else None
        
        # Last 5 candles direction
        last_5 = close.tail(5).values
        dir_5 = np.sign(np.diff(last_5)).tolist() if len(last_5) >= 2 else []
        
        macd_bullish = macd_hist > 0
        
        results[asset_name][interval] = {
            'price': cur_price,
            'rsi14': round(rsi_val, 1),
            'macd_hist': round(macd_hist, 2),
            'macd_bullish': macd_bullish,
            'bb_width_pct': round(bb_width, 2),
            'bb_position_pct': round(upper_bb_pct, 1),
            'ema20': round(ema20, 1),
            'ema50': round(ema50, 1) if ema50 else None,
            'above_ema20': above_ema20,
            'above_ema50': above_ema50,
            'green_pct': round(green_pct, 1) if green_pct else None,
            'vol_ratio': round(vol_ratio, 2) if vol_ratio else None,
            'atr': round(atr_val, 2) if atr_val else None,
            'last_5_direction': dir_5,
        }
        print(f"  {asset_name} {interval}: RSI={rsi_val:.1f}, MACD={'Bull' if macd_bullish else 'Bear'}, BB={bb_width:.2f}%")

# D1 data for completeness
for asset_name, ticker in ticker_map.items():
    df = yf.download(ticker, period='6mo', interval='1d', auto_adjust=True, progress=False, multi_level_index=False)
    if df.empty or len(df) < 20:
        continue
    close = df['Close']
    rsi_val = float(calc_rsi(close).iloc[-1])
    macd_line, signal_line = calc_macd(close)
    macd_hist = float(macd_line - signal_line)
    macd_bullish = macd_hist > 0
    ema20 = float(calc_ema(close, 20))
    ema50 = float(calc_ema(close, 50)) if len(close) >= 50 else None
    ema200 = float(calc_ema(close, 200)) if len(close) >= 200 else None
    cur_price = float(close.iloc[-1])
    green_pct = float((df.tail(20)['Close'] > df.tail(20)['Open']).mean() * 100)
    
    results[asset_name]['D1'] = {
        'price': cur_price,
        'rsi14': round(rsi_val, 1),
        'macd_hist': round(macd_hist, 2),
        'macd_bullish': macd_bullish,
        'ema20': round(ema20, 1),
        'ema50': round(ema50, 1) if ema50 else None,
        'above_ema20': cur_price > ema20,
        'above_ema50': cur_price > ema50 if ema50 else None,
        'green_pct': round(green_pct, 1),
    }
    print(f"  {asset_name} D1: RSI={rsi_val:.1f}, MACD={'Bull' if macd_bullish else 'Bear'}")

# === Intraday correlation across TFs ===
print(f"\n=== INTRADAY CORRELATION ===")
# Use hourly data for cross-correlation
hourly_data = {}
for asset_name, ticker in ticker_map.items():
    df = fetch_intraday(ticker, '1h', '30d')
    if not df.empty and len(df) >= 30:
        hourly_data[asset_name] = df['Close']

if len(hourly_data) >= 3:
    hourly_close = pd.DataFrame(hourly_data)
    hourly_ret = hourly_close.pct_change().dropna()
    h_corr = hourly_ret.corr()
    print("H1 correlation:")
    print(h_corr.round(4))
    
    # M15 correlation
    m15_data = {}
    for asset_name, ticker in ticker_map.items():
        df = fetch_intraday(ticker, '15m', '7d')
        if not df.empty and len(df) >= 30:
            m15_data[asset_name] = df['Close']
    if len(m15_data) >= 3:
        m15_close = pd.DataFrame(m15_data)
        m15_ret = m15_close.pct_change().dropna()
        m15_corr = m15_ret.corr()
        print("\nM15 correlation:")
        print(m15_corr.round(4))

# === OUTPUT JSON ===
output = {
    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
    'results': results,
}

with open('/c/Users/Administrator/Desktop/FxPro/multi_tf_analysis.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)

print(f"\n=== SAVED TO multi_tf_analysis.json ===")
