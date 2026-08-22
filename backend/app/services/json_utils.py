"""
Recursively convert numpy/pandas scalar types (np.bool_, np.int64,
np.float64, etc.) into plain Python types so they can be stored in
SQLAlchemy JSON columns. Pandas/numpy operations inside the agents
routinely produce these types; without this conversion, JSON
serialization fails at write time.
"""
from __future__ import annotations
import numpy as np


def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    return obj
