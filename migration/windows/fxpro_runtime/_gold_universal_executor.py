#!/usr/bin/env python3
"""
GOLD Universal Executor v4 — Умное управление сделками
+ ATR-адаптивный трейлинг
+ Partial Close 30%@+50pts
+ Scalp-выход при затухании объёма
+ Усреднение при откате в пользу тренда (1 раз)
+ Второй лот на сильном тренде
+ Адаптивный выбор стратегии под ситуацию
"""
import MetaTrader5 as mt5
import json
import time
import os
import sys
from datetime import datetime, timezone
import numpy as np
from hermes_mt5_guard import initialize_and_assert, terminal_path, expected_account

# === CONFIG ===
SYMBOL = "GOLD"
MAGIC_SCALP = 123462
MAGIC_M15 = 123463
LOT = 0.03
CHECK_INTERVAL = 3  # сек

# === HARD-CODED MT5 FXPRO ACCOUNT ===
MT5_TERMINAL_PATH = terminal_path()
MT5_ACCOUNT = expected_account()

# === STATE FILES ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIL_FILE = os.path.join(BASE_DIR, ".universal_trail.json")
HEARTBEAT_FILE = os.path.join(BASE_DIR, ".gold_executor_heartbeat.json")
SIGNAL_FILE_V42 = os.path.join(BASE_DIR, ".gold_trade_signal.json")
SIGNAL_FILE_V50 = os.path.join(BASE_DIR, ".gold_trade_signal_v50.json")
SIGNAL_FILE_M15 = os.path.join(BASE_DIR, ".gold_trade_signal_m15.json")
LOG_FILE = os.path.join(BASE_DIR, ".gold_executor_events.log")
EXIT_PLAN_FILE = os.path.join(BASE_DIR, ".gold_exit_plan.json")

# === EXIT STRATEGY MODES ===
# Адаптивно выбирается в зависимости от рынка
EXIT_AGGRESSIVE = "aggressive"      # высокое ATR: быстрый трейлинг + scalp
EXIT_NORMAL = "normal"              # среднее ATR: partial + трейлинг
EXIT_CONSERVATIVE = "conservative"  # низкое ATR: ждём движения, wide трейлинг


def safe_val(val, default=0.0):
    """Extract scalar from numpy array or return value directly."""
    if isinstance(val, np.ndarray):
        return float(val.item()) if val.size > 0 else default
    return float(val) if val is not None else default


def write_heartbeat():
    try:
        with open(HEARTBEAT_FILE, "w") as f:
            json.dump({"timestamp": time.time(), "pid": os.getpid(), "status": "running"}, f)
    except:
        pass


def log_event(event, data=None):
    try:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"{ts}|{event}"
        if data:
            entry += f"|{json.dumps(data)}"
        entry += "\n"
        with open(LOG_FILE, "a") as f:
            f.write(entry)
    except:
        pass


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# === MT5 INIT ===
def init_mt5():
    if not mt5.initialize(path=MT5_TERMINAL_PATH):
        log(f"MT5 init failed: {mt5.last_error()}")
        return False
    acc = mt5.account_info()
    if acc is None:
        log(f"No account info: {mt5.last_error()}")
        return False
    if acc.login == MT5_ACCOUNT:
        log(f"MT5 connected. Login: {acc.login}, Balance: {acc.balance}")
        log_event("MT5_INIT", {"login": acc.login, "balance": acc.balance})
        return True
    log(f"Wrong account: {acc.login}; expected={MT5_ACCOUNT}. Refusing passwordless login/fallback.")
    log_event("MT5_ACCOUNT_MISMATCH", {"login": acc.login, "expected": MT5_ACCOUNT, "terminal": MT5_TERMINAL_PATH})
    return False


# === POSITION ===
def get_position(ticket):
    pos = mt5.positions_get(ticket=ticket)
    return pos[0] if pos else None

def get_all_positions():
    positions = mt5.positions_get()
    if not positions:
        return []
    return [p for p in positions if p.magic in (MAGIC_SCALP, MAGIC_M15)]


