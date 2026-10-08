"""Read the public de-power-forecast dataset on Hugging Face (no token needed).

Used here: weather forecasts (Open-Meteo previous runs and recorded runs), TSO
day-ahead wind/solar forecasts and actuals (only for the ex-post explanation), and
installed capacity. DPS_HF_LOCAL=/path reads the same layout from a local folder
(tests, offline work).
"""
from __future__ import annotations

import glob
import logging
import os
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import config
from .util import month_starts

LOG = logging.getLogger(__name__)
TECHS = ("solar", "wind_on", "wind_off")


_USED: set[str] = set()   # snapshot folders read in this process (= dataset revisions)


def _root(patterns: tuple[str, ...]) -> Path:
    local_dir = os.environ.get("DPS_HF_LOCAL")
    if local_dir:
        _USED.add(f"local:{Path(local_dir).name}")
        return Path(local_dir)
    from huggingface_hub import snapshot_download
    root = Path(snapshot_download(config.HF_DATASET, repo_type="dataset", revision=config.HF_REVISION,
                                  allow_patterns=list(patterns)))
    _USED.add(root.name)
    return root


def revisions_used() -> list[str]:
    """Dataset revisions (snapshot commit hashes) read so far; recorded in every report."""
    return sorted(_USED)


def _read(patterns: tuple[str, ...]) -> pd.DataFrame:
    root = _root(patterns)
    files = sorted({f for p in patterns for f in glob.glob(str(root / p))})
    frames = [pd.read_parquet(f) for f in files]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _month_patterns(prefix: str, start: date, end: date, yearly_dir: bool) -> tuple[str, ...]:
    out = []
    for m in month_starts(start, end):
        out.append(f"{prefix}/{m:%Y}/{m:%Y-%m}.parquet" if yearly_dir else f"{prefix}/{m:%Y-%m}/*.parquet")
    return tuple(out)


def archive_like(runs: pd.DataFrame, model: str) -> pd.DataFrame:
    """Cut complete runs down to what the previous-runs archive offers: only leads inside
    config.ARCHIVE_LEAD_WINDOWS, and never available before the archive's own bound
    (valid - N*24 h + delay). Used for the homogeneous-vintage robustness variant."""
    lead = (pd.to_datetime(runs["valid"], utc=True) - pd.to_datetime(runs["run"], utc=True)) / pd.Timedelta(hours=1)
    n = pd.Series(0, index=runs.index, dtype="int64")
    for i, (lo, hi) in enumerate(config.ARCHIVE_LEAD_WINDOWS, start=1):
        n[(lead >= lo) & (lead < hi)] = i
    keep = n > 0
    out = runs[keep].copy()
    n = n[keep]
    valid = pd.to_datetime(out["valid"], utc=True)
    bound = valid - pd.to_timedelta(n * 24, unit="h") + pd.Timedelta(hours=config.ARCHIVE_DELAY_H[model])
    avail = pd.to_datetime(out["available_at"], utc=True)
    out["available_at"] = avail.where(avail >= bound, bound)
    out["lead_h"] = (n * 24).astype("float64")
    return out


@lru_cache(maxsize=8)
def weather(model: str, start: date, end: date, archive_only: bool = False) -> pd.DataFrame:
    """Every forecast value of `model` for valid times around [start, end), long format:
    point, valid, available_at, lead_h, <variables>.

    lead_h = hours between model run and valid time (previous runs: 24 * lead_days).
    archive_only: complete runs are reduced to what the previous-runs archive has.
    """
    a, b = start - timedelta(days=3), end + timedelta(days=3)
    prev = _read(_month_patterns(f"weather/previous_runs/{model}", a, b, yearly_dir=True))
    runs = _read(_month_patterns(f"weather/runs/{model}", a - timedelta(days=3), b, yearly_dir=False))
    parts = []
    if not prev.empty:
        prev = prev.assign(lead_h=prev["lead_days"].astype("int64") * 24)
        parts.append(prev.drop(columns=[c for c in ("lead_days", "fetched_at") if c in prev]))
    if not runs.empty:
        if archive_only:
            runs = archive_like(runs, model)
        else:
            runs = runs.assign(lead_h=(pd.to_datetime(runs["valid"], utc=True)
                                       - pd.to_datetime(runs["run"], utc=True)) / pd.Timedelta(hours=1))
        parts.append(runs.drop(columns=[c for c in ("run", "fetched_at", "source") if c in runs]))
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    df["point"] = df["point"].astype(str)
    for c in ("valid", "available_at"):
        df[c] = pd.to_datetime(df[c], utc=True)
    lo, hi = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
    df = df[(df["valid"] >= lo) & (df["valid"] < hi)]
    return df.sort_values(["valid", "available_at"], kind="stable").reset_index(drop=True)


def generation(stream: str, start: date, end: date, area: str = "DE") -> pd.DataFrame:
    """Wide quarter-hour frame (solar, wind_on, wind_off) of an ENTSO-E stream: a75 or a69_da."""
    df = _read(_month_patterns(f"entsoe/{stream}/{area}", start - timedelta(days=1), end, yearly_dir=True))
    if df.empty:
        return pd.DataFrame(columns=list(TECHS))
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    wide = df.pivot_table(index="ts", columns="psr", values="mw", aggfunc="last")
    return wide.reindex(columns=list(TECHS))


@lru_cache(maxsize=1)
def capacity() -> pd.DataFrame:
    df = _read(("capacity/latest.parquet",))
    if not df.empty:
        df["month"] = pd.to_datetime(df["month"], utc=True)
    return df


def capacity_mw(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Installed MW per technology as usable at decision time: the value CAPACITY_LAG_MONTHS
    before the local delivery month. The dataset holds the newest revision of each month,
    not the first publication; for a stock of ~100 GW the later corrections of a month two
    back are small, but they are a known approximation (see README, Grenzen)."""
    cap = capacity()
    out = pd.DataFrame(index=index, columns=list(TECHS), dtype="float64")
    if cap.empty:
        return out
    naive = index.tz_convert("Europe/Berlin").tz_localize(None)   # local delivery month
    month = pd.DatetimeIndex(naive.to_period("M").to_timestamp()).tz_localize("UTC") \
        - pd.DateOffset(months=config.CAPACITY_LAG_MONTHS)
    for tech, name in config.CAPACITY_TYPE.items():
        series = cap[cap["type"] == name].set_index("month")["gw"].sort_index() * 1000
        if series.empty:
            continue
        out[tech] = series.reindex(month, method="ffill").to_numpy(dtype="float64")
    return out.astype("float64")
