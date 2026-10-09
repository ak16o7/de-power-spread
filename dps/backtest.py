"""Part 2: walk-forward backtest of the strategy and the baselines.

For every test month M:
- training rows: quarter hours whose ID-AEP was known at the decision time of M's
  first day (11:00 on the day before), i.e. no label from D-2 or D-1 leaks in
- threshold: picked on the newest VALIDATION_DAYS of that window by a model that did
  not train on them, then the model is refit on the whole window
- every day of M is traded with the features known at its own decision time
The first test month is the first one with MIN_TRAIN_DAYS labelled days before it.
The live signal (dps.live) fits its model with exactly the same split (fit_for_day).
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd

from . import baselines, config, features, hf, metrics, panel, store, trading
from .model import SpreadModel, decide, guard, train_and_select
from .util import BERLIN, issue_time, month_starts, now

LOG = logging.getLogger(__name__)
HISTORY_DAYS = 35
BEST_DAYS = 10     # robustness: PnL without the best N days


def dataset(start: date, end: date, as_of: pd.Timestamp | None = None, use_load_forecast: bool | None = None,
            archive_only: bool = False) -> tuple[pd.DataFrame, list[str]]:
    """Features for [start, end) plus labels. Returns (frame, feature columns)."""
    p = panel.build(start - timedelta(days=HISTORY_DAYS), end)
    f = features.build(p, start, end, as_of=as_of, use_load_forecast=use_load_forecast, archive_only=archive_only)
    cols = features.feature_columns(f)
    df = f.join(p[["da", "id_aep", "spread", "spread_known_at"]])
    return df, cols


def default_end() -> date:
    """Day after the newest delivery day whose ID-AEP is both stored and known by now."""
    today = now().tz_convert(BERLIN).date()
    end = today - timedelta(days=config.SPREAD_KNOWN_DAYS_AFTER - 1)
    last = store.last_ts("id_aep")
    if last is not None:
        end = min(end, last.tz_convert(BERLIN).date() + timedelta(days=1))
    return end


def _next_month(m: date) -> date:
    return date(m.year + (m.month == 12), m.month % 12 + 1, 1)


@dataclass
class Split:
    month: date
    first: date                # first test day (the month start, or START)
    cutoff: pd.Timestamp       # decision time of `first`: only labels known by then train
    train: pd.DataFrame
    test: pd.DataFrame
    train_days: int
    train_last_day: date


def training_rows(df: pd.DataFrame, day: date) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Rows a model for delivery day `day` may train on: labels known at the decision
    time of the first day of `day`'s month (models are refit monthly)."""
    first = max(date(day.year, day.month, 1), config.START)
    cutoff = issue_time(first)
    return df[df["spread_known_at"] <= cutoff], cutoff


def splits(df: pd.DataFrame, start: date, end: date, min_train_days: int = config.MIN_TRAIN_DAYS) -> Iterator[Split]:
    """The walk-forward split, one test month at a time."""
    for m in month_starts(start, end - timedelta(days=1)):
        first = max(m, start)
        cutoff = issue_time(first)
        train = df[df["spread_known_at"] <= cutoff]
        labelled = train.dropna(subset=["spread"])
        n_days = labelled["day"].nunique()
        if n_days < min_train_days:
            continue
        test = df[(df["day"] >= first) & (df["day"] < min(_next_month(m), end))]
        if test.empty:
            continue
        yield Split(m, first, cutoff, train, test, int(n_days), max(labelled["day"]))


def fit_for_day(df: pd.DataFrame, cols: list[str], day: date) -> tuple[SpreadModel, float, int]:
    """Model and threshold the backtest uses for delivery day `day` (live uses this)."""
    train, _ = training_rows(df, day)
    n_days = train.dropna(subset=["spread"])["day"].nunique()
    if n_days < config.MIN_TRAIN_DAYS:
        raise ValueError(f"not enough history ({n_days} labelled days)")
    model, threshold, _ = train_and_select(train, cols)
    return model, threshold, int(n_days)


