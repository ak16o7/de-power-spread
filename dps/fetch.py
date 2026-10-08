"""Fetch prices, load and ID-AEP into the local cache (data/).

Sources: ENTSO-E (ENTSOE_API_KEY) and the netztransparenz WebAPI (NTP_CLIENT_ID/SECRET)
when credentials are set; otherwise keyless fallbacks: Energy-Charts for prices and load,
the CSV download of the netztransparenz ID-AEP page for the ID-AEP.

Default is incremental: from the newest stored day minus `recent_days` (catches
late publications and revisions) up to the day after tomorrow. --full refetches
everything since config.START.
"""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from . import config, energycharts, entsoe, ntp, store
from .util import BERLIN, now

LOG = logging.getLogger(__name__)


def _from(name: str, full: bool, recent_days: int) -> date:
    last = None if full else store.last_ts(name)
    if last is None:
        return config.START
    return max(config.START, last.tz_convert(BERLIN).date() - timedelta(days=recent_days))


def _jobs() -> dict:
    if os.environ.get("ENTSOE_API_KEY", "").strip():
        ec = entsoe.Client()
        prices, load = ("ENTSO-E", ec.day_ahead_prices), ("ENTSO-E", ec.load)
    else:
        ch = energycharts.Client()
        prices, load = ("Energy-Charts", ch.day_ahead_prices), ("Energy-Charts", ch.load)
    if ntp.configured():
        id_aep = ("netztransparenz WebAPI", lambda a, b: ntp.Client().id_aep(a, b))
    else:
        id_aep = ("netztransparenz CSV", ntp.public_id_aep)
    return {"da": prices, "load": load, "id_aep": id_aep}


def run(full: bool = False, recent_days: int = 7, end: date | None = None,
        sources: tuple[str, ...] = ("da", "load", "id_aep")) -> dict:
    end = end or (now().tz_convert(BERLIN).date() + timedelta(days=2))
    report: dict[str, str] = {}
    jobs = _jobs()
    for name in sources:
        start = _from(name, full, recent_days)
        if start >= end:
            report[name] = "up to date"
            continue
        label, fn = jobs[name]
        try:
            df = fn(start, end)
            n = store.upsert(name, df)
            report[name] = f"{label} {start}..{end}: {len(df)} rows fetched, {n} values new or changed"
        except Exception as exc:   # one source failing must not stop the others
            report[name] = f"ERROR {label}: {type(exc).__name__}: {str(exc)[:200]}"
        LOG.info("fetch %s: %s", name, report[name])
    return report
