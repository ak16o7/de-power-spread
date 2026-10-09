"""The spread model: gradient-boosted trees on the features, fixed settings, no tuning
on test data, averaged over config.MODEL_SEEDS. The only choice made from data is the
trading threshold, picked on the newest VALIDATION_DAYS of each training window by a
model that did not train on them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from . import config, trading


class SpreadModel:
    def __init__(self, params: dict | None = None, clip_quantiles: tuple[float, float] | None = None,
                 seeds: tuple[int, ...] | None = None) -> None:
        self.params = dict(params or config.MODEL_PARAMS)
        self.clip_quantiles = clip_quantiles or config.TARGET_CLIP_QUANTILES
        self.seeds = tuple(config.MODEL_SEEDS if seeds is None else seeds)
        self.ests: list[HistGradientBoostingRegressor] = []
        self.clip: tuple[float, float] | None = None
        self.columns: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SpreadModel":
        ok = y.notna().to_numpy()
        lo, hi = np.quantile(y[ok], self.clip_quantiles)
        self.clip = (float(lo), float(hi))
        self.columns = list(X.columns)
        Xa = X.loc[ok].to_numpy(dtype="float64")
        ya = y[ok].clip(lo, hi).to_numpy(dtype="float64")
        self.ests = [HistGradientBoostingRegressor(**{**self.params, "random_state": s}).fit(Xa, ya) for s in self.seeds]
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        assert self.ests, "fit first"
        Xa = X[self.columns].to_numpy(dtype="float64")
        return np.mean([e.predict(Xa) for e in self.ests], axis=0)


def data_problem(day: pd.DataFrame) -> str | None:
    """Why a delivery day must not be traded, or None. Same rule in backtest and live: no
    blind trades when an input the model always had in training is missing or stale."""
    if "da_prev_slot" in day and day["da_prev_slot"].isna().all():
        return "no day-ahead prices of D-1"
    if "sp_slot_last" in day and day["sp_slot_last"].isna().all():
        return "no known spread history (ID-AEP of D-3 missing)"
    for m in config.WEATHER_MODELS:
        cols = [c for c in day.columns if c.startswith(f"{m}_") and "_rev_" not in c]
        if cols and day[cols].isna().all().all():
            return f"no {m} forecast available"
        age = day.get(f"diag_wx_age_h_{m}")
        if age is not None and age.notna().any() and float(age.max()) > config.MAX_WEATHER_AGE_H:
            return f"{m} forecast is {float(age.max()):.0f} h old"
    return None


def guard(side: np.ndarray, test: pd.DataFrame) -> tuple[np.ndarray, dict[str, str]]:
    """Zero the positions of every test day with a data problem; returns (sides, {day: reason})."""
    side = np.asarray(side, dtype="float64").copy()
    blocked = {}
    days = test["day"].to_numpy()
    for d, g in test.groupby("day", sort=True):
        why = data_problem(g)
        if why:
            side[days == d] = 0.0
            blocked[str(d)] = why
    return side, blocked


def decide(pred: np.ndarray, threshold: float) -> np.ndarray:
    """Trade the sign of the predicted spread where its size beats the threshold."""
    pred = np.asarray(pred, dtype="float64")
    return np.where(np.abs(pred) > threshold, np.sign(pred), 0.0)


def choose_threshold(pred: np.ndarray, da, id_aep, grid=None) -> tuple[float, list[dict]]:
    """Threshold with the highest net PnL on validation data (ties: the larger threshold)."""
    grid = config.THRESHOLD_GRID if grid is None else grid
    table = []
    for th in grid:
        res = trading.pnl(decide(pred, th), da, id_aep)
        table.append({"threshold": th, "net_eur": float(res["net"].sum()), "mwh": float(res["mwh"].sum())})
    best = max(table, key=lambda r: (round(r["net_eur"], 6), r["threshold"]))
    return float(best["threshold"]), table


def train_and_select(train: pd.DataFrame, cols: list[str]) -> tuple[SpreadModel, float, list[dict]]:
    """Fit on all but the newest VALIDATION_DAYS labelled days, pick the threshold there,
    then refit on everything. `train` must hold only rows whose label was known."""
    labelled = train[train["spread"].notna()]
    days = sorted(labelled["day"].unique())
    val_days = set(days[-config.VALIDATION_DAYS:]) if len(days) > config.VALIDATION_DAYS + 14 else set()
    table: list[dict] = []
    threshold = config.THRESHOLD_GRID[len(config.THRESHOLD_GRID) // 2]
    if val_days:
        fit_part = labelled[~labelled["day"].isin(val_days)]
        val_part = train[train["day"].isin(val_days)]
        m = SpreadModel().fit(fit_part[cols], fit_part["spread"])
        threshold, table = choose_threshold(m.predict(val_part[cols]), val_part["da"], val_part["id_aep"])
    model = SpreadModel().fit(labelled[cols], labelled["spread"])
    return model, threshold, table
