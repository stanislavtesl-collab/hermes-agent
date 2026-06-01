#!/usr/bin/env python3
"""
ATMAN-v04 OPTIMIZER — Pattern A only
Grid search over TP, BE, SL, trailing, hours, DOW filters.
17,280 combinations.

Usage:
    "/c/Program Files/Python312/python.exe" atman_v04_optimizer.py

Output: results/atman_optimization_results.json
"""
import numpy as np
import pandas as pd
import json, itertools, math, sys
from pathlib import Path

# ===== CONFIGURATION =====
DATA_FILE = Path(r"C:\Users\Administrator\Desktop\FxPro\data\XAUUSD_H1_2019_2025.csv")
OUT_DIR = Path(r"C:\Users\Administrator\Desktop\FxPro\results")
BACKTEST_START = "2025-01-01"
LOT = 0.01
POINT = 0.01
SPREAD_FILTER_MAX = 150
SWING_LOOKBACK_H4 = 50

TP_OPTIONS = [150, 200, 250, 300, 350, 400, 500, 555]
BE_OPTIONS = [0.2, 0.3, 0.35, 0.4, 0.5, 0.6]
SL_OPTIONS = [120, 150, 185, 220, 250]
TRAIL_OPTIONS = [None, 20, 30, 50]
HOUR_RANGES = [(7,20), (8,20), (9,20), (10,20), (12,20), (13,20)]
DOW_FILTERS = [None, "not_mon", "not_mon_wed"]

# ===== FULL PYTHON SOURCE in atman_v04_optimizer.py under FxPro/ =====
# See that file for complete implementation.

if __name__ == "__main__":
    print("This file documents the optimizer configuration only.")
    print(f"Total combinations: {len(TP_OPTIONS)*len(BE_OPTIONS)*len(SL_OPTIONS)*len(TRAIL_OPTIONS)*len(HOUR_RANGES)*len(DOW_FILTERS):,}")
    print("Run the actual optimizer via:")
    print('  "/c/Program Files/Python312/python.exe" atman_v04_optimizer.py')
