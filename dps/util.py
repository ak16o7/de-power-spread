"""Time helpers. All stored timestamps are UTC; decisions are made in Berlin local time."""
from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import config

UTC = timezone.utc
BERLIN = ZoneInfo("Europe/Berlin")


def now() -> pd.Timestamp:
    """UTC now; DPS_NOW=2026-10-08T09:00Z pins it (tests, replays)."""
    fixed = os.environ.get("DPS_NOW")
    if fixed:
        return pd.Timestamp(fixed).tz_convert(UTC)
    return pd.Timestamp(datetime.now(UTC))


def local(day: date, hour: float = 0.0) -> pd.Timestamp:
    """Local Berlin wall-clock time on `day` (+hour) as a UTC timestamp. DST-safe."""
    naive = pd.Timestamp(day) + pd.Timedelta(hours=hour)
    return naive.tz_localize(BERLIN, ambiguous=True, nonexistent="shift_forward").tz_convert(UTC)


def qh_index(day: date) -> pd.DatetimeIndex:
    """Quarter-hour starts (UTC) of one local delivery day: 92, 96 or 100 of them."""
    return pd.date_range(local(day), local(day + timedelta(days=1)), freq="15min", inclusive="left")


def days(start: date, end: date) -> list[date]:
    """Delivery days start <= d < end."""
    return [start + timedelta(days=i) for i in range((end - start).days)]


def issue_time(day: date) -> pd.Timestamp:
    """Decision time for delivery day `day`: 11:00 local on the day before."""
    return local(day - timedelta(days=1), config.ISSUE_HOUR)


def gate_closure(day: date) -> pd.Timestamp:
    return local(day - timedelta(days=1), config.GATE_CLOSURE_HOUR)


def da_known_at(day: date) -> pd.Timestamp:
    return local(day - timedelta(days=1), config.DA_KNOWN_HOURS_AFTER_PREV_MIDNIGHT)


def spread_known_at(day: date) -> pd.Timestamp:
    return local(day + timedelta(days=config.SPREAD_KNOWN_DAYS_AFTER))


def delivery_day(ts: pd.DatetimeIndex | pd.Series) -> np.ndarray:
    """Local calendar day of each UTC quarter-hour start."""
    idx = pd.DatetimeIndex(ts).tz_convert(BERLIN)
    return np.array([d.date() for d in idx])


def slot(ts: pd.DatetimeIndex) -> np.ndarray:
    """Local clock quarter of the day, 0..95. The repeated hour in October maps twice."""
    idx = pd.DatetimeIndex(ts).tz_convert(BERLIN)
    return np.asarray(idx.hour * 4 + idx.minute // 15)


def month_starts(first: date, last: date) -> list[date]:
    """First days of the months from `first`'s month to `last`'s month."""
    out, m = [], date(first.year, first.month, 1)
    while m <= last:
        out.append(m)
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return out


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for noisy in ("urllib3", "huggingface_hub", "filelock", "matplotlib", "httpx", "httpx2"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
