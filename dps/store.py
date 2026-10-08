"""Local parquet cache under data/. One file per source, keyed by quarter-hour start.

Every row keeps `first_seen` (when we first stored a value for it) and `fetched_at`
(last write). Live runs build up an honest record of when values were known.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .util import now

SOURCES = {
    "da": ["da"],                              # ENTSO-E A44 day-ahead price, EUR/MWh
    "load": ["load_actual", "load_da"],        # ENTSO-E A65, MW
    "id_aep": ["id_aep"],                      # netztransparenz ID-AEP, EUR/MWh
}


def path(name: str) -> Path:
    return Path(config.DATA_DIR) / f"{name}.parquet"


def read(name: str) -> pd.DataFrame:
    p = path(name)
    if not p.is_file():
        return pd.DataFrame(columns=["ts", *SOURCES[name], "first_seen", "fetched_at"])
    df = pd.read_parquet(p)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def upsert(name: str, new: pd.DataFrame) -> int:
    """Merge `new` (ts + value columns) into the cache. Returns rows written/changed."""
    if new is None or new.empty:
        return 0
    cols = SOURCES[name]
    new = new[["ts", *[c for c in cols if c in new.columns]]].copy()
    new["ts"] = pd.to_datetime(new["ts"], utc=True)
    t = now().floor("s")
    old = read(name)
    if old.empty:
        merged = new.assign(first_seen=t, fetched_at=t)
        changed = int(new[[c for c in cols if c in new.columns]].notna().sum().sum())
    else:
        merged = old.set_index("ts")
        n = new.set_index("ts")
        changed = 0
        for c in n.columns:
            if c not in merged:
                merged[c] = float("nan")
            prev = merged[c].reindex(n.index)
            diff = n[c].notna() & (prev.isna() | ((n[c] - prev).abs() > 1e-9))
            changed += int(diff.sum())
            merged = merged.reindex(merged.index.union(n.index))
            merged.loc[diff[diff].index, c] = n.loc[diff, c]
            merged.loc[diff[diff].index, "fetched_at"] = t
        merged["first_seen"] = merged["first_seen"].fillna(t)
        merged["fetched_at"] = merged["fetched_at"].fillna(t)
        merged = merged.rename_axis("ts").reset_index()
    for c in ("first_seen", "fetched_at"):
        merged[c] = pd.to_datetime(merged[c], utc=True)
    p = path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    merged.sort_values("ts").reset_index(drop=True).to_parquet(p, index=False)
    return changed


def last_ts(name: str) -> pd.Timestamp | None:
    df = read(name)
    vals = df.dropna(subset=[c for c in SOURCES[name] if c in df.columns], how="all")
    return None if vals.empty else vals["ts"].max()
