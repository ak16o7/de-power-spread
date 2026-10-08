"""Scorecard per strategy, from per-quarter-hour results. Days count from the first
to the last test day, including days without a trade (PnL 0)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .explain import ols_hac


def hac_t(x: np.ndarray, lags: int = 5) -> float:
    """t-statistic of the mean of x with Newey-West standard errors."""
    x = np.asarray(x, dtype="float64")
    x = x[~np.isnan(x)]
    if len(x) < 10 or np.allclose(x, x[0]):
        return float("nan")
    return float(ols_hac(x, np.ones((len(x), 1)), lags)["t"][0])


def _num(x, nd):
    """Rounded float, or None for NaN/inf (keeps the JSON valid)."""
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if np.isfinite(x) else None


def daily(res: pd.DataFrame, all_days: list) -> pd.Series:
    return res.groupby("day")["net"].sum().reindex(all_days, fill_value=0.0)


def summary(res: pd.DataFrame, all_days: list) -> dict:
    d = daily(res, all_days)
    traded = res[res["mwh"] > 0]
    cum = d.cumsum()
    mwh = float(traded["mwh"].sum())
    std = float(d.std(ddof=1)) if len(d) > 1 else float("nan")
    return {
        "days": int(len(d)),
        "days_traded": int((res.groupby("day")["mwh"].sum() > 0).sum()),
        "quarter_hours_traded": int(len(traded)),
        "mwh": round(mwh, 1),
        "net_eur": round(float(d.sum()), 0),
        "gross_eur": round(float(res["gross"].sum()), 0),
        "costs_eur": round(float((res["fees"] + res["slippage"]).sum()), 0),
        "eur_per_mwh": round(float(d.sum()) / mwh, 2) if mwh else None,
        "hit_rate": round(float((traded["net"] > 0).mean()), 3) if len(traded) else None,
        "sharpe_daily_ann": round(float(d.mean()) / std * np.sqrt(365), 2) if std and std > 0 else None,
        "t_daily_hac": _num(hac_t(d.to_numpy()), 2),
        "max_drawdown_eur": round(float((cum - cum.cummax()).min()), 0) if len(cum) else 0.0,
        "worst_day_eur": round(float(d.min()), 0) if len(d) else 0.0,
        "best_day_eur": round(float(d.max()), 0) if len(d) else 0.0,
        "missing_exit_qh": int(res["missing_exit"].sum()),
    }


def compare(a: pd.DataFrame, b: pd.DataFrame, all_days: list) -> dict:
    """Daily PnL of a minus b: mean and HAC t. > 2 means a beats b beyond noise."""
    diff = daily(a, all_days) - daily(b, all_days)
    return {"mean_eur_per_day": _num(diff.mean(), 1), "t_hac": _num(hac_t(diff.to_numpy()), 2)}