# === ATR ===
def get_atr(tf=mt5.TIMEFRAME_H1, period=14):
    """Рассчитать ATR в пунктах (pts)."""
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, period + 1)
        if rates is None or len(rates) < period + 1:
            return 10.0  # default
        trs = []
        for i in range(1, len(rates)):
            h = float(rates[i][2])
            l = float(rates[i][3])
            pc = float(rates[i-1][4])
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr / 0.01)  # переводим в пункты
        atr_pts = sum(trs) / len(trs)
        return round(atr_pts, 1)
    except:
        return 10.0


def get_h1_trend():
    """H1 тренд."""
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 60)
        if rates is None or len(rates) < 50:
            return "SIDEWAYS"
        sma20 = sum(r[4] for r in rates[-20:]) / 20
        sma50 = sum(r[4] for r in rates[-50:]) / 50
        if sma20 > sma50 + 2:
            return "BULLISH"
        elif sma20 < sma50 - 2:
            return "BEARISH"
        return "SIDEWAYS"
    except:
        return "SIDEWAYS"


def get_volume_state():
    """Оценить состояние объёма: 'high', 'normal', 'low'."""
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 21)
        if rates is None or len(rates) < 21:
            return "normal"
        vols = [r[5] for r in rates]
        avg = sum(vols[:-1]) / 20
        last = vols[-1]
        if last > avg * 1.5:
            return "high"
        elif last < avg * 0.5:
            return "low"
        return "normal"
    except:
        return "normal"


def get_m1_momentum():
    """Оценить импульс M1: 'strong', 'weak', 'fading', 'reversal'."""
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 10)
        if rates is None or len(rates) < 10:
            return "normal"
        closes = [float(r[4]) for r in rates]
        opens = [float(r[1]) for r in rates]
        vols = [int(r[5]) for r in rates]
        
        # Определяем направление последних 3 свечей
        dirs = []
        for i in range(-3, 0):
            dirs.append("GREEN" if closes[i] >= opens[i] else "RED")
        
        green_count = dirs.count("GREEN")
        red_count = dirs.count("RED")
        
        # Если последняя свеча зелёная и до этого было 2+ красных — это разворот/коррекция
        # В таком случае НЕ закрываем scalp — может быть сильное движение
        if dirs[-1] == "GREEN" and red_count >= 2:
            return "reversal"  # новый тип — коррекция закончена, потенциал роста
        
        # Если объём падает последние 3 свечи И направление не меняется
        if len(vols) >= 3 and vols[-1] < vols[-3] * 0.6:
            if red_count >= 2 or green_count >= 2:
                return "fading"
        
        # Если объём растёт и цена движется
        if vols[-1] > sum(vols[:-1]) / max(len(vols)-1, 1) * 1.3:
            return "strong"
        return "normal"
    except:
        return "normal"


# === ВЫБОР СТРАТЕГИИ ВЫХОДА ===
def choose_exit_strategy(atr_pts, h1_trend):
    """
    Выбирает стратегию выхода в зависимости от рынка.
    Возвращает dict с настройками.
    """
    if atr_pts >= 12:
        # ВЫСОКАЯ ВОЛАТИЛЬНОСТЬ — быстрый трейлинг, агрессивно
        mode = EXIT_AGGRESSIVE
        strategy = {
            "mode": mode,
            "description": "ATR≥12, высокая волатильность",
            # Partial close: раньше, меньше доля
            "partial_pts": 30,       # закрыть часть при +30pts
            "partial_fraction": 0.25,  # 25% позиции
            # Трейлинг: быстрый
            "trail_activation": 50,    # активация при +50pts
            "trail_offset": 30,        # отступ 30pts
            "trail_step": 20,
            # Scalp-выход: при затухании на +10pts
            "scalp_close": True,
            "scalp_min_profit": 8,
            # Второй лот
            "second_entry": True,
            "second_entry_retrace": 15,  # откат на 15pts для входа
            "second_lot": 0.02,
        }
    elif atr_pts >= 6:
        # СРЕДНЯЯ ВОЛАТИЛЬНОСТЬ — стандарт
        mode = EXIT_NORMAL
        strategy = {
            "mode": mode,
            "description": f"ATR={atr_pts}, средняя волатильность",
            "partial_pts": 50,
            "partial_fraction": 0.30,  # 30% при +50pts
            "trail_activation": 80,
            "trail_offset": 50,
            "trail_step": 30,
            "scalp_close": True,
            "scalp_min_profit": 12,
            "second_entry": False,  # на среднем ATR не надо второй лот
            "second_entry_retrace": 0,
            "second_lot": 0.0,
        }
    else:
        # НИЗКАЯ ВОЛАТИЛЬНОСТЬ — широкий трейлинг, ждём движения
        mode = EXIT_CONSERVATIVE
        strategy = {
            "mode": mode,
            "description": f"ATR={atr_pts}, низкая волатильность",
            "partial_pts": 40,
            "partial_fraction": 0.25,
            "trail_activation": 60,
            "trail_offset": 40,
            "trail_step": 25,
            "scalp_close": False,  # не закрываем — ждём движения
            "scalp_min_profit": 0,
            "second_entry": False,
            "second_entry_retrace": 0,
            "second_lot": 0.0,
        }

    # Усиление при сильном тренде
    if h1_trend in ("BULLISH", "BEARISH"):
        strategy["trail_activation"] = max(strategy["trail_activation"] - 10, 30)
        strategy["partial_pts"] = max(strategy["partial_pts"] - 10, 20)

    return strategy


