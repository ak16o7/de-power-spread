"""Part 1, ex post: what does a forecast error cost in EUR/MWh?

Regression per quarter hour:
    spread = a + b_solar * e_solar + b_won * e_wind_on + b_woff * e_wind_off + b_load * e_load + u
with e_x = actual - TSO day-ahead forecast in GW (solar/wind: ENTSO-E A75 - A69/A01,
load: A65/A16 - A65/A01). Expected signs: more renewables than forecast pushes the
intraday price down (b < 0), more demand than forecast pushes it up (b_load > 0).

The TSO day-ahead forecast is published at 18:00 on D-1, after the auction. That is
fine here: this part explains spreads, it never feeds a trading decision.
Standard errors: Newey-West with one day of lags (quarter hours are autocorrelated):
96 for the whole day, the daypart's quarter hours per day for a daypart.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, panel
from .util import BERLIN, now

LOG = logging.getLogger(__name__)
REGRESSORS = ("err_solar", "err_wind_on", "err_wind_off", "err_load")
CAP = 200.0   # robustness: the same regression with the spread capped at +-CAP EUR/MWh
DAYPARTS = {"00-06": (0, 6), "06-10": (6, 10), "10-16": (10, 16), "16-20": (16, 20), "20-24": (20, 24)}


def ols_hac(y: np.ndarray, X: np.ndarray, lags: int) -> dict:
    """OLS with Newey-West (Bartlett) standard errors. X includes the constant."""
    n, k = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    u = y - X @ beta
    xu = X * u[:, None]
    s = xu.T @ xu
    for lag in range(1, min(lags, n - 1) + 1):
        w = 1.0 - lag / (lags + 1.0)
        g = xu[lag:].T @ xu[:-lag]
        s += w * (g + g.T)
    cov = xtx_inv @ s @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float((u ** 2).sum()) / ss_tot if ss_tot > 0 else float("nan")
    return {"beta": beta, "se": se, "t": np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0),
            "r2": r2, "n": n}


MIN_STD_MW = 250.0  # a regressor that barely moves (solar at dusk/night) gives a meaningless slope


def fit(df: pd.DataFrame, lags: int = 96) -> dict | None:
    cols = [c for c in REGRESSORS if c in df and df[c].notna().any()]
    d = df.dropna(subset=["spread", *cols])
    cols = [c for c in cols if d[c].std() >= MIN_STD_MW]
    d = df.dropna(subset=["spread", *cols])
    if len(d) < 200 or not cols:
        return None
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(dtype="float64") / 1000.0 for c in cols])  # GW
    res = ols_hac(d["spread"].to_numpy(dtype="float64"), X, lags)
    names = ["const", *cols]
    return {"n": int(res["n"]), "r2": round(res["r2"], 3),
            "coef": {nm: {"eur_mwh_per_gw": round(float(b), 3), "se": round(float(s), 3), "t": round(float(t), 2)}
                     for nm, b, s, t in zip(names, res["beta"], res["se"], res["t"])}}


def run(start: date | None = None, end: date | None = None) -> dict:
    start = start or config.START
    end = end or now().tz_convert(BERLIN).date()
    df = panel.build(start, end, with_fundamentals=True)
    hours = pd.DatetimeIndex(df.index).tz_convert(BERLIN).hour
    out = {"generated_at": now().isoformat(), "period": {"from": str(start), "to": str(end)},
           "units": "EUR/MWh of spread (ID-AEP - day-ahead) per GW of forecast error (actual - TSO day-ahead)",
           "all": fit(df), "dayparts": {},
           "capped_eur_mwh": CAP, "all_capped": fit(df.assign(spread=df["spread"].clip(-CAP, CAP)))}
    for name, (a, b) in DAYPARTS.items():
        # one day of lags: a daypart has (b - a) * 4 quarter hours per day
        out["dayparts"][name] = fit(df[(hours >= a) & (hours < b)], lags=(b - a) * 4)
    p = Path(config.REPORTS_DIR) / "explain.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    LOG.info("explain: %s", json.dumps(out["all"]))
    return out


def markdown(res: dict) -> str:
    if not res or not res.get("all"):
        return "_Noch keine Daten für die Erklär-Regression._\n"
    label = {"const": "Konstante", "err_solar": "Solar", "err_wind_on": "Wind an Land",
             "err_wind_off": "Wind auf See", "err_load": "Last"}
    capped = (res.get("all_capped") or {}).get("coef", {})
    cap = res.get("capped_eur_mwh")
    cap_head = f" gekappt ±{cap:.0f} | t |" if capped else ""
    lines = ["| Fehler (Ist − ÜNB-DA), je GW | €/MWh Spread | t |" + cap_head + " " + " | ".join(res["dayparts"]) + " |",
             "|---|---:|---:|" + ("---:|---:|" if capped else "") + "---:|" * len(res["dayparts"])]
    def num(x, fmt):   # German decimal comma
        return "–" if x is None or x != x else format(x, fmt).replace(".", ",")
    for k, v in res["all"]["coef"].items():
        cells = []
        for part in res["dayparts"].values():
            c = (part or {}).get("coef", {}).get(k)
            cells.append(num(c["eur_mwh_per_gw"], "+.2f") if c else "–")
        cc = capped.get(k)
        cap_cells = (f"{num(cc['eur_mwh_per_gw'], '+.2f')} | {num(cc['t'], '.1f')} | " if cc else "– | – | ") if capped else ""
        lines.append(f"| {label.get(k, k)} | {num(v['eur_mwh_per_gw'], '+.2f')} | {num(v['t'], '.1f')} | "
                     + cap_cells + " | ".join(cells) + " |")
    n = f"{res['all']['n']:,}".replace(",", "\u202f")
    r2c = f", gekappt {num(res['all_capped']['r2'], '.2f')}" if capped else ""
    lines.append(f"\nn = {n} Viertelstunden, R² = {num(res['all']['r2'], '.2f')}{r2c}. "
                 "t mit Newey-West-Standardfehlern (Lags: ein Tag). „Gekappt“: Spread auf ±"
                 f"{cap or 0:.0f} €/MWh begrenzt, damit wenige Preisspitzen die Schätzung nicht dominieren. "
                 "Spalten rechts: getrennte Regressionen je Tageszeit (ungekappt); „–“: Fehler schwankt dort "
                 f"zu wenig (Standardabweichung unter {MIN_STD_MW:.0f} MW) für eine sinnvolle Steigung.")
    return "\n".join(lines) + "\n"
