#!/usr/bin/env python3
"""
|GOLD Monitor v4.5 — Multi-TF Scalper (M1+M5+H1)
|Четыре точки входа:
|1. Пробой EMA20 (breakout) — на импульсе через EMA20
|2. Откат к EMA20 (pullback) — цена ушла от EMA20 и вернулась
|3. Пробой M5 High/Low — сильное движение через M5 канал
|4. H1 Retest — касание H1 уровня предыдущего часа
|+ H1 тренд-фильтр
|+ ATR-адаптивный SL (не 800pts фикс!)
|Данные через MT5 (прямые)
|Пишет .gold_trade_signal.json — Executor забирает.
"""
import json, time, sys, os, subprocess
from datetime import datetime, timezone

sys.path.insert(0, "/c/Program Files/Python312/Lib/site-packages")
import MetaTrader5 as mt5
from hermes_mt5_guard import initialize_and_assert, terminal_path, expected_account

# --- Config ---
SIGNAL_FILE = "C:/Users/Administrator/Desktop/FxPro/.gold_trade_signal.json"
HEARTBEAT_FILE = "C:/Users/Administrator/Desktop/FxPro/.gold_heartbeat.json"
MT5_PATH = terminal_path()
MT5_ACCOUNT = expected_account()
SYMBOL = "GOLD"
NO_TRADE_INTERVAL = 8
IN_TRADE_INTERVAL = 1
LAST_SIGNAL_TIME = 0  # anti-spam: timestamp последнего сигнала
MIN_SIGNAL_INTERVAL = 30  # мин. сек между сигналами одного типа
LOT = 0.03

# --- Filters ---
MAX_MOVE_POINTS = 15   # защита от входа в конце движения
MIN_VOLUME_RATIO = 1.0  # для breakout
MIN_VOLUME_RATIO_PULLBACK = 0.7  # для отката — объём меньше критичен

# --- Germes path ---
GERMES_CMD = "cd /c/germes && /c/germes/.venv/Scripts/python.exe /c/germes/scripts/germes_signal.py GOLD M15,H1"


def ema(values, period):
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    result.append(sum(values[:period]) / period)
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def get_germes_signal():
    """Запрос Germes ML. Возвращает (direction, p_success) или None при ошибке."""
    try:
        result = subprocess.run(GERMES_CMD, shell=True, capture_output=True, text=True, timeout=20, cwd="/c/germes")
        output = result.stdout.strip()
        # Ищем JSON в выводе
        start = output.find('{')
        if start == -1:
            return None
        data = json.loads(output[start:])
        if not data.get("ok"):
            return None
        sig = data.get("signals", {})
        # Берём M15 как основной для скальпинга
        m15 = sig.get("M15", {})
        if m15.get("ok"):
            return {
                "direction": m15.get("direction"),
                "p_success": m15.get("p_success", 0),
                "regime": m15.get("regime", 0),
                "tradeable": m15.get("tradeable_hint", False),
                "source": "germes_m15"
            }
        return None
    except Exception as e:
        return None


