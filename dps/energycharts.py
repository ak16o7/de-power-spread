"""Energy-Charts API (Fraunhofer ISE): keyless fallback for day-ahead prices and load.

Used when ENTSOE_API_KEY is not set. DE-LU day-ahead prices come from
Bundesnetzagentur | SMARD.de under CC BY 4.0; load and load forecast from Energy-Charts
(CC BY 4.0). The public API allows about 2 requests per minute, so calls are spaced.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta

import pandas as pd
import requests

from . import config
from .entsoe import to_quarter_hours
from .util import local

LOG = logging.getLogger(__name__)
BASE = "https://api.energy-charts.info"
CHUNK_DAYS = 92


def _points(unix_seconds: list[int], values: list, name: str) -> pd.DataFrame:
    """Series with irregular resolution (hourly before Oct 2025, then 15 min) -> quarter hours."""
    ts = pd.to_datetime(pd.Series(unix_seconds, dtype="int64"), unit="s", utc=True)
    val = pd.Series(values, dtype="float64")
    nxt = ts.shift(-1)
    minutes = ((nxt - ts) / pd.Timedelta(minutes=1)).fillna(15).clip(upper=60).astype(int)
    pts = pd.DataFrame({"ts": ts, "value": val, "minutes": minutes, "sequence": None}).dropna(subset=["value"])
    return to_quarter_hours(pts, name)


class Client:
    def __init__(self, session: requests.Session | None = None, min_interval: float = 31.0) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", config.USER_AGENT)
        self.min_interval = min_interval
        self._last = -1e9

    def get(self, path: str, params: dict) -> dict:
        for attempt in range(5):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self.session.get(f"{BASE}{path}", params=params, timeout=180)
            except requests.RequestException as exc:
                LOG.warning("Energy-Charts network %s, retry", type(exc).__name__)
                continue
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 60)))
                continue
            if r.status_code == 404:
                return {}
            if r.status_code != 200:
                raise RuntimeError(f"Energy-Charts {path}: HTTP {r.status_code}")
            return r.json()
        raise RuntimeError(f"Energy-Charts {path}: failed after retries")

    def _chunked(self, fn, start: date, end: date, name: str) -> pd.DataFrame:
        frames, d = [], start
        while d < end:
            e = min(end, d + timedelta(days=CHUNK_DAYS))
            frames.append(fn(d, e))
            d = e
        frames = [f for f in frames if not f.empty]
        if not frames:
            return pd.DataFrame(columns=["ts", name])
        df = pd.concat(frames, ignore_index=True).drop_duplicates("ts", keep="last")
        return df[(df["ts"] >= local(start)) & (df["ts"] < local(end))].sort_values("ts").reset_index(drop=True)

    def day_ahead_prices(self, start: date, end: date) -> pd.DataFrame:
        def one(a: date, b: date) -> pd.DataFrame:
            j = self.get("/price", {"bzn": "DE-LU", "start": str(a), "end": str(b - timedelta(days=1))})
            return _points(j.get("unix_seconds") or [], j.get("price") or [], "da") if j else pd.DataFrame()
        return self._chunked(one, start, end, "da")

    def load(self, start: date, end: date) -> pd.DataFrame:
        def actual(a: date, b: date) -> pd.DataFrame:
            j = self.get("/public_power", {"country": "de", "start": str(a), "end": str(b - timedelta(days=1))})
            series = next((p["data"] for p in j.get("production_types", []) if p["name"] == "Load"), None)
            return _points(j["unix_seconds"], series, "load_actual") if series else pd.DataFrame()

        def forecast(a: date, b: date) -> pd.DataFrame:
            j = self.get("/public_power_forecast", {"country": "de", "production_type": "load",
                                                     "forecast_type": "day-ahead",
                                                     "start": str(a), "end": str(b - timedelta(days=1))})
            return _points(j["unix_seconds"], j["forecast_values"], "load_da") if j.get("unix_seconds") else pd.DataFrame()
        act = self._chunked(actual, start, end, "load_actual")
        fc = self._chunked(forecast, start, end, "load_da")
        return act.merge(fc, on="ts", how="outer").sort_values("ts").reset_index(drop=True)
