import numpy as np
import pandas as pd
import pytest

from dps import config, store, trading
from dps.explain import ols_hac
from dps.report import update_section


def test_pnl_by_hand():
    side = [1, -1, 0, 1, 1]
    da = [50.0, 50.0, 50.0, 50.0, np.nan]
    ida = [60.0, 60.0, 60.0, np.nan, 70.0]
    r = trading.pnl(side, da, ida, size_mw=10, fee=0.25, slippage=1.0, penalty=10.0)
    e = 10 * 0.25                                             # 2.5 MWh per quarter hour
    assert r["mwh"].tolist() == [e, e, 0, e, 0]              # no day-ahead price: no trade
    assert r["gross"].tolist() == pytest.approx([10 * e, -10 * e, 0, -10 * e, 0])
    assert r["net"].iloc[0] == pytest.approx(10 * e - 0.5 * e - 1.0 * e)
    assert r["net"].iloc[1] == pytest.approx(-10 * e - 0.5 * e - 1.0 * e)
    assert r["missing_exit"].tolist() == [False, False, False, True, False]
    assert r["net"].iloc[3] == pytest.approx(-10 * e - 0.5 * e)   # penalty, fees, no slippage


def test_store_upsert_keeps_first_seen_and_ignores_nan(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    ts = pd.date_range("2026-01-01", periods=3, freq="15min", tz="UTC")
    monkeypatch.setenv("DPS_NOW", "2026-01-02T00:00Z")
    assert store.upsert("id_aep", pd.DataFrame({"ts": ts, "id_aep": [1.0, 2.0, np.nan]})) == 2
    monkeypatch.setenv("DPS_NOW", "2026-01-03T00:00Z")
    n = store.upsert("id_aep", pd.DataFrame({"ts": ts, "id_aep": [1.0, np.nan, 3.0]}))
    assert n == 1                                              # only the new value counts
    df = store.read("id_aep").set_index("ts")
    assert df["id_aep"].tolist() == [1.0, 2.0, 3.0]           # NaN never overwrites a value
    assert (df["first_seen"].iloc[:2] == pd.Timestamp("2026-01-02", tz="UTC")).all()
    assert df["fetched_at"].iloc[2] == pd.Timestamp("2026-01-03", tz="UTC")


def test_ols_hac_recovers_coefficients():
    rng = np.random.default_rng(0)
    n = 5000
    x = rng.normal(size=(n, 2))
    u = np.convolve(rng.normal(size=n + 20), np.ones(20) / 4, mode="valid")[:n]  # autocorrelated
    y = 1.0 + 2.0 * x[:, 0] - 3.0 * x[:, 1] + u
    res = ols_hac(y, np.column_stack([np.ones(n), x]), lags=30)
    assert res["beta"] == pytest.approx([1.0, 2.0, -3.0], abs=0.15)
    assert (res["se"] > 0).all()


def test_readme_section_update(tmp_path):
    p = tmp_path / "R.md"
    p.write_text("a\n<!-- RESULTS:START -->\nold\n<!-- RESULTS:END -->\nb\n")
    assert update_section(p, "RESULTS", "new")
    assert p.read_text() == "a\n<!-- RESULTS:START -->\nnew\n<!-- RESULTS:END -->\nb\n"
    assert not update_section(p, "LIVE", "x")


def test_max_drawdown_counts_from_zero():
    from dps.metrics import max_drawdown
    assert max_drawdown(pd.Series([-100.0, 50.0, -20.0])) == -100.0   # the start (0) is a peak
    assert max_drawdown(pd.Series([100.0, -30.0, -50.0, 10.0])) == -80.0
    assert max_drawdown(pd.Series([5.0, 5.0])) == 0.0


def test_archive_like_keeps_only_archive_leads_and_bounds():
    from dps import hf
    run = pd.Timestamp("2026-07-01 00:00", tz="UTC")
    valid = run + pd.to_timedelta([12, 24, 29, 30, 47, 48, 53, 54], unit="h")
    runs = pd.DataFrame({"point": "SH", "valid": valid, "run": run,
                         "available_at": run + pd.Timedelta(hours=3), "wind_speed_120m": 10.0})
    out = hf.archive_like(runs, "icon_eu")
    lead = ((out["valid"] - run) / pd.Timedelta(hours=1)).tolist()
    assert lead == [24, 29, 48, 53]
    assert out["lead_h"].tolist() == [24, 24, 48, 48]
    expect = out["valid"] - pd.to_timedelta(out["lead_h"], unit="h") + pd.Timedelta(hours=4.5)
    assert (out["available_at"] == expect.where(expect > run + pd.Timedelta(hours=3), run + pd.Timedelta(hours=3))).all()
    assert (out["available_at"] >= run + pd.Timedelta(hours=3)).all()


def test_capacity_uses_the_local_delivery_month(monkeypatch):
    from dps import hf
    months = pd.date_range("2025-09-01", "2026-02-01", freq="MS", tz="UTC")
    cap = pd.DataFrame({"month": months, "type": "Solar AC", "gw": np.arange(len(months), dtype=float) + 100})
    monkeypatch.setattr(hf, "capacity", lambda: cap)
    # 00:00 local on 1 January is 23:00 UTC on 31 December: still January locally
    idx = pd.DatetimeIndex([pd.Timestamp("2025-12-31 23:00", tz="UTC"), pd.Timestamp("2026-01-15 12:00", tz="UTC")])
    out = hf.capacity_mw(idx)
    assert out["solar"].tolist() == [102_000.0, 102_000.0]     # November 2025 = January - 2 months


def test_holidays_are_a_hard_dependency():
    from datetime import date
    from dps.features import _holidays
    h = _holidays([2025, 2026])
    assert date(2025, 12, 25) in h and date(2026, 10, 3) in h


def test_weather_vintage_check_identifies_the_run(tmp_path, monkeypatch):
    from datetime import date
    from dps import checks, hf
    monkeypatch.setenv("DPS_HF_LOCAL", str(tmp_path))
    valid = pd.date_range("2026-07-05", periods=6, freq="h", tz="UTC")
    def frame(seed):
        rng = np.random.default_rng(seed)
        return {c: rng.normal(size=len(valid)).round(1) + 10 for c in
                ("temperature_2m", "wind_speed_100m", "surface_pressure", "cloud_cover", "shortwave_radiation")}
    early, late = frame(1), frame(2)
    runs = pd.concat([
        pd.DataFrame({"point": "SH", "valid": valid, "run": valid - pd.Timedelta(hours=26), **early, "source": "archive",
                      "available_at": valid - pd.Timedelta(hours=26) + pd.Timedelta(hours=8.5)}),
        pd.DataFrame({"point": "SH", "valid": valid, "run": valid - pd.Timedelta(hours=10), **late, "source": "live",
                      "available_at": valid - pd.Timedelta(hours=10) + pd.Timedelta(hours=7)}),
        pd.DataFrame({"point": "SH", "valid": valid - pd.Timedelta(days=4), "run": valid - pd.Timedelta(days=4, hours=2),
                      **early, "source": "archive", "available_at": valid - pd.Timedelta(days=4)}),
    ])
    prev = pd.DataFrame({"point": "SH", "valid": valid, "lead_days": 1, "available_at": valid - pd.Timedelta(hours=15.5),
                         **{c: np.where(np.arange(len(valid)) < 5, early[c], late[c]) for c in early}})
    (tmp_path / "weather/runs/ecmwf_ifs/2026-07").mkdir(parents=True)
    (tmp_path / "weather/previous_runs/ecmwf_ifs/2026").mkdir(parents=True)
    runs.to_parquet(tmp_path / "weather/runs/ecmwf_ifs/2026-07/runs.parquet", index=False)
    prev.to_parquet(tmp_path / "weather/previous_runs/ecmwf_ifs/2026/2026-07.parquet", index=False)
    res = checks.weather_vintage("ecmwf_ifs", date(2026, 7, 1), date(2026, 7, 10))
    v = res["lead_days"]["1"]
    assert v["identified"] == 6 and v["lead_h"]["min"] == 10 and v["fresher_than_claimed"] == 1
    assert res["live_publication_delay_h"]["max"] == 7.0


def test_model_is_the_mean_of_its_seeds():
    from dps.model import SpreadModel
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(12_000, 3)), columns=["a", "b", "c"])   # > 10k rows: early stopping is on
    y = pd.Series(2 * X["a"] - X["b"] + rng.normal(size=len(X)))
    both = SpreadModel(seeds=(0, 1)).fit(X, y).predict(X)
    one = [SpreadModel(seeds=(s,)).fit(X, y).predict(X) for s in (0, 1)]
    assert np.allclose(both, (one[0] + one[1]) / 2)
    assert not np.allclose(one[0], one[1])          # the seed matters for a single fit
