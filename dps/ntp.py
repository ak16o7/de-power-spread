"""netztransparenz.de: the ID-AEP (Index Ausgleichsenergiepreis), our exit price.

ID-AEP per quarter hour = volume-weighted price of the last 500 MW traded in the
German continuous intraday market (quarter-hour and hour products) before delivery.
Undefined if 500 MW are not reached in that quarter hour.

Access: free OAuth2 client credentials from https://extranet.netztransparenz.de
-> NTP_CLIENT_ID / NTP_CLIENT_SECRET (same names as in de-power-desk).
Published limit: 2 requests/s per IP; repeated violations block the IP for 2 h.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from . import config
from .util import UTC, local

LOG = logging.getLogger(__name__)
ID_AEP_PATH = "IdAep"
_OFFSETS = {"UTC": 0, "GMT": 0, "CET": 1, "MEZ": 1, "CEST": 2, "MESZ": 2}


def _num(raw: str | None) -> float | None:
    if raw is None:
        return None
    raw = raw.strip().strip('"')
    if not raw or raw.upper() in ("N.A.", "NA", "N/A", "-", "NAN"):
        return None
    try:
        return float(raw.replace(".", "").replace(",", ".")) if "," in raw else float(raw)
    except ValueError:
        return None


def _date(raw: str) -> date:
    raw = raw.strip().strip('"')
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"netztransparenz: unknown date {raw!r}")


def parse_id_aep(text: str) -> pd.DataFrame:
    """ID-AEP CSV -> (ts UTC quarter-hour start, id_aep EUR/MWh; NaN where undefined).

    Documented header: "Datum von;(Uhrzeit) von;Zeitzone;(Uhrzeit) bis;Zeitzone;ID AEP in €/MWh".
    The parser finds columns by name, so the reBAP-style header (Datum;Zeitzone;von;...) works too.
    """
    lines = [ln for ln in text.lstrip("﻿").splitlines() if ln.strip()]
    if not lines:
        return pd.DataFrame(columns=["ts", "id_aep"])
    header = [h.strip().strip('"').lower() for h in lines[0].split(";")]
    i_date = next(i for i, h in enumerate(header) if "datum" in h)
    i_time = next(i for i, h in enumerate(header) if "von" in h and "datum" not in h)
    tz_cols = [i for i, h in enumerate(header) if "zeitzone" in h]
    i_value = next((i for i, h in enumerate(header) if "aep" in h), len(header) - 1)
    rows = []
    for ln in lines[1:]:
        cells = ln.split(";")
        if len(cells) <= max(i_date, i_time, i_value):
            continue
        day = _date(cells[i_date])
        hh, mm = (int(x) for x in cells[i_time].strip().strip('"').split(":")[:2])
        tz = cells[tz_cols[0]].strip().strip('"').upper() if tz_cols else "UTC"
        if tz not in _OFFSETS:
            raise ValueError(f"netztransparenz: unknown time zone {tz!r}")
        ts = pd.Timestamp(datetime(day.year, day.month, day.day, hh, mm), tz=UTC) - pd.Timedelta(hours=_OFFSETS[tz])
        rows.append((ts, _num(cells[i_value])))
    df = pd.DataFrame(rows, columns=["ts", "id_aep"])
    df["id_aep"] = df["id_aep"].astype("float64")
    return df.drop_duplicates("ts", keep="last").sort_values("ts").reset_index(drop=True)


class Client:
    """OAuth2 client credentials; tries both documented date-range URL forms."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", config.USER_AGENT)
        self._token: str | None = None
        self._expires = 0.0
        self._last = 0.0
        self._variant: str | None = None

    def _get_token(self) -> str:
        if self._token and time.time() < self._expires - 60:
            return self._token
        cid = os.environ.get("NTP_CLIENT_ID", "").strip()
        secret = os.environ.get("NTP_CLIENT_SECRET", "").strip()
        if not (cid and secret):
            raise RuntimeError("NTP_CLIENT_ID / NTP_CLIENT_SECRET are not set")
        r = self.session.post(config.NTP_TOKEN_URL, data={"grant_type": "client_credentials",
                                                          "client_id": cid, "client_secret": secret}, timeout=30)
        if not r.ok:
            raise RuntimeError(f"netztransparenz token: HTTP {r.status_code}")
        data = r.json()
        self._token = data["access_token"]
        self._expires = time.time() + float(data.get("expires_in", 3600))
        return self._token

    def _url(self, path: str, a: pd.Timestamp, b: pd.Timestamp, variant: str) -> str:
        fmt = "%Y-%m-%dT%H:%M:%S"
        f, t = a.tz_convert(UTC).strftime(fmt), b.tz_convert(UTC).strftime(fmt)
        if variant == "path":
            return f"{config.NTP_BASE_URL}/{path}/{f}/{t}"
        return f"{config.NTP_BASE_URL}/{path}?dateFrom={f}&dateTo={t}"

    def get(self, path: str, a: pd.Timestamp, b: pd.Timestamp) -> str | None:
        token = self._get_token()
        variants = [self._variant] if self._variant else ["path", "query"]
        last = None
        for variant in variants:
            for attempt in range(4):
                wait = 0.6 - (time.monotonic() - self._last)
                if wait > 0:
                    time.sleep(wait)
                self._last = time.monotonic()
                try:
                    r = self.session.get(self._url(path, a, b, variant), timeout=60,
                                         headers={"Authorization": f"Bearer {token}", "Accept": "text/csv"})
                except requests.RequestException as exc:
                    LOG.warning("netztransparenz network %s, retry", type(exc).__name__)
                    time.sleep(3 * (attempt + 1))
                    continue
                if r.status_code >= 500 or r.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                break
            else:
                raise RuntimeError(f"netztransparenz {path}: failed after retries")
            if r.status_code in (400, 404, 405) and len(variants) > 1:
                last = r
                continue
            if r.status_code == 401:
                self._token = None
                raise RuntimeError("netztransparenz: 401 unauthorized (client id/secret or API scope)")
            if r.status_code == 204 or (r.ok and not r.content.strip()):
                self._variant = variant
                return None
            if not r.ok:
                raise RuntimeError(f"netztransparenz {path}: HTTP {r.status_code}")
            text = r.content.decode("utf-8-sig", "replace")
            if text.lstrip().startswith(("<", "{")):
                raise ValueError("netztransparenz: expected CSV, got HTML/JSON")
            self._variant = variant
            return text
        raise RuntimeError(f"netztransparenz {path}: HTTP {getattr(last, 'status_code', '?')} for all URL forms")

    def id_aep(self, start: date, end: date, chunk_days: int = 31) -> pd.DataFrame:
        """ID-AEP per quarter hour of the local delivery days [start, end)."""
        frames, d = [], start
        while d < end:
            e = min(end, d + timedelta(days=chunk_days))
            text = self.get(ID_AEP_PATH, local(d), local(e))
            if text:
                frames.append(parse_id_aep(text))
            d = e
        if not frames:
            return pd.DataFrame(columns=["ts", "id_aep"])
        df = pd.concat(frames, ignore_index=True).drop_duplicates("ts", keep="last")
        return df[(df["ts"] >= local(start)) & (df["ts"] < local(end))].reset_index(drop=True)