# === ОТКРЫТИЕ СДЕЛКИ ===
def open_trade(signal, source):
    action = signal.get("action", "").upper()
    if action not in ("BUY", "SELL"):
        return False

    h1_trend = signal.get("trend_h1", "SIDEWAYS")
    if action == "BUY" and h1_trend == "BEARISH":
        log(f"H1 BEARISH blocks BUY ({source})")
        return False
    if action == "SELL" and h1_trend == "BULLISH":
        log(f"H1 BULLISH blocks SELL ({source})")
        return False

    positions = get_all_positions()
    if positions:
        for p in positions:
            p_type = "BUY" if p.type == 0 else "SELL"
            if p_type != action:
                log(f"Opposite position exists, skipping {source} {action}")
                return False

    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        return False

    current_price = tick.bid if action == "SELL" else tick.ask

    # SL: ATR-адаптивный (ATR×1.5, минимум 15pts, максимум 50pts)
    atr_sl = get_atr()
    sl_pts = max(15, min(50, atr_sl * 1.5))
    SL_DISTANCE = sl_pts * 0.01  # pts в цену GOLD
    if action == "BUY":
        sl = current_price - SL_DISTANCE
    else:
        sl = current_price + SL_DISTANCE

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": current_price,
        "sl": sl,
        "tp": 0.0,
        "deviation": 20,
        "magic": MAGIC_SCALP,
        "comment": source,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result and result.retcode == 10009:
        log(f"OPEN {action} #{result.order} @ {current_price:.2f} SL={sl:.2f} ({source})")

        # ATR для выбора стратегии
        atr = get_atr()
        h1_t = get_h1_trend()
        strategy = choose_exit_strategy(atr, h1_t)
        log(f"  Exit strategy: {strategy['mode']} ({strategy['description']})")

        trail_data = {
            "ticket": result.order,
            "action": action,
            "entry_price": current_price,
            "source": source,
            "h1_trend": h1_t,
            "strategy": strategy,
            "partial_done": False,
            "second_entry_done": False,
            "scalp_check_pts": strategy.get("scalp_min_profit", 0),
            "scalp_checked": False,
        }
        with open(TRAIL_FILE, "w") as f:
            json.dump(trail_data, f)

        schedule_validation(result.order, current_price, action)
        log_event("OPEN", {"ticket": result.order, "action": action, "price": round(current_price, 2), "sl": round(sl, 2), "source": source, "strategy": strategy['mode']})
        return True
    else:
        log(f"OPEN failed: {result}")
        return False


