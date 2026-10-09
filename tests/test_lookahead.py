"""The honesty test: anything published after the decision time must not move a feature.

We build the features for one delivery day, then rewrite every value that was not yet
known at the decision time (that day's and later day-ahead prices, ID-AEP of D-2 and
later, actual load, load forecasts of later days, capacity of months not yet usable,
every weather variable of archive values and complete runs published later) and
rebuild. The features must be identical. Run for a day covered by complete runs, for
the 100-quarter-hour DST day (archive values only), and for an early live decision
(as_of 10:40, with a run published at 10:50 that only the 11:00 decision may see).
Control checks confirm the test can see changes at all.

What this cannot test: whether the `available_at` stamps in the real weather dataset are
true. `python -m dps checks` tests that against the data (README, "Stimmen die
Zeitstempel der Wetterdaten?").
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dps import config, features, hf, panel, store
from dps.util import delivery_day, issue_time, local, qh_index

WX_BUMP = {"shortwave_radiation": lambda x: x * 3 + 50, "temperature_2m": lambda x: x + 10,
           "cloud_cover": lambda x: 100 - x}


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


def _weather_files(root):
    return sorted(Path(root / "hf" / "weather").rglob("*.parquet"))


def _kind(f: Path) -> str:
    """weather/<previous_runs|runs>/<model>/<year or month>/<file>.parquet"""
    return f.parts[-4]


def _publish_a_run_at(root, run: pd.Timestamp, available_at: pd.Timestamp, model="icon_eu") -> Path:
    f = root / "hf" / "weather" / "runs" / model / f"{run:%Y-%m}" / f"{run:%Y%m%dT%H}.parquet"
    w = pd.read_parquet(f)
    w["available_at"] = available_at
    w.to_parquet(f, index=False)
    return f


@pytest.mark.parametrize("offset, early_min", [(45, 0), (25, 0), (45, 20)],
                         ids=["complete-runs-day", "dst-day-100-qh", "live-as-of-10:40"])
def test_future_data_does_not_change_features(tmp_world, offset, early_min):
    root, start, end = tmp_world
    d = start + timedelta(days=offset)
    if offset == 25:
        assert len(qh_index(d)) == 100                     # 2025-10-26, clocks go back
    runs_cover = any(_kind(p) == "runs" for p in _weather_files(root)) and offset == 45
    decision = issue_time(d) - pd.Timedelta(minutes=early_min)
    as_of = decision if early_min else None
    if early_min:
        # a run published between the early decision (10:40) and 11:00: only 11:00 may use it
        run = pd.Timestamp(d - timedelta(days=1)).tz_localize("UTC") + pd.Timedelta(hours=6)
        _publish_a_run_at(root, run, decision + pd.Timedelta(minutes=10))
        assert not _features(start, end, d, None).equals(_features(start, end, d, as_of)), \
            "control: the 10:50 run must change the 11:00 features, else this case tests nothing"
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
    touched = {"previous_runs": 0, "runs": 0}
    for f in _weather_files(root):
        w = pd.read_parquet(f)
        late = pd.to_datetime(w["available_at"], utc=True) > decision
        if not late.any():
            continue
        ws = [c for c in w.columns if c.startswith("wind_speed_")][0]
        w.loc[late, ws] = w.loc[late, ws] + 40
        for c, fn in WX_BUMP.items():
            w.loc[late, c] = fn(w.loc[late, c])
        w.to_parquet(f, index=False)
        touched[_kind(f)] += int(late.sum())
    assert touched["previous_runs"] > 0
    if runs_cover:
        assert touched["runs"] > 0                         # the complete-run path is exercised too
    after = _features(start, end, d, as_of)
    pd.testing.assert_frame_equal(before, after)


def test_complete_runs_are_used_where_they_exist(tmp_world):
    """Control for the complete-run path: without the runs the features of a covered day change."""
    root, start, end = tmp_world
    d = start + timedelta(days=45)
    before = _features(start, end, d)
    for f in _weather_files(root):
        if _kind(f) == "runs":
            f.unlink()
    after = _features(start, end, d)
    assert not before.equals(after)


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
    assert not np.allclose(before["wind_on_mw"], after["wind_on_mw"])


def test_load_forecast_is_off_by_default(tmp_world):
    root, start, end = tmp_world
    d = start + timedelta(days=45)
    hf.weather.cache_clear()
    f = features.build(panel.build(start, end), d, d + timedelta(days=1))
    assert "load_da" not in f.columns and "resload_mw" not in f.columns
