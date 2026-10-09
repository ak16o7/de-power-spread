"""Every variant we tried, on the same walk-forward split, in one table.

Only the first version (first row) was fixed before the first backtest on real data.
After it, the main model changed twice (no load forecast, average of five seeds); every
other variant was run afterwards to see how much the result depends on such choices.
They are all reported, the good and the bad: picking the best row of this table and
calling it the strategy would be fitting the test period. Read the table as the
uncertainty of the headline number, not as a menu.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from . import backtest, baselines, config, metrics, panel, trading
from .explain import ols_hac
from .model import SpreadModel, choose_threshold, decide, guard
from .util import now

LOG = logging.getLogger(__name__)
CAP = 200.0
NO_TRADE = float("inf")

WEATHER_PREFIXES = tuple(f"{m}_" for m in config.WEATHER_MODELS) + ("dis_",)
MW_COLS = ("wind_on_mw", "wind_off_mw", "solar_mw", "ren_mw", "resload_mw")
TECH_ERRORS = ("err_solar", "err_wind_on", "err_wind_off")


@dataclass(frozen=True)
class Variant:
    key: str
    group: str
    label: str
    data: str = "main"                 # main | with_load | archive_only
    drop: tuple = ()                   # feature names or prefixes to leave out
    params: tuple = ()                 # model parameter overrides as (name, value) pairs
    clip_quantiles: tuple | None = None
    target_cap: float | None = None
    rule: str = "validation"           # validation | fixed | pooled | split
    fixed_threshold: float = 2.0
    validation_days: int = config.VALIDATION_DAYS
    sizing: str = "fixed"              # fixed | signal (up to 2x size with |prediction|)
    bag: int = 1
    min_train_days: int = config.MIN_TRAIN_DAYS
    two_stage: bool = False
    seeds: tuple | None = None         # None: config.MODEL_SEEDS


VARIANTS = (
    Variant("first_version", "Hauptmodell", "erste Version, vor dem ersten Backtest festgelegt "
            "(mit Lastprognose, ein einzelnes Modell, Startwert 0)", data="with_load", seeds=(0,)),
    Variant("main", "Hauptmodell", "Hauptmodell: nach dem ersten Backtest ohne Lastprognose und als Mittel "
            "aus fünf Startwerten"),
    Variant("with_load", "Datenstand", "mit Lastprognose", data="with_load"),
    Variant("archive_only", "Datenstand", "Wetter nur so frisch wie im Archiv (vollständige Läufe auf dessen "
            "Vorlaufzeiten 24–29 h und 48–53 h zurückgeschnitten)", data="archive_only"),
    Variant("no_capacity", "Datenstand", "ohne MW-Features (keine installierte Leistung)", drop=MW_COLS),
    Variant("fixed_2", "Entscheidungsregel", "feste Schwelle 2 €/MWh, nichts gewählt", rule="fixed"),
    Variant("val_56", "Entscheidungsregel", "Schwelle auf 56 statt 28 Tagen gewählt", validation_days=56),
    Variant("pooled", "Entscheidungsregel", "Schwelle auf allen bisherigen Out-of-sample-Tagen gewählt", rule="pooled"),
    Variant("split", "Entscheidungsregel", "getrennte Schwellen für long und short, „nie“ erlaubt", rule="split"),
    Variant("signal_size", "Entscheidungsregel", "Größe nach Signalstärke (10–20 MW)", sizing="signal"),
    Variant("median", "Modell", "Median- statt Quadratverlust", params=(("loss", "absolute_error"),)),
    Variant("regularised", "Modell", "stärker reguliert (150 Bäume, ≥ 500 Viertelstunden je Blatt)",
            params=(("max_iter", 150), ("min_samples_leaf", 500))),
    Variant("cap_100", "Modell", "Trainingsziel hart auf ±100 €/MWh gekappt", target_cap=100.0, clip_quantiles=(0.0, 1.0)),
    Variant("bagging", "Modell", "Mittel aus 5 Modellen auf Tages-Bootstraps", bag=5),
    Variant("two_stage", "Modell", "zweistufig: ÜNB-Prognosefehler vorhersagen, dann in € umrechnen", two_stage=True),
    Variant("no_weather", "Feature-Gruppe weggelassen", "ohne Wetter", drop=WEATHER_PREFIXES + MW_COLS),
    Variant("no_spread_history", "Feature-Gruppe weggelassen", "ohne Spread-Historie", drop=("sp_",)),
    Variant("no_da_prev", "Feature-Gruppe weggelassen", "ohne Day-Ahead-Preise des Vortags", drop=("da_prev_",)),
    Variant("start_december", "Startmonat", "Test ab Dezember 2025 (59 statt 60 Trainingstage verlangt)",
            min_train_days=59),
    # The seed only drives the early-stopping holdout inside each gradient-boosting fit.
    # Single fits show the raw estimation noise; other seed sets show what is left of it
    # after averaging.
    *(Variant(f"single_{s}", "Zufallsstartwert", f"ein einzelnes Modell statt des Mittels, Startwert {s}",
              seeds=(s,)) for s in (0, 1, 2, 3, 4)),
    Variant("seeds_5_9", "Zufallsstartwert", "Mittel über die Startwerte 5–9", seeds=(5, 6, 7, 8, 9)),
    Variant("seeds_10_14", "Zufallsstartwert", "Mittel über die Startwerte 10–14", seeds=(10, 11, 12, 13, 14)),
)


LABELS = {v.key: v.label for v in VARIANTS}


def _cols(cols: list[str], v: Variant) -> list[str]:
    return [c for c in cols if not any(c == d or c.startswith(d) for d in v.drop)]


def _fit(lab: pd.DataFrame, cols: list[str], v: Variant) -> list[SpreadModel]:
    params = {**config.MODEL_PARAMS, **dict(v.params)}
    out = []
    days = np.array(sorted(lab["day"].unique()))
    rng = np.random.default_rng(0)
    for b in range(v.bag):
        part, seeds = lab, v.seeds
        if v.bag > 1:   # each bootstrap model is a single fit, so bagging costs what the main model costs
            pick = pd.Series(rng.choice(days, size=len(days), replace=True)).value_counts()
            part = pd.concat([lab[lab["day"] == d] for d, c in pick.items() for _ in range(c)])
            seeds = (b,)
        y = part["spread"] if v.target_cap is None else part["spread"].clip(-v.target_cap, v.target_cap)
        out.append(SpreadModel(params, v.clip_quantiles, seeds).fit(part[cols], y))
    return out


def _predict(models: list[SpreadModel], X: pd.DataFrame) -> np.ndarray:
    return np.mean([m.predict(X) for m in models], axis=0)


def _two_stage(lab: pd.DataFrame, X: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Predict each TSO day-ahead forecast error, then price it with the ex-post slope."""
    lab = lab.dropna(subset=["spread", *TECH_ERRORS])
    Xl, Xp = lab[cols].to_numpy(float), X[cols].to_numpy(float)
    pred_err = {k: np.mean([HistGradientBoostingRegressor(**config.MODEL_PARAMS, random_state=s)
                            .fit(Xl, lab[k].to_numpy(float)).predict(Xp) for s in config.MODEL_SEEDS], axis=0)
                for k in TECH_ERRORS}
    A = np.column_stack([np.ones(len(lab))] + [lab[k].to_numpy(float) / 1000 for k in TECH_ERRORS])
    beta = ols_hac(lab["spread"].clip(-CAP, CAP).to_numpy(float), A, 96)["beta"]
    return beta[0] + sum(beta[i + 1] * pred_err[k] / 1000 for i, k in enumerate(TECH_ERRORS))