# === ЗАКРЫТИЕ ===
def close_position(ticket, reason=""):
    pos = get_position(ticket)
    if not pos:
        return False

    try:
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick:
            current_price = tick.bid if pos.type == 1 else tick.ask
            profit_pts = (current_price - pos.price_open) / 0.01 if pos.type == 0 else (pos.price_open - current_price) / 0.01
            profit_pts = round(profit_pts, 1)
        else:
            profit_pts = 0

        postmortem = {
            "ticket": ticket,
            "action": "BUY" if pos.type == 0 else "SELL",
            "entry": round(pos.price_open, 2),
            "close_reason": reason,
            "profit_pts": profit_pts,
            "profit_usd": round(pos.profit, 2) if pos.profit else 0,
        }
        log_event("POSTMORTEM", postmortem)
        sl_label = "🔴 SL" if "SL" in reason.upper() else ("✅ WIN" if profit_pts > 0 else "⏹ CLOSE")
        log(f"📊 #{ticket}: {sl_label} | {profit_pts}pts (${postmortem['profit_usd']}) | {reason}")
    except:
        pass

    # Открываем обратную сделку для закрытия
    close_type = mt5.ORDER_TYPE_BUY if pos.type == 1 else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(pos.symbol).ask if pos.type == 1 else mt5.symbol_info_tick(pos.symbol).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": close_type,
        "position": pos.ticket,
        "price": price,
        "deviation": 20,
        "magic": pos.magic,
        "comment": reason or "CLOSE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result and result.retcode == 10009:
        log(f"#{ticket} closed ({reason})")
        log_event("CLOSE", {"ticket": ticket, "reason": reason, "price": round(price, 2)})
        # Чистим trail файл
        try:
            if os.path.exists(TRAIL_FILE):
                os.remove(TRAIL_FILE)
        except:
            pass
        return True
    return False


def set_sl(ticket, sl_price):
    pos = get_position(ticket)
    if not pos:
        return False
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos.symbol,
        "position": pos.ticket,
        "sl": sl_price,
        "tp": pos.tp,
        "magic": pos.magic,
    }
    result = mt5.order_send(request)
    if result and result.retcode == 10009:
        log(f"#{ticket} SL -> {sl_price:.2f}")
        return True
    return False


def partial_close(ticket, fraction):
    """Закрыть часть позиции."""
    pos = get_position(ticket)
    if not pos:
        return False
    part_vol = round(pos.volume * fraction, 2)
    if part_vol <= 0:
        return False

    close_type = mt5.ORDER_TYPE_BUY if pos.type == 1 else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(pos.symbol).ask if pos.type == 1 else mt5.symbol_info_tick(pos.symbol).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": part_vol,
        "type": close_type,
        "position": pos.ticket,
        "price": price,
        "deviation": 20,
        "magic": pos.magic,
        "comment": "PARTIAL",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result and result.retcode == 10009:
        log(f"#{ticket} PARTIAL CLOSE {part_vol:.2f} @ {price:.2f}")
        log_event("PARTIAL", {"ticket": ticket, "volume": part_vol, "price": round(price, 2)})
        return True
    return False


