#!/usr/bin/env python3
"""
GOLD Monitor v5.0 — M5 EMA10 Crossover
Чистая стратегия:
1. EMA10 crossover на M5
2. H1 тренд-фильтр (SMA20/SMA50, только закрытые бары)
3. M15 EMA20 фильтр (только закрытые бары)
4. TimesFM veto (блок при сильном противоречии >12pts)
5. Germes ML как read-only confluence
Пишет .gold_trade_signal.json — Executor забирает.
"""
import json, time, sys, os, subprocess, warnings

# Перенаправляем stdout в лог-файл
LOG_FILE = "C:/Users/Administrator/Desktop/FxPro/.gold_monitor_v50.log"
if '--foreground' not in sys.argv:
    try:
        log_fd = open(LOG_FILE, 'a', buffering=1)
        sys.stdout = log_fd
        sys.stderr = log_fd
    except Exception as e:
        print(f"Could not redirect stdout to {LOG_FILE}: {e}", file=sys.__stdout__)
from datetime import datetime, timezone
import numpy as np

warnings.filterwarnings('ignore')

sys.path.insert(0, "/c/Program Files/Python312/Lib/site-packages")
import MetaTrader5 as mt5
from hermes_mt5_guard import initialize_and_assert, terminal_path, expected_account

# === Config ===
SIGNAL_FILE = "C:/Users/Administrator/Desktop/FxPro/.gold_trade_signal.json"
HEARTBEAT_FILE = "C:/Users/Administrator/Desktop/FxPro/.gold_heartbeat.json"
MT5_PATH = terminal_path()
MT5_ACCOUNT = expected_account()
SYMBOL = "GOLD"

MONITOR_INTERVAL = 5  # сек (M5 свеча = 300сек, проверяем каждые 5сек)
ANTISPAM_INTERVAL = 60  # сек между сигналами

# === Параметры стратегии ===
SL_PTS = 80
TP_PTS = 600
EMA_PERIOD = 10
TIME_EXIT_BARS = 12  # M5 свечей (1 час)

# === TimesFM (veto only) ===
USE_TIMESFM = True
TFM_THRESHOLD = 12  # pts
TFM_HORIZON = 12
TFM_UPDATE_INTERVAL = 6  # обновляем каждые 6 проверок (30сек)

# === Germes ===
GERMES_CMD = "cd /c/germes && /c/germes/.venv/Scripts/python.exe /c/germes/scripts/germes_signal.py GOLD M15,H1"

_tfm_model = None
_tfm_cache = {}
_tfm_tick = 0
_last_signal_time = 0


def ema(values, period):
    """EMA с произвольным периодом."""
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    result.append(sum(values[:period]) / period)
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def load_timesfm():
    """Ленивая загрузка TimesFM."""
    global _tfm_model
    if _tfm_model is not None:
        return _tfm_model
    try:
        import torch
        torch.set_float32_matmul_precision('high')
        import timesfm
        _tfm_model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            'google/timesfm-2.5-200m-pytorch',
            cache_dir='C:/Users/Administrator/Desktop/FxPro/timesfm_model'
        )
        _tfm_model.compile(timesfm.ForecastConfig(
            max_context=1024, max_horizon=256, normalize_inputs=True,
            use_continuous_quantile_head=True, force_flip_invariance=True,
        ))
        print("[TimesFM] Loaded successfully")
        return _tfm_model
    except Exception as e:
        print(f"[TimesFM] Load failed: {e}")
        return None


