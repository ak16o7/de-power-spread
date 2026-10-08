"""The honesty test: anything published after the decision time must not move a feature.

We build the features for one delivery day, then rewrite every value that was not yet
known at the decision time (that day's and later day-ahead prices, ID-AEP of D-2 and
later, actual load, load forecasts of later days, capacity of months not yet usable,
weather published later) and rebuild. The features must be identical. Run for a normal
day, for the 100-quarter-hour DST day, and for an early live decision (as_of < 11:00).
A control check confirms the test can see changes at all.

What this cannot test: whether the `available_at` stamps in the real weather dataset are
true. That is checked against the real data (README, "Woher die Daten kommen").
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dps import config, features, hf, panel, store
from dps.util import delivery_day, issue_time, qh_index


def _features(start, end, d, as_of=None, use_load=True):
    hf.weather.cache_clear()
    hf.capacity.cache_clear()
    f = features.build(panel.build(start, end), d, d + timedelta(days=1), as_of=as_of, use_load_forecast=use_load)
    return f[features.feature_columns(f)]


def _rewrite(name, fn):
    df = store.read(name)
    df = fn(df, np.array(delivery_day(df["ts"])))
    df.to_parquet(store.path(name), index=False)


def _bump(cols, mask_fn, delta):
    def fn(df, day):
        m = mask_fn(day)
        for c in cols:
            df.loc[m, c] = df.loc[m, c] + delta
        return df
    return fn


@pytest.mark.parametrize("offset, early_min", [(45, 0), (25, 0), (45, 20)],
                         ids=["normal-day", "dst-day-100-qh", "live-as-of-10:40"])
def test_future_data_does_not_change_features(tmp_world, offset, early_min):
    root, start, end = tmp_world
    d = start + timedelta(days=offset)
    if offset == 25:
        assert len(qh_index(d)) == 100                     # 2025-10-26, clocks go back
    decision = issue_time(d) - pd.Timedelta(minutes=early_min)
    as_of = decision if early_min else None
    before = _features(start, end, d, as_of)
    assert before.notna().mean().mean() > 0.75             # the test means something only with real values

    _rewrite("da", _bump(["da"], lambda day: day >= d, 1000.0))
    _rewrite("id_aep", _bump(["id_aep"], lambda day: day >= d - timedelta(days=2), 1000.0))
    _rewrite("load", _bump(["load_actual"], lambda day: np.ones(len(day), bool), 5000.0))
    _rewrite("load", _bump(["load_da"], lambda day: day > d, 5000.0))   # forecasts of later days
    cap_path = Path(root / "hf" / "capacity" / "latest.parquet")
    cap = pd.read_parquet(cap_path)
    usable = pd.Timestamp(date(d.year, d.month, 1), tz="UTC") - pd.DateOffset(months=config.CAPACITY_LAG_MONTHS)
    cap.loc[pd.to_datetime(cap["month"], utc=True) > usable, "gw"] *= 3
    cap.to_parquet(cap_path, index=False)
    for f in Path(root / "hf" / "weather").rglob("*.parquet"):
        w = pd.read_parquet(f)
        late = w["available_at"] > decision
        ws = [c for c in w.columns if c.startswith("wind_speed_")][0]
        w.loc[late, ws] = w.loc[late, ws] + 40
        w.loc[late, "shortwave_radiation"] = w.loc[late, "shortwave_radiation"] * 3
        w.to_parquet(f, index=False)
    after = _features(start, end, d, as_of)
    pd.testing.assert_frame_equal(before, after)


def test_control_known_data_does_change_features(tmp_world):
    root, start, end = tmp_world
    d = start + timedelta(days=45)
    before = _features(start, end, d)
    known_day = d - timedelta(days=3)

    def fn(df, day):
        df.loc[day == known_day, "id_aep"] += 500.0
        return df
    _rewrite("id_aep", fn)
    after = _features(start, end, d)
    assert not np.allclose(before["sp_slot_last"], after["sp_slot_last"])


def test_control_usable_capacity_does_change_features(tmp_world):
    root, start, end = tmp_world
    d = start + timedelta(days=45)
    before = _features(start, end, d)
    cap_path = Path(root / "hf" / "capacity" / "latest.parquet")
    cap = pd.read_parquet(cap_path)
    cap["gw"] *= 2
    cap.to_parquet(cap_path, index=False)
    after = _features(start, end, d)
    assert not np.allclose(before["solar_mw"].fillna(0), after["solar_mw"].fillna(0)) or before["solar_mw"].isna().all()
    assert not np.allclose(before["wind_on_mw"], after["wind_on_mw"])


def test_load_forecast_is_off_by_default(tmp_world):
    root, start, end = tmp_world
    d = start + timedelta(days=45)
    hf.weather.cache_clear()
    f = features.build(panel.build(start, end), d, d + timedelta(days=1))
    assert "load_da" not in f.columns and "resload_mw" not in f.columns
