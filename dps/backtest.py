"""Part 2: walk-forward backtest of the strategy and the baselines.

For every test month M:
- training rows: quarter hours whose ID-AEP was known at the decision time of M's
  first day (11:00 on the day before), i.e. no label from D-2 or D-1 leaks in
- threshold: picked on the newest VALIDATION_DAYS of that window by a model that did
  not train on them, then the model is refit on the whole window
- every day of M is traded with the features known at its own decision time
The first test month is the first one with MIN_TRAIN_DAYS labelled days before it.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import baselines, config, features, metrics, panel, store, trading
from .model import decide, train_and_select
from .util import BERLIN, issue_time, month_starts, now

LOG = logging.getLogger(__name__)
HISTORY_DAYS = 35


def dataset(start: date, end: date, as_of: pd.Timestamp | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Features for [start, end) plus labels. Returns (frame, feature columns)."""
    p = panel.build(start - timedelta(days=HISTORY_DAYS), end)
    f = features.build(p, start, end, as_of=as_of)
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


def run(start: date | None = None, end: date | None = None) -> dict:
    start = start or config.START
    end = end or default_end()
    if end <= start:
        raise RuntimeError(f"nothing to backtest: {start}..{end}")
    df, cols = dataset(start, end)
    LOG.info("dataset: %d quarter hours, %d features, %d with ID-AEP", len(df), len(cols), int(df["id_aep"].notna().sum()))
    parts, months = [], []
    for m in month_starts(start, end - timedelta(days=1)):
        first = max(m, start)
        cutoff = issue_time(first)
        train = df[df["spread_known_at"] <= cutoff]
        n_days = train.dropna(subset=["spread"])["day"].nunique()
        if n_days < config.MIN_TRAIN_DAYS:
            continue
        test = df[(df["day"] >= first) & (df["day"] < min(_next_month(m), end))]
        if test.empty:
            continue
        model, threshold, table = train_and_select(train, cols)
        pred = model.predict(test[cols])
        sides = {"model": decide(pred, threshold)}
        sides.update({name: fn(test) for name, fn in baselines.BASELINES.items()})
        for strategy, side in sides.items():
            r = trading.pnl(side, test["da"], test["id_aep"])
            r.index = test.index
            r["day"] = test["day"].to_numpy()
            r["strategy"] = strategy
            r["side"] = side
            r["pred"] = pred if strategy == "model" else np.nan
            r["da"] = test["da"].to_numpy()
            r["id_aep"] = test["id_aep"].to_numpy()
            parts.append(r)
        months.append({"month": f"{m:%Y-%m}", "first_test_day": str(first), "train_days": int(n_days),
                       "train_last_day": str(max(train.dropna(subset=["spread"])["day"])),
                       "threshold": threshold, "validation": table, "cutoff": cutoff.isoformat()})
        LOG.info("%s: trained on %d days, threshold %.1f EUR/MWh", f"{m:%Y-%m}", n_days, threshold)
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
                        "decision": f"{config.ISSUE_HOUR}:00 local on D-1, entry at day-ahead price, exit at ID-AEP"},
        "features": cols,
        "months": months,
        "strategies": {s: metrics.summary(g, test_days) for s, g in by.items()},
        "model_vs": {b: metrics.compare(by["model"], by[b], test_days) for b in baselines.BASELINES},
        "slippage_sensitivity": {},
        "model_monthly": {},
    }
    for s, g in by.items():
        row = {}
        for slip in config.SLIPPAGE_GRID:
            r = trading.pnl(g["side"], g["da"], g["id_aep"], slippage=slip)
            row[str(slip)] = round(float(r["net"].sum()), 0)
        out["slippage_sensitivity"][s] = row
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
