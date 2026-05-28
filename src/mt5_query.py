"""
Hermes Agent — MetaTrader 5 Client
====================================
Connects to a locally running MetaTrader 5 terminal (no password required —
``mt5.initialize()`` discovers the running instance).

Provides:
    - Account info (balance, equity, margin, etc.)
    - Open positions
    - Current price (bid/ask)
    - Historical bars (OHLCV)

Requires: MetaTrader 5 terminal installed and logged into a trading account.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

_initialized: bool = False


def _ensure_connected() -> None:
    """Lazy-initialize MT5 connection.  Call before any MT5 operation."""
    global _initialized
    if _initialized:
        return

    import MetaTrader5 as mt5  # type: ignore

    if not mt5.initialize():
        error_code = mt5.last_error()
        raise ConnectionError(
            f"MT5 initialize() failed. "
            f"Is MetaTrader 5 terminal running and logged in? "
            f"Error: ({error_code[0]}) {error_code[1]}"
        )

    _initialized = True
    logger.info("MT5 connected — version %s", mt5.version())


def shutdown() -> None:
    """Explicitly shut down the MT5 connection."""
    global _initialized
    if not _initialized:
        return

    import MetaTrader5 as mt5  # type: ignore

    mt5.shutdown()
    _initialized = False
    logger.info("MT5 connection closed.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def account_info() -> Dict[str, Any]:
    """Return account summary.

    Returns:
        Dict with keys: login, server, balance, equity, margin, margin_free,
        currency, leverage, etc.  Empty dict on failure.
    """
    _ensure_connected()
    import MetaTrader5 as mt5  # type: ignore

    info = mt5.account_info()
    if info is None:
        error_code = mt5.last_error()
        raise RuntimeError(
            f"MT5 account_info() failed. Error: ({error_code[0]}) {error_code[1]}"
        )
    return info._asdict()


def open_positions(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return list of currently open positions.

    Args:
        symbol: Optional ticker filter (e.g. ``EURUSD``).

    Returns:
        List of position dicts (ticket, symbol, type, volume, open_price,
        sl, tp, profit, comment, etc.).
    """
    _ensure_connected()
    import MetaTrader5 as mt5  # type: ignore

    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    if positions is None:
        return []
    return [p._asdict() for p in positions]


def current_price(symbol: str) -> Dict[str, Any]:
    """Get current bid/ask for a symbol.

    Args:
        symbol: Ticker symbol (e.g. ``EURUSD``).

    Returns:
        Dict with keys: symbol, bid, ask, time, spread.
    """
    if not symbol or not symbol.strip():
        raise ValueError("symbol must be non-empty")

    _ensure_connected()
    import MetaTrader5 as mt5  # type: ignore

    tick = mt5.symbol_info_tick(symbol.strip())
    if tick is None:
        error_code = mt5.last_error()
        raise RuntimeError(
            f"MT5 symbol_info_tick({symbol!r}) failed. "
            f"Is the symbol available in Market Watch? "
            f"Error: ({error_code[0]}) {error_code[1]}"
        )
    return tick._asdict()


def bars(
    symbol: str,
    timeframe: str = "H1",
    count: int = 100,
) -> np.ndarray:
    """Get historical OHLCV bars.

    Args:
        symbol: Ticker symbol (e.g. ``EURUSD``).
        timeframe: MT5 timeframe: ``M1``, ``M5``, ``M15``, ``M30``,
                   ``H1``, ``H4``, ``D1``, ``W1``, ``MN1``.
        count: Number of bars to retrieve (default 100).

    Returns:
        Structured numpy array with columns:
        time, open, high, low, close, tick_volume, spread, real_volume.
    """
    if not symbol or not symbol.strip():
        raise ValueError("symbol must be non-empty")
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")

    _ensure_connected()
    import MetaTrader5 as mt5  # type: ignore

    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }

    tf = tf_map.get(timeframe.upper())
    if tf is None:
        raise ValueError(
            f"Unknown timeframe {timeframe!r}. "
            f"Valid: {', '.join(tf_map.keys())}"
        )

    rates = mt5.copy_rates_from_pos(symbol.strip(), tf, 0, count)
    if rates is None:
        error_code = mt5.last_error()
        raise RuntimeError(
            f"MT5 copy_rates_from_pos({symbol!r}, {timeframe}) failed. "
            f"Error: ({error_code[0]}) {error_code[1]}"
        )
    return rates