def check_signal():
    """
    Проверяем все 3 типа входов на M1+M5.
    Возвращает (signal_dict, blocked_reason) или (None, None/blocked)
    """
    # --- Данные M1 ---
    rates_m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 60)
    if rates_m1 is None or len(rates_m1) < 25:
        return None, None

    closes = [r[4] for r in rates_m1]
    highs_m1 = [r[2] for r in rates_m1]
    lows_m1 = [r[3] for r in rates_m1]
    volumes = [r[5] for r in rates_m1]
    last_c = closes[-1]
    prev_c = closes[-2]

    # --- Данные M5 ---
    rates_m5 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 20)
    m5_high = max(r[2] for r in rates_m5[-6:]) if rates_m5 is not None and len(rates_m5) >= 6 else None
    m5_low = min(r[3] for r in rates_m5[-6:]) if rates_m5 is not None and len(rates_m5) >= 6 else None
    m5_prev_high = max(r[2] for r in rates_m5[-12:-6]) if rates_m5 is not None and len(rates_m5) >= 12 else None
    m5_prev_low = min(r[3] for r in rates_m5[-12:-6]) if rates_m5 is not None and len(rates_m5) >= 12 else None

    # --- EMA20 на M1 ---
    e20 = ema(closes, 20)
    last_e20 = e20[-1]
    prev_e20 = e20[-2]
    if None in (last_e20, prev_e20):
        return None, None

    # --- Базовые расчёты ---
    avg_vol = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else volumes[-1]
    last_vol = volumes[-1]

    # --- Счётчик движения ---
    candles_back = 3
    if len(closes) >= candles_back + 1:
        price_change_3 = abs(closes[-1] - closes[-1 - candles_back])
        dir_3 = "UP" if closes[-1] > closes[-1 - candles_back] else "DOWN"
    else:
        price_change_3 = 0
        dir_3 = "NONE"

    # --- Germes confluence ---
    germes = get_germes_signal()

    def build_signal(action, price_in, reason, entry_type):
        """Собрать словарь сигнала."""
        sig = {
            "action": action,
            "symbol": SYMBOL,
            "price": round(price_in, 2),
            "lot": LOT,
            "sl": None,
            "tp": None,
            "trailing_offset": 30,
            "trailing_step": 10,
            "partial_close_pts": 15,
            "partial_close_fraction": 0.3,
            "reason": reason,
            "entry_type": entry_type,
            "trend_h1": None,
            "germes": germes,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "source": "monitor_v44",
            "data_source": "MT5_ONLY"
        }
        return sig

    action = None
    reason = ""
    entry_type = ""
    filters_triggered = []

    # ====================================================================
    # ТИП 1: BREAKOUT — пробой EMA20 M1
    # ====================================================================
    # SELL breakout: цена была выше EMA20, пробила вниз
    if prev_c > prev_e20 and last_c <= last_e20:
        if dir_3 == "DOWN" and price_change_3 >= MAX_MOVE_POINTS:
            filters_triggered.append(f"BO_S: move3={price_change_3:.1f}pts >= {MAX_MOVE_POINTS}")
        elif last_vol < avg_vol * MIN_VOLUME_RATIO:
            filters_triggered.append(f"BO_S: vol={last_vol:.0f} < avg*{MIN_VOLUME_RATIO}={avg_vol*MIN_VOLUME_RATIO:.0f}")
        else:
            action = "SELL"
            reason = f"[BO] M1 EMA20 break DOWN ({prev_c:.1f}->{last_c:.1f}, EMA20={last_e20:.1f}, VOL={last_vol})"
            entry_type = "breakout"
    elif prev_c > prev_e20 and last_c < prev_e20:
        if dir_3 == "DOWN" and price_change_3 >= MAX_MOVE_POINTS:
            filters_triggered.append(f"BO_S: move3={price_change_3:.1f}pts >= {MAX_MOVE_POINTS}")
        elif last_vol < avg_vol * MIN_VOLUME_RATIO:
            filters_triggered.append(f"BO_S: vol={last_vol:.0f} < avg*{MIN_VOLUME_RATIO}={avg_vol*MIN_VOLUME_RATIO:.0f}")
        else:
            action = "SELL"
            reason = f"[BO] M1 below prev EMA20 ({prev_c:.1f}->{last_c:.1f}, VOL={last_vol})"
            entry_type = "breakout"

    # BUY breakout: цена была ниже EMA20, пробила вверх
    if not action and prev_c < prev_e20 and last_c >= last_e20:
        if dir_3 == "UP" and price_change_3 >= MAX_MOVE_POINTS:
            filters_triggered.append(f"BO_B: move3={price_change_3:.1f}pts >= {MAX_MOVE_POINTS}")
        elif last_vol < avg_vol * MIN_VOLUME_RATIO:
            filters_triggered.append(f"BO_B: vol={last_vol:.0f} < avg*{MIN_VOLUME_RATIO}={avg_vol*MIN_VOLUME_RATIO:.0f}")
        else:
            action = "BUY"
            reason = f"[BO] M1 EMA20 break UP ({prev_c:.1f}->{last_c:.1f}, EMA20={last_e20:.1f}, VOL={last_vol})"
            entry_type = "breakout"
    elif not action and prev_c < prev_e20 and last_c > prev_e20:
        if dir_3 == "UP" and price_change_3 >= MAX_MOVE_POINTS:
            filters_triggered.append(f"BO_B: move3={price_change_3:.1f}pts >= {MAX_MOVE_POINTS}")
        elif last_vol < avg_vol * MIN_VOLUME_RATIO:
            filters_triggered.append(f"BO_B: vol={last_vol:.0f} < avg*{MIN_VOLUME_RATIO}={avg_vol*MIN_VOLUME_RATIO:.0f}")
        else:
            action = "BUY"
            reason = f"[BO] M1 above prev EMA20 ({prev_c:.1f}->{last_c:.1f}, VOL={last_vol})"
            entry_type = "breakout"

    # ====================================================================
    # ТИП 2: PULLBACK — откат к EMA20 M1
    # ====================================================================
    if not action and len(closes) >= 20:
        # Ищем: цена была далеко от EMA20 (>=8pts), вернулась в зону EMA20 (+/- 2pts)
        dist_to_ema = abs(last_c - last_e20)

        # Расчёт расстояния 5 свечей назад
        c_5_back = closes[-5] if len(closes) >= 5 else closes[0]
        dist_5_back = abs(c_5_back - ema(closes, 20)[-5]) if len(closes) >= 20 and ema(closes, 20)[-5] is not None else 0
        was_far = dist_5_back >= 8  # 5 свечей назад было далеко от EMA

        # Если сейчас близко к EMA (дист < 3pts), а раньше было далеко — это откат
        if dist_to_ema < 3 and was_far:
            # Определяем направление: с какой стороны подошли к EMA
            if last_c < last_e20 - 0.5:
                # Цена ниже EMA — подтянулась снизу, возможный BUY
                if last_vol >= avg_vol * MIN_VOLUME_RATIO_PULLBACK:
                    action = "BUY"
                    reason = f"[PB] Pullback to EMA20 from below (dist_now={dist_to_ema:.1f}, was_dist={dist_5_back:.1f}, VOL={last_vol})"
                    entry_type = "pullback"
            elif last_c > last_e20 + 0.5:
                # Цена выше EMA — подтянулась сверху, возможный SELL
                if last_vol >= avg_vol * MIN_VOLUME_RATIO_PULLBACK:
                    action = "SELL"
                    reason = f"[PB] Pullback to EMA20 from above (dist_now={dist_to_ema:.1f}, was_dist={dist_5_back:.1f}, VOL={last_vol})"
                    entry_type = "pullback"

    # ====================================================================
    # ТИП 3: M5 BREAKOUT — пробой зоны M5 High/Low
    # ====================================================================
    if not action and m5_high is not None and m5_low is not None and m5_prev_high is not None and m5_prev_low is not None:
        # BUY: цена пробила M5 High последних 6 свечей
        if last_c > m5_high and prev_c <= m5_high:
            if last_vol >= avg_vol * MIN_VOLUME_RATIO:
                action = "BUY"
                reason = f"[M5] Break above M5 high ({m5_high:.1f}->{last_c:.1f}, prev_high={m5_prev_high:.1f}, VOL={last_vol})"
                entry_type = "m5_breakout"
        # SELL: цена пробила M5 Low последних 6 свечей
        elif last_c < m5_low and prev_c >= m5_low:
            if last_vol >= avg_vol * MIN_VOLUME_RATIO:
                action = "SELL"
                reason = f"[M5] Break below M5 low ({m5_low:.1f}->{last_c:.1f}, prev_low={m5_prev_low:.1f}, VOL={last_vol})"
                entry_type = "m5_breakout"

    # ====================================================================
    # ТИП 4: H1 RE-TEST — касание H1 High/Low предыдущего часа и отскок
    # ====================================================================
    if not action:
        try:
            h1_rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 3)
            if h1_rates is not None and len(h1_rates) >= 2:
                # Предыдущий H1 бар
                prev_h1 = h1_rates[-2]
                h1_high = prev_h1[2]  # High предыдущего часа
                h1_low = prev_h1[3]   # Low предыдущего часа
                h1_close = prev_h1[4]
                curr_h1 = h1_rates[-1]
                curr_h1_high = curr_h1[1]  # Open текущего = высокий
                curr_h1_low = curr_h1[3]   # Low текущего

                # BUY: цена коснулась H1 Low предыдущего часа и отскочила
                if abs(last_c - h1_low) <= 3 and prev_c < h1_low + 1 and last_c > h1_low:
                    action = "BUY"
                    reason = f"[RT] H1 low retest ({h1_low:.1f}), bounce to {last_c:.1f}, VOL={last_vol})"
                    entry_type = "h1_retest"
                # SELL: цена коснулась H1 High предыдущего часа и отскочила вниз
                elif abs(last_c - h1_high) <= 3 and prev_c > h1_high - 1 and last_c < h1_high:
                    action = "SELL"
                    reason = f"[RT] H1 high retest ({h1_high:.1f}), bounce down to {last_c:.1f}, VOL={last_vol})"
                    entry_type = "h1_retest"
        except:
            pass

    # --- ТИП 5 исключён (round_bounce): генерировал 79.8% шумовых сигналов,
    # 90.5% которых достигали и +40pts и -60pts одновременно.
    # GOLD на M1 касается круглых уровней на каждом баре — реального отскока нет.
    # ---

    # --- ФИНАЛ: формируем сигнал ---
    if action:
        # Anti-spam: не чаще 1 сигнала в MIN_SIGNAL_INTERVAL сек
        now = time.time()
        if now - LAST_SIGNAL_TIME < MIN_SIGNAL_INTERVAL:
            return None, f"ANTISPAM: {action} @ {last_c:.2f} (last was {now - LAST_SIGNAL_TIME:.0f}s ago)"

        sig = build_signal(action, last_c, reason, entry_type)

        # Добавляем Germes информацию в reason если есть
        if germes and germes.get("p_success", 0) >= 0.50:
            g_dir = germes.get("direction", "?")
            g_p = germes.get("p_success", 0) * 100
            g_regime = germes.get("regime", "?")
            sig["reason"] += f" | GERMES={g_dir} p={g_p:.0f}% regime={g_regime}"
            sig["germes"] = germes

        with open(SIGNAL_FILE, "w") as f:
            json.dump(sig, f)
        LAST_SIGNAL_TIME = time.time()
        return sig, None

    if filters_triggered:
        return None, f"BLOCKED: {', '.join(filters_triggered)}"

    return None, None


