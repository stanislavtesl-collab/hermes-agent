"""
Hermes Agent — Twelve Data API Client
======================================
Lightweight wrapper around Twelve Data REST API for market quotes and
historical bars.  Uses only standard-library ``urllib`` — no ``twelvedata`` SDK.

Endpoints used:
    - /quote        — real-time quote for a symbol
    - /time_series  — historical OHLCV bars

Rate limit: 800 requests/day (free tier).
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

API_BASE = "https://api.twelvedata.com"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api_key() -> str:
    """Return Twelve Data API key from environment."""
    key = os.getenv("TWELVEDATA_API_KEY", "")
    if not key:
        raise RuntimeError(
            "TWELVEDATA_API_KEY environment variable is not set. "
            "Get a free key at https://twelvedata.com/apikey"
        )
    return key


def _get(endpoint: str, params: Dict[str, str]) -> Dict[str, Any]:
    """Perform a GET request to the Twelve Data API.

    Args:
        endpoint: API path (e.g. ``/quote``).
        params: Query-string parameters (``apikey`` added automatically).

    Returns:
        Parsed JSON response as a dictionary.

    Raises:
        RuntimeError: On HTTP or API-level errors.
    """
    params = {**params, "apikey": _api_key()}
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}{endpoint}?{query}"

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Twelve Data HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Twelve Data connection error: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Twelve Data invalid JSON response: {exc}") from exc

    if "code" in data and data.get("status") == "error":
        raise RuntimeError(f"Twelve Data API error: {data.get('message', data)}")

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def quote(symbol: str, interval: str = "1min") -> Dict[str, Any]:
    """Get a real-time (or delayed) quote for a symbol.

    Args:
        symbol: Ticker symbol (e.g. ``EUR/USD``, ``AAPL``).
        interval: Bar interval for the quote (default ``1min``).

    Returns:
        Dictionary with keys: symbol, name, open, high, low, close,
        previous_close, change, percent_change, volume, datetime, etc.
    """
    if not symbol or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")

    return _get("/quote", {"symbol": symbol.strip(), "interval": interval})


def time_series(
    symbol: str,
    interval: str = "1h",
    outputsize: int = 60,
) -> Dict[str, Any]:
    """Get historical OHLCV bars for a symbol.

    Args:
        symbol: Ticker symbol (e.g. ``EUR/USD``, ``AAPL``).
        interval: Bar interval: ``1min``, ``5min``, ``15min``, ``30min``,
                  ``1h``, ``1day``, ``1week``, ``1month``.
        outputsize: Number of bars to return (default 60).

    Returns:
        Dictionary with keys: meta (symbol, interval, etc.),
        values (list of {datetime, open, high, low, close, volume}),
        status.
    """
    if not symbol or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")
    if outputsize < 1 or outputsize > 5000:
        raise ValueError(f"outputsize must be 1–5000, got {outputsize}")

    return _get(
        "/time_series",
        {
            "symbol": symbol.strip(),
            "interval": interval,
            "outputsize": str(outputsize),
        },
    )


def extract_close_series(data: Dict[str, Any]) -> list:
    """Extract closing prices as a list (oldest first) from a time_series response.

    Args:
        data: Response dict from ``time_series()``.

    Returns:
        List of float closing prices, chronological order.
    """
    values = data.get("values", [])
    if not values:
        return []
    # Twelve Data returns newest-first; reverse to oldest-first
    return [float(v["close"]) for v in reversed(values)]