def _sides(pred: np.ndarray, state, v: Variant) -> np.ndarray:
    if v.rule == "split":
        th_long, th_short = state
        s = np.where(pred > th_long, 1.0, 0.0)
        return np.where(pred < -th_short, -1.0, s)
    if v.sizing == "signal":
        size = np.clip(1.0 + (np.abs(pred) - state) / max(state, 1.0), 1.0, 2.0)
        return np.where(np.abs(pred) > state, np.sign(pred) * size, 0.0)
    return decide(pred, state)


def _choose(pred, da, ida, v: Variant):
    if v.rule == "split":
        grid = list(config.THRESHOLD_GRID) + [NO_TRADE]
        # ties go to the more cautious pair, like the main rule
        best = max(((round(float(trading.pnl(_sides(pred, (a, b), v), da, ida)["net"].sum()), 6),
                     min(a, 1e6) + min(b, 1e6)), (a, b)) for a in grid for b in grid)
        return best[1]
    if v.sizing == "signal":
        table = [(round(float(trading.pnl(_sides(pred, th, v), da, ida)["net"].sum()), 6), th) for th in config.THRESHOLD_GRID]
        return max(table)[1]
    return choose_threshold(pred, da, ida)[0]


def walk(df: pd.DataFrame, cols: list[str], start: date, end: date, v: Variant) -> pd.DataFrame:
    cols = _cols(cols, v)
    parts, oos = [], []
    for sp in backtest.splits(df, start, end, min_train_days=v.min_train_days):
        lab = sp.train[sp.train["spread"].notna()]
        days = sorted(lab["day"].unique())
        if v.two_stage:
            vd = set(days[-v.validation_days:])
            val = sp.train[sp.train["day"].isin(vd)]
            state = _choose(_two_stage(lab[~lab["day"].isin(vd)], val, cols), val["da"], val["id_aep"], v)
            pred = _two_stage(lab, sp.test, cols)
        else:
            if v.rule == "fixed":
                state = v.fixed_threshold
            else:
                vd = set(days[-v.validation_days:])
                val = sp.train[sp.train["day"].isin(vd)]
                vpred = _predict(_fit(lab[~lab["day"].isin(vd)], cols, v), val[cols])
                P, DA, IDA = vpred, val["da"].to_numpy(), val["id_aep"].to_numpy()
                if v.rule == "pooled" and oos:
                    known = pd.concat(oos)
                    known = known[(known["spread_known_at"] <= sp.cutoff) & ~known["day"].isin(vd)]
                    P = np.concatenate([known["pred"].to_numpy(), P])
                    DA = np.concatenate([known["da"].to_numpy(), DA])
                    IDA = np.concatenate([known["id_aep"].to_numpy(), IDA])
                state = _choose(P, DA, IDA, v)
            pred = _predict(_fit(lab, cols, v), sp.test[cols])
        r = backtest.results_frame(guard(_sides(pred, state, v), sp.test)[0], sp.test, "model", pred)
        r["spread_known_at"] = sp.test["spread_known_at"].to_numpy()
        parts.append(r)
        oos.append(r[["day", "pred", "da", "id_aep", "spread_known_at"]])
    return pd.concat(parts)


