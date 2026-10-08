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