def timesfm_veto(action, closes_100):
    """
    TimesFM veto: блокирует сделку ТОЛЬКО если модель СИЛЬНО (>12pts) против.
    Возвращает True если можно торговать, False если блок.
    """
    global _tfm_tick, _tfm_cache, _last_prediction
    _tfm_tick += 1
    # Используем кэш: пересчитываем только каждый TFM_UPDATE_INTERVAL раз
    if _tfm_tick % TFM_UPDATE_INTERVAL != 0 and _tfm_cache:
        pred_dir = _tfm_cache.get('dir')
        pred_chg = _tfm_cache.get('chg', 0)
        ema_dir = 'UP' if action == 'BUY' else 'DOWN'
        if pred_dir and pred_dir != ema_dir and abs(pred_chg) > TFM_THRESHOLD:
            return False  # veto из кэша!
        return True
    
    model = load_timesfm()
    if model is None:
        return True  # без модели — не блокируем
    
    if len(closes_100) < 100:
        return True
    
    try:
        ctx = np.array(closes_100[-100:], dtype=np.float64)
        pt, _ = model.forecast(horizon=TFM_HORIZON, inputs=[ctx])
        last = ctx[-1]
        pred_change = pt[0][-1] - last
        pred_dir = 'UP' if pred_change > 0 else 'DOWN'
        ema_dir = 'UP' if action == 'BUY' else 'DOWN'
        
        _tfm_cache = {'dir': pred_dir, 'chg': pred_change}
        
        # Блок ТОЛЬКО если сильно противоречит
        if pred_dir != ema_dir and abs(pred_change) > TFM_THRESHOLD:
            print(f"  [TimesFM] VETO: {action} blocked (predicts {pred_dir} {pred_change:+.1f}pts)")
            return False
        
        if pred_dir == ema_dir and abs(pred_change) > TFM_THRESHOLD:
            print(f"  [TimesFM] AGREE: {action} confirmed ({pred_dir} {pred_change:+.1f}pts)")
        
        return True
    except Exception as e:
        print(f"  [TimesFM] Error: {e}")
        return True


def get_germes_signal():
    """Germes ML — read-only confluence."""
    try:
        result = subprocess.run(GERMES_CMD, shell=True, capture_output=True, text=True, timeout=20, cwd="/c/germes")
        output = result.stdout.strip()
        start = output.find('{')
        if start == -1:
            return None
        data = json.loads(output[start:])
        if not data.get("ok"):
            return None
        sig = data.get("signals", {})
        m15 = sig.get("M15", {})
        if m15.get("ok"):
            return {
                "direction": m15.get("direction"),
                "p_success": m15.get("p_success", 0),
                "regime": m15.get("regime", 0),
                "tradeable": m15.get("tradeable_hint", False),
            }
        return None
    except Exception as e:
        return None


def get_h1_trend():
    """H1 тренд из ЗАКРЫТЫХ баров (SMA20/SMA50)."""
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 1, 60)
        if rates is None or len(rates) < 50:
            return "SIDEWAYS"
        closes = [float(r[4]) for r in rates]
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50
        if sma20 > sma50 + 2:
            return "BULLISH"
        elif sma20 < sma50 - 2:
            return "BEARISH"
        return "SIDEWAYS"
    except:
        return "SIDEWAYS"


def get_m15_trend():
    """M15 тренд из ЗАКРЫТЫХ баров (EMA20)."""
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 1, 25)
        if rates is None or len(rates) < 25:
            return "SIDEWAYS"
        closes = [float(r[4]) for r in rates]
        e = ema(closes, 20)
        if e[-1] is None:
            return "SIDEWAYS"
        last_close = closes[-1]
        return "BULLISH" if last_close > e[-1] else "BEARISH"
    except:
        return "SIDEWAYS"


def heartbeat():
    hb = {"last_check": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()}
    with open(HEARTBEAT_FILE, "w") as f:
        json.dump(hb, f)