def _row(v: Variant, res: pd.DataFrame, df: pd.DataFrame, secs: float) -> dict:
    days = sorted(res["day"].unique())
    s = metrics.summary(res, days)
    c = backtest.capped(res, CAP)
    test = df.loc[res.index]
    vs = {}
    for b in ("slot_sign_28d", "always_long"):
        base = backtest.results_frame(baselines.BASELINES[b](test), test, b)
        vs[b] = metrics.compare(res, base, days)["t_hac"]
    return {"key": v.key, "group": v.group, "label": v.label,
            "from": str(days[0]), "to": str(days[-1]), "days": len(days),
            "net_eur": s["net_eur"], "eur_per_mwh": s["eur_per_mwh"], "mwh": s["mwh"], "t_daily_hac": s["t_daily_hac"],
            "capped_net_eur": round(float(c["net"].sum()), 0),
            "capped_t": metrics._num(metrics.hac_t(metrics.daily(c, days).to_numpy()), 2),
            "t_vs_slot_sign_28d": vs["slot_sign_28d"], "t_vs_always_long": vs["always_long"],
            "long_net_eur": round(float(res.loc[res["side"] > 0, "net"].sum()), 0),
            "short_net_eur": round(float(res.loc[res["side"] < 0, "net"].sum()), 0),
            "seconds": round(secs)}