# === УМНОЕ УПРАВЛЕНИЕ СДЕЛКОЙ ===
def manage_trail():
    try:
        if os.path.exists(TRAIL_FILE):
            with open(TRAIL_FILE) as f:
                trail = json.load(f)
        else:
            return
    except:
        return

    ticket = trail.get("ticket")
    pos = get_position(ticket)
    if not pos:
        try:
            os.remove(TRAIL_FILE)
        except:
            pass
        return

    entry = safe_val(pos.price_open)
    current = safe_val(pos.price_current)
    sl_current = safe_val(pos.sl)
    action = trail.get("action", "BUY")
    strategy = trail.get("strategy", {})
    h1_trend = trail.get("h1_trend", "SIDEWAYS")

    # PROFIT PTS
    if action == "BUY":
        profit_pts = (current - entry) / 0.01
    else:
        profit_pts = (entry - current) / 0.01

    trail_activation = strategy.get("trail_activation", 60)
    trail_offset = strategy.get("trail_offset", 40)
    trail_step = strategy.get("trail_step", 25)
    partial_pts = strategy.get("partial_pts", 50)
    partial_fraction = strategy.get("partial_fraction", 0.30)
    scalp_min = strategy.get("scalp_min_profit", 0)
    partial_done = trail.get("partial_done", False)

    # ============================================================
    # 1. CONTRADICT CLOSE — против тренда
    # ============================================================
    if h1_trend:
        must_close = False
        reason = ""
        if action == "BUY" and h1_trend == "BEARISH":
            must_close = True
            reason = "BUY@BEARISH"
        elif action == "SELL" and h1_trend == "BULLISH":
            must_close = True
            reason = "SELL@BULLISH"

        if must_close and profit_pts > -10:
            log(f"CONTRADICT {reason}, closing #{ticket}")
            close_position(ticket, f"CONTRADICT_{reason}")
            return

    # ============================================================
    # 2. SCALP-ВЫХОД — при затухании импульса
    # ============================================================
    if strategy.get("scalp_close") and profit_pts >= scalp_min and profit_pts < 50:
        momentum = get_m1_momentum()
        # Reversal = коррекция закончена, потенциал роста — не закрываем
        if momentum == "reversal":
            pass
        elif momentum == "fading":
            log(f"📉 SCALP EXIT: {profit_pts:.0f}pts, momentum fading. #{ticket}")
            log_event("SCALP_EXIT", {"ticket": ticket, "profit_pts": round(profit_pts, 1), "reason": "momentum_fading"})
            close_position(ticket, f"SCALP_{profit_pts:.0f}pts")
            return

    # ============================================================
    # 2.5 REVERSAL — разворот убыточной сделки
    # ============================================================
    if profit_pts <= -15 and profit_pts >= -60:
        reversal_key = f"reversal_{ticket}"
        last_reversal = trail.get("_last_reversal_time", 0)
        # Не чаще 1 раза в 5 минут
        if time.time() - last_reversal > 300:
            # Проверяем импульс — последние 3 свечи идут против нас?
            try:
                rates_m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 5)
                if rates_m1 is not None and len(rates_m1) >= 3:
                    closes = [float(r[4]) for r in rates_m1[-3:]]
                    opens = [float(r[1]) for r in rates_m1[-3:]]
                    red_count = sum(1 for i in range(3) if closes[i] < opens[i])
                    green_count = 3 - red_count

                    # Если мы в BUY и 2+ красных подряд — цена идёт против
                    # Если мы в SELL и 2+ зелёных подряд — цена идёт против
                    if (action == "BUY" and red_count >= 2) or (action == "SELL" and green_count >= 2):
                        new_action = "SELL" if action == "BUY" else "BUY"
                        log(f"🔄 REVERSAL: {action} -> {new_action} at {profit_pts:.0f}pts loss. #{ticket}")
                        log_event("REVERSAL", {"ticket": ticket, "from": action, "to": new_action, "loss_pts": round(profit_pts, 1)})

                        # Закрываем текущую
                        close_position(ticket, f"REVERSAL_{action}to{new_action}")

                        # Открываем новую в противоположную сторону
                        tick = mt5.symbol_info_tick(SYMBOL)
                        if tick:
                            new_price = tick.bid if new_action == "SELL" else tick.ask
                            atr_r = get_atr()
                            sl_pts_r = max(15, min(50, atr_r * 1.5))
                            sl_dist = sl_pts_r * 0.01
                            sl_rev = new_price + sl_dist if new_action == "SELL" else new_price - sl_dist
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": SYMBOL,
                                "volume": LOT,
                                "type": mt5.ORDER_TYPE_SELL if new_action == "SELL" else mt5.ORDER_TYPE_BUY,
                                "price": new_price,
                                "sl": sl_rev,
                                "tp": 0.0,
                                "deviation": 20,
                                "magic": MAGIC_SCALP,
                                "comment": f"REV_{new_action}",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC,
                            }
                            result = mt5.order_send(req)
                            if result and result.retcode == 10009:
                                log(f"  -> REVERSAL OPEN {new_action} #{result.order} @ {new_price:.2f}")
                                log_event("REVERSAL_OPEN", {"ticket": result.order, "action": new_action, "price": round(new_price, 2)})

                                # Новый файл управления для разворота
                                atr_r = get_atr()
                                h1_r = get_h1_trend()
                                strategy_r = choose_exit_strategy(atr_r, h1_r)
                                trail_r = {
                                    "ticket": result.order,
                                    "action": new_action,
                                    "entry_price": new_price,
                                    "source": f"REV_{new_action}",
                                    "h1_trend": h1_r,
                                    "strategy": strategy_r,
                                    "partial_done": False,
                                    "second_entry_done": False,
                                    "scalp_check_pts": strategy_r.get("scalp_min_profit", 0),
                                    "scalp_checked": False,
                                    "_last_atr_update": 0,
                                    "_last_reversal_time": 0,
                                }
                                with open(TRAIL_FILE, "w") as f:
                                    json.dump(trail_r, f)
            except:
                pass
            trail["_last_reversal_time"] = time.time()
            with open(TRAIL_FILE, "w") as f:
                json.dump(trail, f)

    # ============================================================
    # 3. PARTIAL CLOSE
    # ============================================================
    if not partial_done and profit_pts >= partial_pts:
        log(f"💰 PARTIAL TRIGGERED: {profit_pts:.0f}pts, closing {partial_fraction*100:.0f}% of #{ticket}")
        if partial_close(ticket, partial_fraction):
            trail["partial_done"] = True
            with open(TRAIL_FILE, "w") as f:
                json.dump(trail, f)

    # ============================================================
    # 4. TRAILING STOP (ATR-адаптивный)
    # ============================================================
    if profit_pts >= trail_activation:
        new_sl = None
        if action == "BUY":
            # Первая активация
            if sl_current <= entry or sl_current <= 0.01:
                new_sl = entry + 0.05  # entry + 5pts безубыток
                log(f"🎯 FIRST TRAIL: SL={new_sl:.2f} (entry+5pts) #{ticket}")
                log_event("TRAIL_ACTIVATE", {"ticket": ticket, "action": "BUY", "entry": round(entry, 2), "sl": round(new_sl, 2)})
            else:
                # Нормальный трейлинг
                candidate = current - trail_offset * 0.01
                step = trail_step * 0.01
                if candidate > sl_current + step:
                    new_sl = candidate
        else:
            # SELL
            if sl_current >= entry or sl_current <= 0.01 or abs(sl_current - entry) < 0.001:
                new_sl = entry - 0.05
                log(f"🎯 FIRST TRAIL: SL={new_sl:.2f} (entry-5pts) #{ticket}")
                log_event("TRAIL_ACTIVATE", {"ticket": ticket, "action": "SELL", "entry": round(entry, 2), "sl": round(new_sl, 2)})
            else:
                candidate = current + trail_offset * 0.01
                step = trail_step * 0.01
                if candidate < sl_current - step:
                    new_sl = candidate

        if new_sl:
            for attempt in range(3):
                if set_sl(ticket, new_sl):
                    log_event("TRAIL_MOVE", {"ticket": ticket, "sl": round(new_sl, 2)})
                    break
                time.sleep(0.1)

    # ============================================================
    # 5. DYNAMIC ATR UPDATE — пересчёт стратегии каждые 30с
    # ============================================================
    # Если стратегия не менялась больше 30с — пересчитать ATR
    last_update = trail.get("_last_atr_update", 0)
    if time.time() - last_update > 30:
        atr = get_atr()
        h1_t = get_h1_trend()
        new_strategy = choose_exit_strategy(atr, h1_t)
        if new_strategy["mode"] != trail.get("strategy", {}).get("mode"):
            log(f"🔄 Strategy update: {trail.get('strategy', {}).get('mode', '?')} -> {new_strategy['mode']} (ATR={atr})")
            trail["strategy"] = new_strategy
        trail["_last_atr_update"] = time.time()
        trail["h1_trend"] = h1_t
        with open(TRAIL_FILE, "w") as f:
            json.dump(trail, f)


