"""The spread model: gradient-boosted trees on the features, fixed settings, no tuning
on test data. The only choice made from data is the trading threshold, picked on the
newest VALIDATION_DAYS of each training window by a model that did not train on them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from . import config, trading


class SpreadModel:
    def __init__(self, params: dict | None = None) -> None:
        self.params = dict(params or config.MODEL_PARAMS)
        self.est: HistGradientBoostingRegressor | None = None
        self.clip: tuple[float, float] | None = None
        self.columns: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SpreadModel":
        ok = y.notna().to_numpy()
        lo, hi = np.quantile(y[ok], config.TARGET_CLIP_QUANTILES)
        self.clip = (float(lo), float(hi))
        self.columns = list(X.columns)
        self.est = HistGradientBoostingRegressor(**self.params)
        self.est.fit(X.loc[ok].to_numpy(dtype="float64"), y[ok].clip(lo, hi).to_numpy(dtype="float64"))
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        assert self.est is not None, "fit first"
        return self.est.predict(X[self.columns].to_numpy(dtype="float64"))


def decide(pred: np.ndarray, threshold: float) -> np.ndarray:
    """Trade the sign of the predicted spread where its size beats the threshold."""
    pred = np.asarray(pred, dtype="float64")
    return np.where(np.abs(pred) > threshold, np.sign(pred), 0.0)


def choose_threshold(pred: np.ndarray, da, id_aep, grid=config.THRESHOLD_GRID) -> tuple[float, list[dict]]:
    """Threshold with the highest net PnL on validation data (ties: the larger threshold)."""
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
