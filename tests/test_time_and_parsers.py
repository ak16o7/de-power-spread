import io
import zipfile
from datetime import date

import numpy as np
import pandas as pd
import pytest

from dps import entsoe, ntp, util


# ----------------------------------------------------------------------------- time
@pytest.mark.parametrize("day,n", [(date(2026, 3, 29), 92), (date(2026, 10, 25), 100), (date(2026, 6, 1), 96)])
def test_quarter_hours_per_local_day(day, n):
    idx = util.qh_index(day)
    assert len(idx) == n
    assert idx[0] == util.local(day)


def test_issue_time_is_11_local_on_the_day_before():
    assert util.issue_time(date(2026, 7, 2)) == pd.Timestamp("2026-07-01 09:00", tz="UTC")   # CEST
    assert util.issue_time(date(2026, 1, 2)) == pd.Timestamp("2026-01-01 10:00", tz="UTC")   # CET
    assert util.issue_time(date(2026, 3, 30)) == pd.Timestamp("2026-03-29 09:00", tz="UTC")  # day after spring DST


def test_spread_of_d_minus_3_is_the_newest_known_at_decision():
    d = date(2026, 5, 10)
    issue = util.issue_time(d)
    assert util.spread_known_at(date(2026, 5, 7)) <= issue
    assert util.spread_known_at(date(2026, 5, 8)) > issue


def test_da_price_of_previous_day_is_known_but_not_of_the_day_itself():
    d = date(2026, 5, 10)
    assert util.da_known_at(date(2026, 5, 9)) <= util.issue_time(d)
    assert util.da_known_at(d) > util.issue_time(d)


# ----------------------------------------------------------------------------- ENTSO-E
A44 = b"""<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
 <TimeSeries>
  <curveType>A03</curveType>
  <Period>
   <timeInterval><start>2026-05-01T22:00Z</start><end>2026-05-01T23:00Z</end></timeInterval>
   <resolution>PT15M</resolution>
   <Point><position>1</position><price.amount>50.5</price.amount></Point>
   <Point><position>3</position><price.amount>-10</price.amount></Point>
  </Period>
 </TimeSeries>
 <TimeSeries>
  <curveType>A01</curveType>
  <Period>
   <timeInterval><start>2026-05-01T22:00Z</start><end>2026-05-02T00:00Z</end></timeInterval>
   <resolution>PT60M</resolution>
   <Point><position>1</position><price.amount>99</price.amount></Point>
   <Point><position>2</position><price.amount>70</price.amount></Point>
  </Period>
 </TimeSeries>
</Publication_MarketDocument>"""


def test_a44_curve_a03_and_finer_resolution_wins():
    df = entsoe.to_quarter_hours(entsoe.parse(A44, "price.amount"), "da").set_index("ts")["da"]
    t0 = pd.Timestamp("2026-05-01 22:00", tz="UTC")
    q = pd.Timedelta(minutes=15)
    # quarter-hourly series: positions 1,2 = 50.5 (A03 repeat), 3,4 = -10 (repeat to period end)
    assert df[t0] == 50.5 and df[t0 + q] == 50.5 and df[t0 + 2 * q] == -10 and df[t0 + 3 * q] == -10
    # second hour only exists hourly: expanded to four quarters
    assert all(df[t0 + k * q] == 70 for k in range(4, 8))
    assert len(df) == 8


def test_a44_in_zip_and_no_data():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.xml", A44)
    assert len(entsoe.parse(buf.getvalue(), "price.amount")) > 0
    ack = b"""<Acknowledgement_MarketDocument xmlns="x"><Reason><code>999</code>
    <text>No matching data found for Data item</text></Reason></Acknowledgement_MarketDocument>"""
    with pytest.raises(entsoe.NoData):
        entsoe.parse(ack, "price.amount")


# ----------------------------------------------------------------------------- netztransparenz
def test_id_aep_documented_format():
    text = ("Datum von;(Uhrzeit) von;Zeitzone;(Uhrzeit) bis;Zeitzone;ID AEP in €/MWh\n"
            "2023-07-01;00:00;UTC;00:15;UTC;90,30\n"
            "2023-07-01;00:15;UTC;00:30;UTC;\n"
            "2023-07-01;00:30;UTC;00:45;UTC;1.234,56\n"
            "2023-07-01;00:45;UTC;01:00;UTC;-12,5\n")
    df = ntp.parse_id_aep(text).set_index("ts")["id_aep"]
    t0 = pd.Timestamp("2023-07-01 00:00", tz="UTC")
    assert df[t0] == pytest.approx(90.30)
    assert np.isnan(df[t0 + pd.Timedelta(minutes=15)])          # undefined (< 500 MW): NaN, not 0
    assert df[t0 + pd.Timedelta(minutes=30)] == pytest.approx(1234.56)
    assert df[t0 + pd.Timedelta(minutes=45)] == pytest.approx(-12.5)


def test_id_aep_other_header_and_local_time_zone():
    text = "﻿Datum;Zeitzone;von;bis;ID AEP\n01.07.2023;CEST;02:00;02:15;55,5\n"
    df = ntp.parse_id_aep(text)
    assert df["ts"].iloc[0] == pd.Timestamp("2023-07-01 00:00", tz="UTC")
    assert df["id_aep"].iloc[0] == pytest.approx(55.5)
