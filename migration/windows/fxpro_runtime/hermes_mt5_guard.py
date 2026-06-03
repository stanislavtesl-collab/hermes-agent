"""Pinned MT5 guard for Hermes/FxPro runtime.

Fail-closed: runtime may only talk to the FxPro terminal that is already logged
into account 591712391. Never falls back to bare mt5.initialize() and never tries
passwordless mt5.login() into another terminal.
"""
from __future__ import annotations

import json
from pathlib import Path

import MetaTrader5 as mt5

FXPRO_DIR = Path(r"C:\Users\Administrator\Desktop\FxPro")
CONSTANTS_FILE = FXPRO_DIR / "_hermes_constants.json"
EXPECTED_ACCOUNT = 591712391
TERMINAL_PATH = r"C:\Users\Administrator\Desktop\FxPro\terminal64.exe"


def load_constants() -> dict:
    try:
        data = json.loads(CONSTANTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return data


def expected_account() -> int:
    return int(load_constants().get("allowed_mt5_account", EXPECTED_ACCOUNT))


def terminal_path() -> str:
    return str(load_constants().get("allowed_terminal_path", TERMINAL_PATH))


def initialize_pinned(timeout: int = 15000) -> bool:
    """Initialize MT5 only through the pinned FxPro terminal path."""
    return bool(mt5.initialize(path=terminal_path(), timeout=timeout))


def assert_pinned_account() -> object:
    acc = mt5.account_info()
    exp = expected_account()
    if acc is None:
        raise RuntimeError(f"MT5 account_info is None; last_error={mt5.last_error()}")
    if int(acc.login) != exp:
        raise RuntimeError(f"MT5_ACCOUNT_MISMATCH got={acc.login} expected={exp} terminal={terminal_path()}")
    return acc


def initialize_and_assert(timeout: int = 15000) -> object:
    if not initialize_pinned(timeout=timeout):
        raise RuntimeError(f"MT5_INIT_FAILED terminal={terminal_path()} last_error={mt5.last_error()}")
    return assert_pinned_account()