def run(start: date | None = None, end: date | None = None, only: list[str] | None = None) -> dict:
    start = start or config.START
    end = end or backtest.default_end()
    variants = [v for v in VARIANTS if not only or v.key in only]
    data: dict[str, tuple[pd.DataFrame, list[str]]] = {}
    rows = []
    for v in variants:
        if v.data not in data:
            kw = {"with_load": {"use_load_forecast": True}, "archive_only": {"archive_only": True}}.get(v.data, {})
            df, cols = backtest.dataset(start, end, **({"use_load_forecast": False} | kw))
            if v.data == "main":
                err = panel.build(start, end, with_fundamentals=True)[list(TECH_ERRORS)]
                df = df.join(err)
            data[v.data] = (df, cols)
        df, cols = data[v.data]
        t0 = time.time()
        res = walk(df, cols, start, end, v)
        rows.append(_row(v, res, df, time.time() - t0))
        LOG.info("robustness %-18s net %9.0f  t %5s  capped t %5s", v.key, rows[-1]["net_eur"],
                 rows[-1]["t_daily_hac"], rows[-1]["capped_t"])
    out = {"generated_at": now().isoformat(), "capped_eur_mwh": CAP,
           "note": "all variants that were run, on the same walk-forward split; the main model was fixed beforehand",
           "variants": rows, "provenance": backtest.provenance()}
    p = Path(config.REPORTS_DIR) / "robustness.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    return out


def markdown(rob: dict | None) -> str:
    if not rob or not rob.get("variants"):
        return "_Robustheitstabelle noch nicht gerechnet (`python -m dps robustness`)._\n"
    from .report import _fmt
    cap = rob.get("capped_eur_mwh", CAP)
    L = ["| Variante | Netto € | €/MWh | t | Spread gekappt ±%.0f: Netto € (t) | t gegen Vorzeichen je Viertelstunde | Long € | Short € |" % cap,
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    group = None
    for r in rob["variants"]:
        if r["group"] != group:
            group = r["group"]
            L.append(f"| _{group}_ | | | | | | | |")
        label = LABELS.get(r["key"], r["label"])          # labels live in the code, numbers in the JSON
        name = f"**{label}**" if r["key"] in ("main", "first_version") else label
        period = "" if r["key"] != "start_december" else f" ({r['from']} bis {r['to']})"
        L.append(f"| {name}{period} | {_fmt(r['net_eur'], 0, True)} | {_fmt(r['eur_per_mwh'], 2, True)} | "
                 f"{_fmt(r['t_daily_hac'], 2)} | {_fmt(r['capped_net_eur'], 0, True)} ({_fmt(r['capped_t'], 1)}) | "
                 f"{_fmt(r['t_vs_slot_sign_28d'], 2)} | {_fmt(r['long_net_eur'], 0, True)} | {_fmt(r['short_net_eur'], 0, True)} |")
    nets = [r["net_eur"] for r in rob["variants"] if r["group"] not in ("Feature-Gruppe weggelassen",)
            and r["key"] not in ("signal_size",)]
    L.append(f"\nSpanne über die Varianten (ohne weggelassene Feature-Gruppen und ohne die größere Position): "
             f"{_fmt(min(nets), 0, True)} bis {_fmt(max(nets), 0, True)} €.")
    single = [r for r in rob["variants"] if r["key"].startswith("single_")]
    sets = [r for r in rob["variants"] if r["key"] == "main" or r["key"].startswith("seeds_")]
    if len(single) > 1:
        n = [r["net_eur"] for r in single]
        t = [r["t_daily_hac"] for r in single if r["t_daily_hac"] is not None]
        L.append(f"Ein einzelnes Modell landet je nach Zufallsstartwert bei {_fmt(min(n), 0, True)} bis "
                 f"{_fmt(max(n), 0, True)} € (t {_fmt(min(t), 2)} bis {_fmt(max(t), 2)}). So groß ist das "
                 "Schätzrauschen, bevor irgendeine Designentscheidung ins Spiel kommt; deshalb mittelt das "
                 "Hauptmodell fünf Startwerte.")
        if len(sets) > 1:
            names = {"main": "0–4 (Hauptmodell)", "seeds_5_9": "5–9", "seeds_10_14": "10–14"}
            L.append("Mittel über fünf Startwerte: " + ", ".join(
                f"{names.get(r['key'], r['key'])}: {_fmt(r['net_eur'], 0, True)} € (t {_fmt(r['t_daily_hac'], 2)})"
                for r in sets) + ".")
    return "\n".join(L) + "\n"