def heartbeat():
    hb = {"last_check": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()}
    with open(HEARTBEAT_FILE, "w") as f:
        json.dump(hb, f)


def get_h1_trend(debug=False):
    """Получаем H1 тренд через SMA20/SMA50"""
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 60)
    except:
        return "SIDEWAYS"
    if rates is None or (hasattr(rates, 'size') and rates.size == 0) or len(rates) < 50:
        if debug:
            print(f"[H1] Not enough data: {len(rates) if rates else 0}")
        return "SIDEWAYS"
    sma20 = sum(r[4] for r in rates[-20:]) / 20
    sma50 = sum(r[4] for r in rates[-50:]) / 50
    if sma20 > sma50 + 2:
        return "BULLISH"
    elif sma20 < sma50 - 2:
        return "BEARISH"
    return "SIDEWAYS"


if __name__ == "__main__":
    print(f"[Monitor v4.4] Starting, PID={os.getpid()}")
    print(f"[Monitor v4.4] Entry types: breakout(EMA20) | pullback(EMA20) | m5_breakout(M5 range)")
    print(f"[Monitor v4.4]                  retest(H1 high/low) | round_bounce(.00/.20/.50/.80)")
    print(f"[Monitor v4.4] Confluence: Germes ML (read-only, p_success>50%)")
    print(f"[Monitor v4.4] Filters: move3<{MAX_MOVE_POINTS}pts, vol>={MIN_VOLUME_RATIO}x(breakout)/{MIN_VOLUME_RATIO_PULLBACK}x(pullback)")
    print(f"[Monitor v4.4] H1 trend filter: active (pass-through)")
    print(f"[Monitor v4.4] Signal file: {SIGNAL_FILE}")
    print("-" * 55)

    if not mt5.initialize(path=MT5_PATH, timeout=15000):
        print(f"MT5 init failed: {mt5.last_error()}")
        sys.exit(1)
    acc = mt5.account_info()
    if not acc or int(acc.login) != MT5_ACCOUNT:
        print(f"MT5 account mismatch: got={acc.login if acc else 'None'} expected={MT5_ACCOUNT}")
        mt5.shutdown()
        sys.exit(1)
    mt5.symbol_select(SYMBOL, True)
    print(f"MT5 connected, account: {acc.login}")

    check_interval = NO_TRADE_INTERVAL
    last_h1_trend = None

    while True:
        heartbeat()
        try:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            tick = mt5.symbol_info_tick(SYMBOL)
            if tick is None:
                print(f"[{ts}] Warning: no tick for {SYMBOL}; reconnecting/backoff")
                try:
                    mt5.shutdown()
                    initialize_and_assert(timeout=7000)
                except Exception as e:
                    print(f"[{ts}] MT5 pinned reconnect failed: {e}")
                time.sleep(POLL_SECONDS)
                continue
            positions = mt5.positions_get(symbol=SYMBOL) or []
            in_trade = len(positions) > 0
            check_interval = IN_TRADE_INTERVAL if in_trade else NO_TRADE_INTERVAL

            # H1 trend (refresh every ~5 min)
            h1_trend = get_h1_trend()
            if h1_trend != last_h1_trend:
                print(f"[{ts}] H1 trend: {h1_trend}")
                last_h1_trend = h1_trend

            signal, blocked = check_signal()
            if signal:
                signal["trend_h1"] = h1_trend
                sig_dir = "BUY" if signal["action"] == "BUY" else "SELL"
                # H1 filter: SELL on BULLISH blocked, BUY on BEARISH blocked
                if (sig_dir == "SELL" and h1_trend == "BULLISH") or \
                   (sig_dir == "BUY" and h1_trend == "BEARISH"):
                    print(f"[{ts}] BLOCKED {sig_dir} @ {signal['price']} | H1={h1_trend} | {signal['reason']}")
                else:
                    print(f"[{ts}] >>> SIGNAL {signal['action']} @ {signal['price']} | {signal['reason']} | H1={h1_trend}")
                    signal["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                    with open(SIGNAL_FILE, "w") as f:
                        json.dump(signal, f)
            elif blocked:
                print(f"[{ts}] {blocked} | {SYMBOL} @ {tick.bid:.2f}")
            else:
                print(f"[{ts}] No signal | {SYMBOL} @ {tick.bid:.2f} | H1={h1_trend}")

        except Exception as e:
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[{ts}] Error: {e}")

        time.sleep(check_interval)