# === VALIDATION (unchanged, simplified) ===
_VALIDATION_PENDING = None

def schedule_validation(ticket, entry, action):
    global _VALIDATION_PENDING
    _VALIDATION_PENDING = {"ticket": ticket, "entry": entry, "action": action, "check_time": time.time() + 90, "check_done": False}

def run_validation():
    global _VALIDATION_PENDING
    if not _VALIDATION_PENDING or _VALIDATION_PENDING.get("check_done"):
        return
    if time.time() < _VALIDATION_PENDING["check_time"]:
        return

    v = _VALIDATION_PENDING
    ticket = v["ticket"]
    action = v["action"]
    _VALIDATION_PENDING["check_done"] = True

    log(f"=== VALIDATION #{ticket} ({action}) ===")

    # 1. Alligator M15
    try:
        r = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 30)
        n = None
        if r and len(r) > 15:
            sma5 = sum(float(x[4]) for x in r[-5:]) / 5
            sma8 = sum(float(x[4]) for x in r[-8:]) / 8
            sma13 = sum(float(x[4]) for x in r[-13:]) / 13
            n = "BULLISH" if sma5 > sma8 > sma13 else ("BEARISH" if sma5 < sma8 < sma13 else "SLEEPING")
    except:
        n = "UNKNOWN"
    gator = n or "UNKNOWN"

    # 2. H1
    h1 = get_h1_trend()

    # 3. RSI M5
    try:
        r5 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M5, 0, 20)
        if r5 and len(r5) > 15:
            c = [float(x[4]) for x in r5[-16:]]
            gains = [max(c[i]-c[i-1],0) for i in range(1,len(c))]
            losses = [max(c[i-1]-c[i],0) for i in range(1,len(c))]
            ag = sum(gains[-14:])/14
            al = sum(losses[-14:])/14
            rsi = 50 if al == 0 else 100 - 100/(1+ag/al)
        else:
            rsi = 50
    except:
        rsi = 50

    # 4. Свечи
    try:
        r1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 5)
        if r1 and len(r1) >= 3:
            green = sum(1 for x in r1[-3:] if float(x[4]) > float(x[1]))
            red = 3 - green
        else:
            green, red = 1, 1
    except:
        green, red = 1, 1

    flags = 0
    reasons = []
    if action == "BUY":
        if gator == "BEARISH": flags += 1; reasons.append("BUY@BEARISH")
        if h1 == "BEARISH": flags += 1; reasons.append("BUY@H1_BEARISH")
        if rsi > 70: flags += 1; reasons.append(f"RSI={rsi:.0f}>70")
        if red >= 2: flags += 1; reasons.append(f"{red}red")
    else:
        if gator == "BULLISH": flags += 1; reasons.append("SELL@BULLISH")
        if h1 == "BULLISH": flags += 1; reasons.append("SELL@H1_BULLISH")
        if rsi < 30: flags += 1; reasons.append(f"RSI={rsi:.0f}<30")
        if green >= 2: flags += 1; reasons.append(f"{green}green")

    log(f"  Flags: {flags}/4 — {', '.join(reasons) if reasons else 'OK'}")
    log_event("VALIDATION", {"ticket": ticket, "action": action, "flags": flags, "gator": gator, "h1": h1, "rsi": round(rsi,1), "green": green, "red": red, "reasons": reasons or "OK"})

    if flags >= 3:
        log(f"  🚨 CLOSING #{ticket} — {flags}/4 flags")
        pos = get_position(ticket)
        if pos:
            close_position(ticket, f"INVALID_{flags}f")
    elif flags == 2:
        log(f"  ⚠️ WARNING: {flags}/4 flags. Holding.")
    else:
        log(f"  ✅ PASSED: {flags}/4 flags.")