def results_frame(side, test: pd.DataFrame, strategy: str, pred=None) -> pd.DataFrame:
    r = trading.pnl(side, test["da"], test["id_aep"])
    r.index = test.index
    r["day"] = test["day"].to_numpy()
    r["strategy"] = strategy
    r["side"] = np.asarray(side, dtype="float64")
    r["pred"] = np.nan if pred is None else pred
    r["da"] = test["da"].to_numpy()
    r["id_aep"] = test["id_aep"].to_numpy()
    return r


def capped(g: pd.DataFrame, cap: float) -> pd.DataFrame:
    """The same positions, PnL with the spread capped at +-cap EUR/MWh."""
    net = trading.pnl(g["side"], g["da"], g["da"] + (g["id_aep"] - g["da"]).clip(-cap, cap))["net"]
    return g.assign(net=net.to_numpy())


def scorecard(by: dict[str, pd.DataFrame], test_days: list) -> dict:
    """Everything the report shows about a set of strategies on the same test days."""
    out: dict = {"strategies": {s: metrics.summary(g, test_days) for s, g in by.items()}}
    out["model_vs"] = {b: metrics.compare(by["model"], by[b], test_days) for b in baselines.BASELINES if b in by}
    out["slippage_sensitivity"] = {}
    for s, g in by.items():
        out["slippage_sensitivity"][s] = {str(slip): round(float(trading.pnl(g["side"], g["da"], g["id_aep"],
                                                                             slippage=slip)["net"].sum()), 0)
                                          for slip in config.SLIPPAGE_GRID}
    out["break_even_slippage_eur_mwh"] = {
        s: (round(config.SLIPPAGE_EUR_MWH + v["net_eur"] / v["mwh"], 2) if v["mwh"] else None)
        for s, v in out["strategies"].items()}
    out["spike_sensitivity"] = {}
    for s, g in by.items():
        d = metrics.daily(g, test_days)
        row = {"top10_qh_net_eur": round(float(g.reindex(g["net"].abs().sort_values(ascending=False).index)["net"]
                                                .head(10).sum()), 0),
               f"without_best_{BEST_DAYS}_days_eur": round(float(d.sort_values(ascending=False).iloc[BEST_DAYS:].sum()), 0)}
        for cap in config.SPIKE_CAPS:
            gc = capped(g, cap)
            row[str(int(cap))] = {"net_eur": round(float(gc["net"].sum()), 0),
                                  "t_daily_hac": metrics._num(metrics.hac_t(metrics.daily(gc, test_days).to_numpy()), 2)}
        out["spike_sensitivity"][s] = row
    mid = config.SPIKE_CAPS[len(config.SPIKE_CAPS) // 2]
    out["model_vs_capped"] = {"cap_eur_mwh": mid, **{b: metrics.compare(capped(by["model"], mid), capped(by[b], mid), test_days)
                                                     for b in baselines.BASELINES if b in by}}
    out["long_short"] = {}
    for s, g in by.items():
        lo, sh = g[g["side"] > 0], g[g["side"] < 0]
        out["long_short"][s] = {"long_net_eur": round(float(lo["net"].sum()), 0), "long_mwh": round(float(lo["mwh"].sum()), 1),
                                "short_net_eur": round(float(sh["net"].sum()), 0), "short_mwh": round(float(sh["mwh"].sum()), 1)}
    beats = {b: bool((v.get("t_hac") or 0) > 2) for b, v in out["model_vs"].items()}
    out["verdict"] = {"criterion": "model beats every baseline on daily net PnL with HAC t > 2",
                      "beats": beats, "passed": bool(beats) and all(beats.values())}
    return out


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=5,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except Exception:
        return None


def _git_commit() -> str | None:
    """HEAD, with '+dirty' if the package code differs from it (then the hash alone does not
    reproduce the numbers)."""
    head = _git("rev-parse", "HEAD")
    if not head:
        return None
    dirty = _git("status", "--porcelain", "--", str(Path(__file__).resolve().parent))
    return head + ("+dirty" if dirty else "")


def provenance() -> dict:
    """What the numbers were computed from: code commit, dataset revision, local cache."""
    data = {}
    for name in store.SOURCES:
        df = store.read(name)
        data[name] = {"rows": int(len(df)),
                      "first_ts": str(df["ts"].min()) if len(df) else None,
                      "last_ts": str(df["ts"].max()) if len(df) else None}
    return {"code_commit": _git_commit(), "hf_dataset": config.HF_DATASET, "hf_revisions": hf.revisions_used(),
            "store": data, "use_load_forecast": config.USE_LOAD_FORECAST}


def run(start: date | None = None, end: date | None = None) -> dict:
    start = start or config.START
    end = end or default_end()
    if end <= start:
        raise RuntimeError(f"nothing to backtest: {start}..{end}")
    df, cols = dataset(start, end)
    LOG.info("dataset: %d quarter hours, %d features, %d with ID-AEP", len(df), len(cols), int(df["id_aep"].notna().sum()))
    parts, months, blocked = [], [], {}
    for sp in splits(df, start, end):
        model, threshold, table = train_and_select(sp.train, cols)
        pred = model.predict(sp.test[cols])
        side, why = guard(decide(pred, threshold), sp.test)
        blocked.update(why)
        parts.append(results_frame(side, sp.test, "model", pred))
        for name, fn in baselines.BASELINES.items():
            parts.append(results_frame(fn(sp.test), sp.test, name))
        months.append({"month": f"{sp.month:%Y-%m}", "first_test_day": str(sp.first), "train_days": sp.train_days,
                       "train_last_day": str(sp.train_last_day), "threshold": threshold, "validation": table,
                       "cutoff": sp.cutoff.isoformat()})
        LOG.info("%s: trained on %d days, threshold %.1f EUR/MWh", f"{sp.month:%Y-%m}", sp.train_days, threshold)
    if not parts:
        raise RuntimeError("no test month has enough training data yet "
                           f"(need {config.MIN_TRAIN_DAYS} labelled days)")
    res = pd.concat(parts).rename_axis("ts").reset_index()
    test_days = sorted(res["day"].unique())
    by = {s: g for s, g in res.groupby("strategy")}
    out = {
        "generated_at": now().isoformat(),
        "test_period": {"from": str(test_days[0]), "to": str(test_days[-1]), "days": len(test_days)},
        "assumptions": {"size_mw": config.SIZE_MW, "fee_eur_mwh_per_leg": config.FEE_EUR_MWH_PER_LEG,
                        "slippage_eur_mwh": config.SLIPPAGE_EUR_MWH,
                        "missing_exit_penalty_eur_mwh": config.MISSING_EXIT_PENALTY_EUR_MWH,
                        "decision": f"{config.ISSUE_HOUR}:00 local on D-1, entry at day-ahead price, "
                                    "exit benchmark ID-AEP"},
        "features": cols,
        "months": months,
        "days_not_traded_for_data": blocked,
        **scorecard(by, test_days),
        "model_monthly": {},
        "provenance": provenance(),
    }
    mg = by["model"]
    for mon, g in mg.groupby(pd.to_datetime(mg["day"].astype(str)).dt.strftime("%Y-%m")):
        out["model_monthly"][mon] = {"net_eur": round(float(g["net"].sum()), 0), "mwh": round(float(g["mwh"].sum()), 1)}
    rep = Path(config.REPORTS_DIR)
    rep.mkdir(parents=True, exist_ok=True)
    res.assign(day=res["day"].astype(str)).to_parquet(rep / "backtest.parquet", index=False)
    (rep / "backtest.json").write_text(json.dumps(out, indent=1, default=str))
    for s, v in out["strategies"].items():
        LOG.info("%-16s net %10.0f EUR  %6s EUR/MWh  t %5s  maxDD %8.0f", s, v["net_eur"], v["eur_per_mwh"],
                 v["t_daily_hac"], v["max_drawdown_eur"])
    return out
