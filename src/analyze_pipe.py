"""
Hermes Agent — Technical Analysis Pipeline
============================================
Orchestrates data fetching and indicator calculation.

Workflow:
    1. Fetch OHLCV data (from MT5 or Twelve Data)
    2. Compute indicators via ``indicators.py``
    3. Return structured analysis result

Intended to be called by the Hermes Gateway agent via skill tools.
"""

import json
import logging
import sys
from typing import Any, Dict, Optional

import numpy as np

# Local imports — assume scripts are on sys.path (set by gateway)
from indicators import compute_all
from twelvedata_query import extract_close_series, time_series

logger = logging.getLogger(__name__)

# Try to import MT5; it may not be available outside Windows
try:
    from mt5_query import bars as mt5_bars
    _MT5_AVAILABLE = True
except ImportError:
    _MT5_AVAILABLE = False
    logger.warning("mt5_query not available — MT5 data source disabled.")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def analyze(
    symbol: str,
    source: str = "mt5",
    timeframe: str = "H1",
    bars_count: int = 100,
) -> Dict[str, Any]:
    """Run full technical analysis for a symbol.

    Args:
        symbol: Ticker (e.g. ``EURUSD`` for MT5, ``EUR/USD`` for Twelve Data).
        source: Data source — ``mt5`` or ``twelvedata``.
        timeframe: Bar interval (MT5: ``H1``, Twelve Data: ``1h``).
        bars_count: Number of bars to fetch (default 100).

    Returns:
        Dictionary with:
            - symbol, source, timeframe, data_points
            - latest: latest indicator values
            - signals: derived buy/sell signals
    """
    if source not in ("mt5", "twelvedata"):
        raise ValueError(f"source must be 'mt5' or 'twelvedata', got {source!r}")

    # ------------------------------------------------------------------
    # 1. Fetch data
    # ------------------------------------------------------------------
    close_prices: np.ndarray

    if source == "mt5":
        if not _MT5_AVAILABLE:
            raise RuntimeError(
                "MT5 source requested but mt5_query is not available. "
                "Install MetaTrader5 package or use source='twelvedata'."
            )
        # Map external timeframe to MT5 format
        tf_map = {
            "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
            "1h": "H1", "H1": "H1",
            "4h": "H4", "H4": "H4",
            "1d": "D1", "D1": "D1",
            "1w": "W1", "W1": "W1",
            "1M": "MN1", "MN1": "MN1",
        }
        mt5_tf = tf_map.get(timeframe, timeframe)
        rates = mt5_bars(symbol, mt5_tf, bars_count)
        close_prices = rates["close"].astype(np.float64)

    else:  # twelvedata
        # Map timeframe to Twelve Data format
        td_tf_map = {
            "M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min",
            "H1": "1h", "1h": "1h",
            "H4": "4h", "4h": "4h",
            "D1": "1day", "1d": "1day",
            "W1": "1week", "1w": "1week",
            "MN1": "1month", "1M": "1month",
        }
        td_interval = td_tf_map.get(timeframe, "1h")
        data = time_series(symbol, interval=td_interval, outputsize=bars_count)
        close_list = extract_close_series(data)
        if not close_list:
            raise RuntimeError(
                f"No data returned from Twelve Data for {symbol!r} "
                f"(interval={td_interval}). Check symbol spelling and API key."
            )
        close_prices = np.array(close_list, dtype=np.float64)

    # ------------------------------------------------------------------
    # 2. Compute indicators
    # ------------------------------------------------------------------
    indicators = compute_all(close_prices)
    if "error" in indicators:
        raise RuntimeError(f"Indicator computation failed: {indicators['error']}")

    latest = indicators["latest"]

    # ------------------------------------------------------------------
    # 3. Derive simple signals
    # ------------------------------------------------------------------
    signals = _derive_signals(latest)

    return {
        "symbol": symbol,
        "source": source,
        "timeframe": timeframe,
        "data_points": len(close_prices),
        "latest": latest,
        "signals": signals,
    }


def _derive_signals(latest: Dict[str, Optional[float]]) -> Dict[str, str]:
    """Derive basic trading signals from indicator values."""
    signals: Dict[str, str] = {}

    # RSI
    rsi_val = latest.get("rsi_14")
    if rsi_val is not None:
        if rsi_val > 70:
            signals["rsi"] = "overbought"
        elif rsi_val < 30:
            signals["rsi"] = "oversold"
        else:
            signals["rsi"] = "neutral"

    # MACD
    macd_val = latest.get("macd")
    macd_sig = latest.get("macd_signal")
    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig:
            signals["macd"] = "bullish"
        else:
            signals["macd"] = "bearish"

    # EMA crossover (9 vs 21)
    ema9 = latest.get("ema_9")
    ema21 = latest.get("ema_21")
    if ema9 is not None and ema21 is not None:
        if ema9 > ema21:
            signals["ema_cross"] = "bullish"
        else:
            signals["ema_cross"] = "bearish"

    # Bollinger Bands
    price = latest.get("price")
    bb_upper = latest.get("bb_upper")
    bb_lower = latest.get("bb_lower")
    if price is not None and bb_upper is not None and bb_lower is not None:
        if price >= bb_upper:
            signals["bollinger"] = "upper_band_touch"
        elif price <= bb_lower:
            signals["bollinger"] = "lower_band_touch"
        else:
            signals["bollinger"] = "inside_bands"

    return signals


# ---------------------------------------------------------------------------
# CLI entry point (for manual testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} SYMBOL [SOURCE] [TIMEFRAME] [BARS]")
        print(f"Example: python {sys.argv[0]} EURUSD mt5 H1 100")
        sys.exit(1)

    sym = sys.argv[1]
    src = sys.argv[2] if len(sys.argv) > 2 else "twelvedata"
    tf = sys.argv[3] if len(sys.argv) > 3 else "1h"
    cnt = int(sys.argv[4]) if len(sys.argv) > 4 else 100

    try:
        result = analyze(sym, source=src, timeframe=tf, bars_count=cnt)
        print(json.dumps(result, indent=2, default=str))
    except Exception as exc:
        logger.error("Analysis failed: %s", exc)
        sys.exit(1)
