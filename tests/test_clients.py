"""HTTP clients against fake sessions: request shape, chunking, URL-form fallback, fetch -> store."""
from datetime import date

import pandas as pd
import pytest

from dps import config, entsoe, fetch, ntp, store


class Resp:
    def __init__(self, status=200, content=b"", payload=None):
        self.status_code, self.content, self._payload = status, content, payload

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


def a44_for(start: str, n_qh: int, price: float) -> bytes:
    pts = "".join(f"<Point><position>{i + 1}</position><price.amount>{price + i}</price.amount></Point>"
                  for i in range(n_qh))
    end = pd.Timestamp(start) + pd.Timedelta(minutes=15 * n_qh)
    return (f"<Publication_MarketDocument><TimeSeries><curveType>A01</curveType><Period>"
            f"<timeInterval><start>{start}</start><end>{end.strftime('%Y-%m-%dT%H:%MZ')}</end></timeInterval>"
            f"<resolution>PT15M</resolution>{pts}</Period></TimeSeries></Publication_MarketDocument>").encode()


class FakeEntsoe:
    def __init__(self):
        self.headers, self.calls = {}, []

    def get(self, url, params, timeout):
        self.calls.append(params)
        start = pd.Timestamp(params["periodStart"], tz="UTC")
        end = pd.Timestamp(params["periodEnd"], tz="UTC")
        n = int((end - start) / pd.Timedelta(minutes=15))
        return Resp(content=a44_for(start.strftime("%Y-%m-%dT%H:%MZ"), n, 40.0))


def test_entsoe_day_ahead_monthly_chunks(monkeypatch):
    monkeypatch.setenv("ENTSOE_API_KEY", "secret")
    s = FakeEntsoe()
    df = entsoe.Client(session=s, min_interval=0).day_ahead_prices(date(2026, 1, 30), date(2026, 2, 3))
    assert len(s.calls) == 2                                    # January part, February part
    p = s.calls[0]
    assert p["documentType"] == "A44" and p["in_Domain"] == config.EIC_DE_LU == p["out_Domain"]
    assert p["contract_MarketAgreement.type"] == "A01"
    assert len(df) == 4 * 96 and df["ts"].is_monotonic_increasing


class FakeNtp:
    def __init__(self):
        self.headers, self.gets = {}, []

    def post(self, url, data, timeout):
        assert data["grant_type"] == "client_credentials"
        return Resp(payload={"access_token": "tok", "expires_in": 3600})

    def get(self, url, headers, timeout):
        self.gets.append(url)
        assert headers["Authorization"] == "Bearer tok"
        if "?dateFrom=" not in url:
            return Resp(status=404)
        return Resp(content=("Datum von;(Uhrzeit) von;Zeitzone;(Uhrzeit) bis;Zeitzone;ID AEP in €/MWh\n"
                             "2026-01-31;23:00;UTC;23:15;UTC;77,7\n").encode())


def test_ntp_falls_back_to_query_form_and_remembers_it(monkeypatch):
    monkeypatch.setenv("NTP_CLIENT_ID", "id")
    monkeypatch.setenv("NTP_CLIENT_SECRET", "secret")
    s = FakeNtp()
    c = ntp.Client(session=s)
    c._last = -1e9
    df = c.id_aep(date(2026, 2, 1), date(2026, 2, 2))
    assert df["id_aep"].tolist() == [77.7]
    assert c._variant == "query"
    c.id_aep(date(2026, 2, 1), date(2026, 2, 2))
    assert s.gets[-1].count("?dateFrom=") == 1 and len(s.gets) == 3   # no second try of the path form


def test_fetch_writes_store_and_reports_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DPS_NOW", "2026-02-02T12:00Z")
    monkeypatch.setenv("ENTSOE_API_KEY", "secret")
    base = entsoe.Client

    class Offline(base):
        def __init__(self):
            super().__init__(session=FakeEntsoe(), min_interval=0)
    monkeypatch.setattr(entsoe, "Client", Offline)
    monkeypatch.delenv("NTP_CLIENT_ID", raising=False)
    monkeypatch.setattr(config, "START", date(2026, 1, 25))
    rep = fetch.run(sources=("da", "id_aep"))
    assert "rows fetched" in rep["da"]
    assert rep["id_aep"].startswith("ERROR")                    # one source down, the other still stored
    assert store.last_ts("da") is not None
    assert len(store.read("da")) == (date(2026, 2, 4) - date(2026, 1, 25)).days * 96
