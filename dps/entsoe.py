"""ENTSO-E Transparency Platform: day-ahead prices (A44) and load (A65).

Needs ENTSOE_API_KEY. Parser handles curveType A03 (omitted positions repeat the
previous value), mixed PT15M/PT60M series (the finer one wins) and zip answers.
"""
from __future__ import annotations

import io
import logging
import math
import os
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests

from . import config
from .util import UTC, local, month_starts

LOG = logging.getLogger(__name__)


class NoData(Exception):
    """ENTSO-E answered 'No matching data found'."""


def _mask(text: str) -> str:
    key = os.environ.get("ENTSOE_API_KEY", "")
    text = text.replace(key, "***") if key else text
    return re.sub(r"securityToken=[^&\s]+", "securityToken=***", text)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(elem: ET.Element, name: str) -> str | None:
    for node in elem.iter():
        if _local(node.tag) == name and node.text:
            return node.text.strip()
    return None


def _step(resolution: str | None) -> timedelta:
    m = re.fullmatch(r"PT(\d+)([MH])", resolution or "")
    if not m:
        raise ValueError(f"unsupported resolution {resolution!r}")
    n = int(m.group(1))
    return timedelta(minutes=n) if m.group(2) == "M" else timedelta(hours=n)


def _docs(content: bytes) -> list[bytes]:
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return [zf.read(n) for n in zf.namelist() if n.lower().endswith(".xml")]
    return [content]


def parse(content: bytes, value_tag: str) -> pd.DataFrame:
    """All points of all TimeSeries as rows (ts, value, minutes, sequence).

    value_tag: "price.amount" for A44, "quantity" for A65.
    """
    rows = []
    for doc in _docs(content):
        root = ET.fromstring(doc)
        if _local(root.tag).lower() == "acknowledgement_marketdocument":
            reason = _text(root, "text") or "acknowledgement"
            if "no matching data" in reason.lower():
                raise NoData(reason)
            raise RuntimeError(f"ENTSO-E: {_mask(reason)}")
        for series in (n for n in root.iter() if _local(n.tag) == "TimeSeries"):
            curve = _text(series, "curveType")
            seq_val = None   # several auctions per zone are numbered; None if not given
            for n in series.iter():
                if _local(n.tag) == "classificationSequence_AttributeInstanceComponent.position" and n.text:
                    seq_val = int(n.text.strip())
            for period in (n for n in series.iter() if _local(n.tag) == "Period"):
                start = pd.Timestamp(_text(period, "start")).tz_convert(UTC)
                end_txt = _text(period, "end")
                end = pd.Timestamp(end_txt).tz_convert(UTC) if end_txt else None
                res = _text(period, "resolution")
                step = _step(res)
                pts = []
                for p in (n for n in period.iter() if _local(n.tag) == "Point"):
                    try:
                        pos, val = int(_text(p, "position")), float(_text(p, value_tag))
                    except (TypeError, ValueError):
                        continue
                    if pos >= 1 and math.isfinite(val):
                        pts.append((pos, val))
                pts.sort()
                for i, (pos, val) in enumerate(pts):
                    repeat = 1
                    if curve == "A03":
                        if i + 1 < len(pts):
                            repeat = max(1, pts[i + 1][0] - pos)
                        elif end is not None:
                            repeat = max(1, int((end - (start + (pos - 1) * step)) / step))
                    for k in range(repeat):
                        t = start + (pos - 1 + k) * step
                        if end is not None and t >= end:
                            break
                        rows.append((t, val, int(step / timedelta(minutes=1)), seq_val))
    return pd.DataFrame(rows, columns=["ts", "value", "minutes", "sequence"])


