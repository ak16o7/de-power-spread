"""The honesty test: anything published after the decision time must not move a feature.

We build the features for one delivery day, then rewrite every value that was not yet
known at 11:00 on D-1 (that day's and later day-ahead prices, ID-AEP of D-2 and later,
actual load, weather published later) and rebuild. The features must be identical.
A control check confirms the test can see changes at all.
"""
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from dps import config, features, hf, panel, store
from dps.util import delivery_day, issue_time


def _features(start, end, d):
    hf.weather.cache_clear()
    f = features.build(panel.build(start, end), d, d + timedelta(days=1))
    return f[features.feature_columns(f)]


def _rewrite(name, fn):
    df = store.read(name)
    df = fn(df, np.array(delivery_day(df["ts"])))
    df.to_parquet(store.path(name), index=False)


def test_future_data_does_not_change_features(tmp_world):
    root, start, end = tmp_world
    d = start + timedelta(days=45)
    issue = issue_time(d)
    before = _features(start, end, d)
    assert before.notna().mean().mean() > 0.8          # the test means something only with real values

    def bump(cols, mask_fn, delta):
        def fn(df, day):
            m = mask_fn(day)
            for c in cols:
                df.loc[m, c] = df.loc[m, c] + delta
            return df
        return fn
    _rewrite("da", bump(["da"], lambda day: day >= d, 1000.0))
    _rewrite("id_aep", bump(["id_aep"], lambda day: day >= d - timedelta(days=2), 1000.0))
    _rewrite("load", bump(["load_actual"], lambda day: np.ones(len(day), bool), 5000.0))
    for f in Path(root / "hf" / "weather").rglob("*.parquet"):
        w = pd.read_parquet(f)
        late = w["available_at"] > issue
        ws = [c for c in w.columns if c.startswith("wind_speed_")][0]
        w.loc[late, ws] = w.loc[late, ws] + 40
        w.loc[late, "shortwave_radiation"] = w.loc[late, "shortwave_radiation"] * 3
        w.to_parquet(f, index=False)
    after = _features(start, end, d)
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
