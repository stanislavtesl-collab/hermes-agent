"""Безопасное чтение MT5 position-полей — safe_val().

MT5 positions_get() может возвращать numpy массивы вместо float.
Используй этот модуль вместо прямого float(pos.field).

Импорт:
```python
import sys
sys.path.insert(0, r"C:\Users\Administrator\AppData\Local\hermes\skills\trading\strategy-backtest-optimization\scripts")
from safe_val import safe_val, safe_get
```
"""

import numpy as np


def safe_val(val):
    """Безопасно приводит MT5/любое значение к float или None.
    \n    Обрабатывает:
      - None → None
      - numpy.array → float(array.item())
      - float/int → float
      - numpy.generic → float
      - мусор (NoneType от numpy) → None
    \n    Также фильтрует выбросы (>1e10) которые означают ошибку чтения.
    \n    Применяется к: pos.price_current, pos.sl, pos.volume, pos.profit, pos.tp
    \n    ВАЖНО: pos.ticket тоже может быть numpy — сравнение pos.ticket == trail["ticket"]
    работает с numpy.int64, но для обратной совместимости safe_val() тоже можно применить.
    """
    if val is None:
        return None
    if isinstance(val, np.ndarray):
        if val.size == 0:
            return None
        return float(val.item())
    if isinstance(val, np.generic):
        return float(val)
    try:
        v = float(val)
        return None if v > 1e10 or v < -1e10 else v
    except (TypeError, ValueError):
        return None


def safe_get(pos, field, default=None):
    """Безопасно читает поле из MT5 position-объекта."""
    try:
        return safe_val(getattr(pos, field, None))
    except Exception:
        return default
