"""
Hermes Agent — Technical Indicators Library
=============================================
Pure Python implementations of core technical indicators.
No external dependencies beyond numpy (standard in scientific Python).

Indicators:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - EMA (Exponential Moving Average)
    - SMA (Simple Moving Average)
    - Bollinger Bands
"""

import numpy as np
from typing import Tuple, Optional


def sma(close: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average.

    Args:
        close: 1-D array of closing prices.
        period: Lookback window.

    Returns:
        Array of same length; first ``period - 1`` values are NaN.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if len(close) < period:
        return np.full_like(close, np.nan, dtype=np.float64)

    result = np.full_like(close, np.nan, dtype=np.float64)
    cumsum = np.cumsum(np.insert(close, 0, 0.0))
    result[period - 1 :] = (cumsum[period:] - cumsum[:-period]) / period
    return result


def ema(close: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average.

    Args:
        close: 1-D array of closing prices.
        period: Lookback window.

    Returns:
        Array of same length; first ``period - 1`` values are NaN.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if len(close) == 0:
        return np.array([], dtype=np.float64)

    result = np.full_like(close, np.nan, dtype=np.float64)
    multiplier = 2.0 / (period + 1)

    # Seed EMA with SMA of first `period` values
    if len(close) >= period:
        result[period - 1] = np.mean(close[:period])
        for i in range(period, len(close)):
            result[i] = (close[i] - result[i - 1]) * multiplier + result[i - 1]

    return result


def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index (Wilder's smoothing).

    Args:
        close: 1-D array of closing prices.
        period: Lookback window (default 14).

    Returns:
        Array of same length; first ``period`` values are NaN.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if len(close) < period + 1:
        return np.full_like(close, np.nan, dtype=np.float64)

    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    result = np.full_like(close, np.nan, dtype=np.float64)

    # Wilder's smoothing: first value is simple average
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(close)):
        avg_gain = (avg_gain * (period - 1) + gain[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i - 1]) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))

    return result


def macd(
    close: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD (Moving Average Convergence Divergence).

    Args:
        close: 1-D array of closing prices.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        Tuple of (macd_line, signal_line, histogram).
        All arrays same length as `close`.
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)

    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)

    # Histogram is valid wherever signal_line is valid
    histogram = np.where(~np.isnan(signal_line), macd_line - signal_line, np.nan)

    return macd_line, signal_line, histogram


def bollinger_bands(
    close: np.ndarray,
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bollinger Bands.

    Args:
        close: 1-D array of closing prices.
        period: SMA period (default 20).
        num_std: Number of standard deviations (default 2.0).

    Returns:
        Tuple of (middle_band, upper_band, lower_band).
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if num_std <= 0:
        raise ValueError(f"num_std must be positive, got {num_std}")

    middle = sma(close, period)
    std = np.full_like(close, np.nan, dtype=np.float64)

    for i in range(period - 1, len(close)):
        std[i] = np.std(close[i - period + 1 : i + 1], ddof=1)

    upper = middle + num_std * std
    lower = middle - num_std * std

    return middle, upper, lower


def compute_all(close: np.ndarray) -> dict:
    """Compute all standard indicators for a price series.

    Args:
        close: 1-D array of closing prices.

    Returns:
        Dictionary with keys: rsi_14, macd, macd_signal, macd_hist,
        ema_9, ema_21, bb_middle, bb_upper, bb_lower.
        Latest (last valid) values under ``latest`` sub-dict.
    """
    if len(close) == 0:
        return {"error": "empty price series"}

    rsi_14 = rsi(close, 14)
    macd_line, macd_signal, macd_hist = macd(close)
    ema_9 = ema(close, 9)
    ema_21 = ema(close, 21)
    bb_mid, bb_up, bb_lo = bollinger_bands(close, 20, 2.0)

    def _last(arr: np.ndarray) -> Optional[float]:
        valid = arr[~np.isnan(arr)]
        return float(valid[-1]) if len(valid) > 0 else None

    return {
        "series": {
            "rsi_14": rsi_14.tolist(),
            "macd": macd_line.tolist(),
            "macd_signal": macd_signal.tolist(),
            "macd_histogram": macd_hist.tolist(),
            "ema_9": ema_9.tolist(),
            "ema_21": ema_21.tolist(),
            "bb_middle": bb_mid.tolist(),
            "bb_upper": bb_up.tolist(),
            "bb_lower": bb_lo.tolist(),
        },
        "latest": {
            "rsi_14": _last(rsi_14),
            "macd": _last(macd_line),
            "macd_signal": _last(macd_signal),
            "macd_histogram": _last(macd_hist),
            "ema_9": _last(ema_9),
            "ema_21": _last(ema_21),
            "bb_middle": _last(bb_mid),
            "bb_upper": _last(bb_up),
            "bb_lower": _last(bb_lo),
            "price": float(close[-1]),
        },
    }
