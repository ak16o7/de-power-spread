"""End to end on synthetic worlds: the pipeline finds a planted signal, invents none in
noise, never trains on labels it could not have known, and live settles like the backtest."""
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from dps import backtest, explain, live, report, store, trading
from dps.util import issue_time


def test_finds_planted_signal(planted):
    root, start, end = planted
    out = backtest.run(start, end)
    m = out["strategies"]["model"]
    assert m["net_eur"] > 0 and m["t_daily_hac"] > 2
    for b, v in out["model_vs"].items():
        assert v["t_hac"] > 2, f"model should beat {b}"


def test_invents_nothing_in_noise(noise):
    root, start, end = noise
    out = backtest.run(start, end)
    t = out["strategies"]["model"]["t_daily_hac"]
    assert t is None or t < 2


def test_no_label_from_after_the_decision(planted):
    root, start, end = planted
    out = backtest.run(start, end)
    assert out["months"]
    for m in out["months"]:
        first = date.fromisoformat(m["first_test_day"])
        assert date.fromisoformat(m["train_last_day"]) <= first - timedelta(days=3)


def test_explain_recovers_negative_wind_effect(planted):
    root, start, end = planted
    res = explain.run(start, end)
    c = res["all"]["coef"]
    assert c["err_wind_on"]["eur_mwh_per_gw"] < 0 and c["err_wind_on"]["t"] < -2
    assert "nan" not in explain.markdown(res)


def test_report_renders(planted):
    root, start, end = planted
    explain.run(start, end)
    backtest.run(start, end)
    (root / "README.md").write_text("x\n<!-- RESULTS:START -->\n<!-- RESULTS:END -->\n")
    body = report.run()
    assert (Path(root) / "reports" / "pnl.png").stat().st_size > 10_000
    assert "Modell" in body and "nan" not in body.lower()
    assert "Modell" in (root / "README.md").read_text()


def test_live_signal_window_and_settlement(planted, monkeypatch):
    root, start, end = planted
    day = end - timedelta(days=5)
    issue = issue_time(day)
    monkeypatch.setenv("DPS_NOW", (issue - pd.Timedelta(minutes=30)).isoformat())
    assert live.signal(day)["status"] == "too early"
    monkeypatch.setenv("DPS_NOW", (issue + pd.Timedelta(minutes=55)).isoformat())
    assert live.signal(day)["status"] == "too late"
    monkeypatch.setenv("DPS_NOW", (issue - pd.Timedelta(minutes=5)).isoformat())
    res = live.signal(day)
    assert res["status"] == "written" and not res["late"]
    assert res["as_of"] == (issue - pd.Timedelta(minutes=5)).isoformat()
    assert live.signal(day)["status"] == "exists"
    sig = pd.read_csv(root / "signals" / f"{day}.csv")
    assert set(sig["side"].unique()) <= {-1, 0, 1}
    # settle after the ID-AEP is out: same numbers as the shared PnL function
    monkeypatch.setenv("DPS_NOW", f"{day + timedelta(days=3)}T12:00:00+00:00")
    (root / "README.md").write_text("x\n<!-- LIVE:START -->\n<!-- LIVE:END -->\n")
    out = live.settle()
    idx = pd.DatetimeIndex(pd.to_datetime(sig["ts_utc"], utc=True))
    expect = trading.pnl(sig["side"], store.read("da").set_index("ts")["da"].reindex(idx),
                         store.read("id_aep").set_index("ts")["id_aep"].reindex(idx))["net"].sum()
    assert out["net_eur"] == pytest.approx(round(expect, 2), abs=0.01)
    assert str(day) in (root / "README.md").read_text()
    meta = json.loads((root / "signals" / f"{day}.json").read_text())
    assert meta["gate_closure"] > meta["generated_at"]


def test_live_uses_the_backtest_procedure(planted, monkeypatch):
    """Same data, same day, decision at 11:00: the live signal must equal the backtest's positions."""
    root, start, end = planted
    backtest.run(start, end)
    res = pd.read_parquet(root / "reports" / "backtest.parquet")
    day = end - timedelta(days=9)
    bt = res[(res["strategy"] == "model") & (res["day"] == str(day))].set_index("ts")["side"]
    assert len(bt) and (bt != 0).any()
    monkeypatch.setattr("dps.config.SIGNALS_DIR", str(root / "signals_proc"))
    monkeypatch.setenv("DPS_NOW", issue_time(day).isoformat())
    out = live.signal(day)
    assert out["status"] == "written"
    sig = pd.read_csv(root / "signals_proc" / f"{day}.csv")
    live_side = pd.Series(sig["side"].to_numpy(dtype=float), index=pd.to_datetime(sig["ts_utc"], utc=True))
    assert (live_side.to_numpy() == bt.reindex(live_side.index).to_numpy()).all()


def test_signal_finished_after_the_window_is_not_counted(planted, monkeypatch):
    root, start, end = planted
    day = end - timedelta(days=6)
    issue = issue_time(day)
    monkeypatch.setattr("dps.config.SIGNALS_DIR", str(root / "signals_late"))
    monkeypatch.setattr("dps.config.LIVE_DIR", str(root / "live_late"))
    clock = iter([issue + pd.Timedelta(minutes=45)] * 2 + [issue + pd.Timedelta(minutes=55)] * 50)
    monkeypatch.setattr("dps.live.now", lambda: next(clock))
    out = live.signal(day)
    assert out["status"] == "written" and out["late"]
    monkeypatch.setattr("dps.live.now", lambda: pd.Timestamp(f"{day + timedelta(days=3)}T12:00:00", tz="UTC"))
    (root / "README.md").write_text("x\n<!-- LIVE:START -->\n<!-- LIVE:END -->\n")
    settled = live.settle()
    assert settled["settled_days"] == 0 and settled["net_eur"] == 0.0
    assert "nicht gezählt" in (root / "live_late" / "SUMMARY.md").read_text()


def test_status_gate(planted, monkeypatch):
    root, start, end = planted
    day = end - timedelta(days=4)
    issue = issue_time(day)
    monkeypatch.setattr("dps.config.SIGNALS_DIR", str(root / "signals_status"))
    for minutes, expect in ((-30, "too early"), (-10, "due"), (49, "due"), (51, "too late")):
        monkeypatch.setenv("DPS_NOW", (issue + pd.Timedelta(minutes=minutes)).isoformat())
        assert live.status(day)["status"] == expect, minutes


def test_robustness_main_row_equals_backtest(planted):
    from dps import robustness
    root, start, end = planted
    bt = backtest.run(start, end)
    rob = robustness.run(start, end, only=["main", "fixed_2", "no_weather"])
    rows = {r["key"]: r for r in rob["variants"]}
    assert rows["main"]["net_eur"] == bt["strategies"]["model"]["net_eur"]
    assert rows["main"]["t_daily_hac"] == bt["strategies"]["model"]["t_daily_hac"]
    assert rows["no_weather"]["net_eur"] < rows["main"]["net_eur"]   # the planted signal lives in the weather
    md = robustness.markdown(rob)
    assert "Hauptmodell" in md and "ohne Wetter" in md and "nan" not in md.lower()
