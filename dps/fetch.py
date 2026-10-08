"""Fetch prices, load and ID-AEP into the local cache (data/).

Default is incremental: from the newest stored day minus `recent_days` (catches
late publications and revisions) up to the day after tomorrow. --full refetches
everything since config.START.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from . import config, entsoe, ntp, store
from .util import BERLIN, now

LOG = logging.getLogger(__name__)


def _from(name: str, full: bool, recent_days: int) -> date:
    last = None if full else store.last_ts(name)
    if last is None:
        return config.START
    return max(config.START, last.tz_convert(BERLIN).date() - timedelta(days=recent_days))


def run(full: bool = False, recent_days: int = 7, end: date | None = None,
        sources: tuple[str, ...] = ("da", "load", "id_aep")) -> dict:
    end = end or (now().tz_convert(BERLIN).date() + timedelta(days=2))
    report: dict[str, str] = {}
    ec = entsoe.Client()
    jobs = {
        "da": lambda a, b: ec.day_ahead_prices(a, b),
        "load": lambda a, b: ec.load(a, b),
        "id_aep": lambda a, b: ntp.Client().id_aep(a, b),
    }
    for name in sources:
        start = _from(name, full, recent_days)
        if start >= end:
            report[name] = "up to date"
            continue
        try:
            df = jobs[name](start, end)
            n = store.upsert(name, df)
            report[name] = f"{start}..{end}: {len(df)} rows fetched, {n} values new or changed"
        except Exception as exc:   # one source failing must not stop the others
            report[name] = f"ERROR {type(exc).__name__}: {str(exc)[:200]}"
        LOG.info("fetch %s: %s", name, report[name])
    return report