def to_quarter_hours(points: pd.DataFrame, name: str) -> pd.DataFrame:
    """One value per quarter hour. Hourly points cover their four quarters; where a
    quarter-hourly value exists for the same quarter it wins. Lowest sequence wins next."""
    if points.empty:
        return pd.DataFrame(columns=["ts", name])
    out = []
    for t, v, minutes, seq in points.itertuples(index=False):
        n = max(1, minutes // 15)
        for k in range(n):
            out.append((t + timedelta(minutes=15 * k), v, minutes, 99 if seq is None or pd.isna(seq) else seq))
    df = pd.DataFrame(out, columns=["ts", name, "minutes", "seq"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.sort_values(["ts", "minutes", "seq"], kind="stable").drop_duplicates("ts", keep="first")
    return df[["ts", name]].reset_index(drop=True)


class Client:
    def __init__(self, session: requests.Session | None = None, min_interval: float = 0.2) -> None:
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", config.USER_AGENT)
        self.min_interval = min_interval     # ENTSO-E allows 400 requests/min per IP
        self._last = 0.0

    def get(self, params: dict, start: pd.Timestamp, end: pd.Timestamp) -> bytes:
        key = os.environ.get("ENTSOE_API_KEY", "").strip()
        if not key:
            raise RuntimeError("ENTSOE_API_KEY is not set")
        payload = dict(params, securityToken=key,
                       periodStart=start.tz_convert(UTC).strftime("%Y%m%d%H%M"),
                       periodEnd=end.tz_convert(UTC).strftime("%Y%m%d%H%M"))
        err = "?"
        for attempt in range(5):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self.session.get(config.ENTSOE_ENDPOINT, params=payload, timeout=90)
            except requests.RequestException as exc:
                err = f"network: {type(exc).__name__}"
            else:
                if r.content[:2] != b"PK" and b"No matching data" in r.content[:4000]:
                    raise NoData("No matching data found")
                if r.status_code == 200:
                    return r.content
                if r.status_code in (400, 401, 403):
                    raise RuntimeError(_mask(f"ENTSO-E {r.status_code}: {r.content[:300].decode('utf-8', 'ignore')}"))
                err = f"HTTP {r.status_code}"
            LOG.warning("ENTSO-E %s, retry %d", err, attempt + 1)
            time.sleep(min(60, 5 * 2 ** attempt))
        raise RuntimeError(f"ENTSO-E failed after retries ({err})")

    def _monthly(self, params: dict, value_tag: str, name: str, start: date, end: date) -> pd.DataFrame:
        frames = []
        for m in month_starts(start, end - timedelta(days=1)):
            a = max(local(m), local(start))
            nxt = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
            b = min(local(nxt), local(end))
            try:
                frames.append(to_quarter_hours(parse(self.get(params, a, b), value_tag), name))
            except NoData:
                LOG.info("ENTSO-E %s: no data %s..%s", name, a, b)
        if not frames:
            return pd.DataFrame(columns=["ts", name])
        df = pd.concat(frames, ignore_index=True).drop_duplicates("ts", keep="last")
        return df[(df["ts"] >= local(start)) & (df["ts"] < local(end))].reset_index(drop=True)

    def day_ahead_prices(self, start: date, end: date) -> pd.DataFrame:
        """DE-LU day-ahead clearing prices, EUR/MWh, per quarter hour [start, end)."""
        params = {"documentType": "A44", "in_Domain": config.EIC_DE_LU, "out_Domain": config.EIC_DE_LU,
                  "contract_MarketAgreement.type": "A01"}
        return self._monthly(params, "price.amount", "da", start, end)

    def load(self, start: date, end: date) -> pd.DataFrame:
        """Germany total load: actual (A16) and day-ahead forecast (A01), MW per quarter hour."""
        actual = self._monthly({"documentType": "A65", "processType": "A16",
                                "outBiddingZone_Domain": config.EIC_DE}, "quantity", "load_actual", start, end)
        fc = self._monthly({"documentType": "A65", "processType": "A01",
                            "outBiddingZone_Domain": config.EIC_DE}, "quantity", "load_da", start, end)
        return actual.merge(fc, on="ts", how="outer").sort_values("ts").reset_index(drop=True)