# === SIGNALS ===
def read_signal(fp):
    try:
        if os.path.exists(fp):
            with open(fp) as f:
                return json.load(f)
    except:
        pass
    return None

def delete_signal(fp):
    try:
        if os.path.exists(fp):
            os.remove(fp)
    except:
        pass

def check_signals():
    all_pos = mt5.positions_get(symbol=SYMBOL)
    if all_pos and len(all_pos) > 0:
        return False
    signals = [(SIGNAL_FILE_V42, "V42"), (SIGNAL_FILE_V50, "V50"), (SIGNAL_FILE_M15, "M15")]
    for sig_file, source in signals:
        signal = read_signal(sig_file)
        if signal:
            action = signal.get("action", "")
            log(f"Signal {source}: {action} @ {signal.get('price', 0)}")
            if open_trade(signal, source):
                delete_signal(sig_file)
                return True
            else:
                delete_signal(sig_file)
    return False


# === MAIN ===
def main():
    log("=== GOLD Universal Executor v4 STARTED ===")
    log("Smart exit: ATR-adaptive trailing | Partial close | Scalp exit")
    if not init_mt5():
        return

    write_heartbeat()
    while True:
        try:
            write_heartbeat()
            manage_trail()
            run_validation()

            positions = get_all_positions()
            if len(positions) > 1:
                types = ["BUY" if p.type == 0 else "SELL" for p in positions]
                if "BUY" in types and "SELL" in types:
                    log(f"Cross-magic conflict! Closing smaller.")
                    for p in sorted(positions, key=lambda x: x.volume):
                        close_position(p.ticket, "CONTRADICT_CROSS")
                        break

            if not positions:
                check_signals()

        except Exception as e:
            log(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
