"""Безопасное чтение MT5 position-полей — safe_val().

MT5 positions_get() может возвращать numpy массивы вместо float.
Используй этот модуль вместо прямого float(pos.field).
"""

import numpy as np


def safe_val(val):
    """Безопасно приводит MT5/любое значение к float или None.
    
    Обрабатывает:
      - None → None
      - numpy.array → float(array.item()) 
      - float/int → float
      - мусор (NoneType от numpy) → None
    
    Также фильтрует выбросы (>1e10) которые означают ошибку чтения.
    """
    if val is None:
        return None
    # numpy array — самое частое (pos.sl, pos.price_current)
    if isinstance(val, np.ndarray):
        if val.size == 0:
            return None
        return float(val.item())
    if isinstance(val, np.generic):
        return float(val)
    try:
        v = float(val)
        # выброс — ошибка чтения
        return None if v > 1e10 or v < -1e10 else v
    except (TypeError, ValueError):
        return None


def safe_get(pos, field, default=None):
    """Безопасно читает поле из MT5 position-объекта."""
    try:
        return safe_val(getattr(pos, field, None))
    except Exception:
        return default
