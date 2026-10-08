"""The dumb strategies the model has to beat. If one of these already earns money,
that is a risk premium or a calendar effect, not alpha from the forecast.

All use only spreads known at the decision time (feature columns sp_*).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def always_long(f: pd.DataFrame) -> np.ndarray:
    return np.ones(len(f))


def always_short(f: pd.DataFrame) -> np.ndarray:
    return -np.ones(len(f))


def slot_sign_28d(f: pd.DataFrame) -> np.ndarray:
    """Sign of the mean spread of the same local quarter over the last 28 known days."""
    return np.nan_to_num(np.sign(f["sp_slot_mean28"].to_numpy(dtype="float64")))


def last_known_sign(f: pd.DataFrame) -> np.ndarray:
    """Sign of the same quarter's spread on the newest known day (D-3)."""
    return np.nan_to_num(np.sign(f["sp_slot_last"].to_numpy(dtype="float64")))


BASELINES = {
    "always_long": always_long,
    "always_short": always_short,
    "slot_sign_28d": slot_sign_28d,
    "last_known_sign": last_known_sign,
}
