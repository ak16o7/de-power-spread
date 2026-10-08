"""One row per quarter hour: prices, spread and when each of them became known.

spread = ID-AEP - day-ahead price. A long position (buy day-ahead, sell at ID-AEP)
earns the spread.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from . import hf, store
from .util import da_known_at, delivery_day, local, slot, spread_known_at


def quarter_hours(start: date, end: date) -> pd.DatetimeIndex:
    """All quarter-hour starts (UTC) of the local delivery days [start, end)."""
    return pd.date_range(local(start), local(end), freq="15min", inclusive="left")


def build(start: date, end: date, with_fundamentals: bool = False) -> pd.DataFrame:
    """Panel for local delivery days [start, end)."""
    idx = quarter_hours(start, end)
    df = pd.DataFrame(index=idx)
    df.index.name = "ts"
    for name in ("da", "id_aep", "load"):
        src = store.read(name).set_index("ts")
        for c in store.SOURCES[name]:
            df[c] = src[c].reindex(idx).astype("float64") if c in src else np.nan
    df["spread"] = df["id_aep"] - df["da"]
    df["day"] = delivery_day(idx)
    df["slot"] = slot(idx)
    first = {d: (da_known_at(d), spread_known_at(d)) for d in sorted(set(df["day"]))}
    df["da_known_at"] = pd.DatetimeIndex([first[d][0] for d in df["day"]])
    df["spread_known_at"] = pd.DatetimeIndex([first[d][1] for d in df["day"]])
    if with_fundamentals:
        act = hf.generation("a75", start, end).reindex(idx)
        fc = hf.generation("a69_da", start, end).reindex(idx)
        for tech in hf.TECHS:
            df[f"{tech}_actual"] = act[tech]
            df[f"{tech}_da"] = fc[tech]
            df[f"err_{tech}"] = act[tech] - fc[tech]          # MW, > 0: more than forecast
        df["err_load"] = df["load_actual"] - df["load_da"]  # MW, > 0: more demand than forecast
    return df