def check_signal():
    """Проверяет условия входа: EMA10 crossover + H1 trend + M15 EMA20 + TimesFM veto + Germes."""
    global _last_signal_time
    now = time.time()
    
    # Anti-spam
    if now - _last_signal_time < ANTISPAM_INTERVAL:
        return None, None
    
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 30)
        if rates is None or len(rates) < EMA_PERIOD + 1:
            return None, None
        
        closes = [float(r[4]) for r in rates]
        ema_vals = ema(closes, EMA_PERIOD)
        if len(ema_vals) < 2 or ema_vals[-1] is None or ema_vals[-2] is None:
            return None, None
        
        prev_close, curr_close = closes[-2], closes[-1]
        prev_ema, curr_ema = ema_vals[-2], ema_vals[-1]
        
        action = None
        reason = None
        
        # EMA10 crossover
        if prev_close <= prev_ema and curr_close > curr_ema:
            action, reason = "BUY", "EMA10 crossover UP"
        elif prev_close >= prev_ema and curr_close < curr_ema:
            action, reason = "SELL", "EMA10 crossover DOWN"
        
        if not action:
            return None, None
        
        # H1 trend filter
        h1_t = get_h1_trend()
        if h1_t == "BEARISH" and action == "BUY":
            return None, "BLOCKED: H1 BEARISH for BUY"
        if h1_t == "BULLISH" and action == "SELL":
            return None, "BLOCKED: H1 BULLISH for SELL"
        
        # M15 EMA20 filter
        m15_t = get_m15_trend()
        if m15_t == "BEARISH" and action == "BUY":
            return None, "BLOCKED: M15 BEARISH for BUY"
        if m15_t == "BULLISH" and action == "SELL":
            return None, "BLOCKED: M15 BULLISH for SELL"
        
        # TimesFM veto
        if USE_TIMESFM:
            if not timesfm_veto(action, closes):
                return None, "BLOCKED: TimesFM veto"
        
        # Germes — read-only confluence (логируем, не блокируем)
        try:
            germes = get_germes_signal()
            if germes and germes.get('direction'):
                gdir = germes['direction']
                g_ok = (action == "BUY" and gdir == "LONG") or (action == "SELL" and gdir == "SHORT")
                reason += f" | Germes={'agree' if g_ok else 'against'}"
        except:
            pass
        
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            return None, None
        
        price = tick.ask if action == "BUY" else tick.bid
        sl = price - SL_PTS * 0.01 if action == "BUY" else price + SL_PTS * 0.01
        tp = price + TP_PTS * 0.01 if action == "BUY" else price - TP_PTS * 0.01
        
        _last_signal_time = now
        
        return {
            "action": action,
            "price": round(price, 2),
            "sl": round(sl, 2),
            "tp": round(tp, 2),
            "reason": reason,
            "lot": 0.03,
            "magic": 50500,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "time_exit_bars": TIME_EXIT_BARS,
        }, None
    
    except Exception as e:
        print(f"[check_signal] Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    print("=" * 55)
    print("GOLD Monitor v5.0 — M5 EMA10 Crossover")
    print("=" * 55)
    print(f"  SL={SL_PTS}pts | TP={TP_PTS}pts | EMA{EMA_PERIOD}")
    print(f"  H1 trend filter: ON")
    print(f"  M15 EMA20 filter: ON")
    print(f"  TimesFM veto: {'ON' if USE_TIMESFM else 'OFF'}")
    print(f"  Signal file: {SIGNAL_FILE}")
    print()
    
    if not mt5.initialize(path=MT5_PATH, timeout=15000):
        print(f"MT5 init failed: {mt5.last_error()}")
        sys.exit(1)
    acc = mt5.account_info()
    if not acc or int(acc.login) != MT5_ACCOUNT:
        print(f"MT5 account mismatch: got={acc.login if acc else 'None'} expected={MT5_ACCOUNT}")
        mt5.shutdown()
        sys.exit(1)
    mt5.symbol_select(SYMBOL, True)
    print(f"MT5 connected: {acc.login}, Balance: {acc.balance}")
    
    last_h1 = None
    last_m15 = None
    
    while True:
        try:
            heartbeat()
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick is None:
                print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] No tick, reconnecting...")
                time.sleep(1)
                continue
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            
            # H1 trend (печатаем при смене)
            h1_t = get_h1_trend()
            if h1_t != last_h1:
                print(f"[{ts}] H1: {h1_t}")
                last_h1 = h1_t
            
            m15_t = get_m15_trend()
            if m15_t != last_m15:
                print(f"[{ts}] M15: {m15_t}")
                last_m15 = m15_t
            
            signal, blocked = check_signal()
            
            if signal:
                signal_key = f"{signal.get('entry_type', '')}_{signal.get('price', 0)}_{signal.get('action', '')}"
                if signal_key == getattr(check_signal, '_last_signal_key', ''):
                    print(f"[{ts}] DUPLICATE: {signal['action']} @ {signal['price']} (already sent)")
                else:
                    check_signal._last_signal_key = signal_key
                    signal["trend_h1"] = get_h1_trend()
                    signal["trend_m15"] = get_m15_trend()
                    with open(SIGNAL_FILE, "w") as f:
                        json.dump(signal, f)
                    print(f"[{ts}] >>> SIGNAL {signal['action']} @ {signal['price']} | {signal['reason']} | SL={signal['sl']} TP={signal['tp']}")
            elif blocked:
                print(f"[{ts}] {blocked} | {SYMBOL} @ {tick.bid:.2f}")
            else:
                print(f"[{ts}] No signal | {SYMBOL} @ {tick.bid:.2f} | H1={h1_t} M15={m15_t}")
        
        except Exception as e:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[{ts}] Error: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(MONITOR_INTERVAL)
