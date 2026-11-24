"""Live track record: a signal for tomorrow before the auction, settled once the ID-AEP is out.

signal: runs between 10:45 and 11:50 local (GitHub Actions, started by an external
        scheduler; GitHub's own cron slots are only a fallback; the first run inside the
        window writes the file). Same procedure as the backtest: the model of the
        delivery month (labels known at the decision time of the month's first day,
        threshold from the same validation rule), features from data available at
        min(now, 11:00 D-1). One model per month, as in the backtest: the month's first
        signal fits model and threshold and stores them in live/models/YYYY-MM.pkl.gz
        (+ .json); every later signal of the month loads that object. Until 30 Nov 2026
        each signal refit it on the newest dataset revision, so a data revision alone could
        move it. No signal on a day the data guard blocks (model.data_problem, same rule
        as the backtest). A signal finished after 11:50 is marked late and never
        counted. The push to GitHub and the Actions run log are the public proof that it
        existed before the 12:00 auction.
settle: books every counted signal whose ID-AEP is known, with the same PnL function as
        the backtest, into live/ledger.csv and the README, and lists every delivery day
        since the first signal that has none.
"""
from __future__ import annotations

import gzip
import json
import logging
import pickle
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, hf, metrics, report, store, trading
from .backtest import _git_commit, dataset, fit_for_day
from .model import SpreadModel, data_problem, decide
from .util import BERLIN, gate_closure, issue_time, now, qh_index, spread_known_at

LOG = logging.getLogger(__name__)
WINDOW_OPENS_MIN_BEFORE_ISSUE = 15     # 10:45 local
WINDOW_CLOSES_MIN_BEFORE_GATE = 10     # 11:50 local


def _paths(day: date) -> tuple[Path, Path]:
    base = Path(config.SIGNALS_DIR) / f"{day:%Y-%m-%d}"
    return base.with_suffix(".csv"), base.with_suffix(".json")


def model_paths(day: date) -> tuple[Path, Path]:
    """The frozen model of `day`'s delivery month: pickle and its description."""
    base = Path(config.LIVE_DIR) / "models" / f"{day:%Y-%m}"
    return base.with_suffix(".pkl.gz"), base.with_suffix(".json")


def _sklearn_version() -> str:
    import sklearn
    return sklearn.__version__


def load_month_model(day: date, cols: list[str]) -> tuple[SpreadModel | None, dict, str | None]:
    """(model, description, None) if the month's frozen model can be used for `cols`,
    else (None, {}, reason). The pickle is written only by this repository's own workflow."""
    pkl, js = model_paths(day)
    if not (pkl.is_file() and js.is_file()):
        return None, {}, None
    info = json.loads(js.read_text())
    if info.get("sklearn") != _sklearn_version():
        return None, info, f"scikit-learn {info.get('sklearn')} -> {_sklearn_version()}"
    if info.get("columns") != list(cols):
        return None, info, "feature columns changed"
    with gzip.open(pkl, "rb") as fh:
        model = pickle.load(fh)
    return model, info, None


def fit_month_model(day: date, t: pd.Timestamp, refit_reason: str | None = None) -> tuple[SpreadModel, dict]:
    """Fit the delivery month's model exactly as the backtest does and store it."""
    hist, cols = dataset(config.START, day)
    model, threshold, labelled_days = fit_for_day(hist, cols, day)
    info = {
        "month": f"{day:%Y-%m}", "trained_at": t.isoformat(), "trained_for_day": str(day),
        "train_cutoff": issue_time(max(date(day.year, day.month, 1), config.START)).isoformat(),
        "threshold_eur_mwh": threshold, "train_days": labelled_days, "columns": list(cols),
        "seeds": list(model.seeds), "sklearn": _sklearn_version(), "hf_revisions": hf.revisions_used(),
        "code_commit": _git_commit(), "refit_reason": refit_reason,
    }
    pkl, js = model_paths(day)
    pkl.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(pkl, "wb") as fh:          # ~2.5 MB a month (5 seeds x 300 trees)
        pickle.dump(model, fh, protocol=pickle.HIGHEST_PROTOCOL)
    js.write_text(json.dumps(info, indent=1))
    LOG.info("month model %s fitted: threshold %.1f EUR/MWh, %d labelled days%s", info["month"], threshold,
             labelled_days, f" (refit: {refit_reason})" if refit_reason else "")
    return model, info


def window(day: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    return (issue_time(day) - pd.Timedelta(minutes=WINDOW_OPENS_MIN_BEFORE_ISSUE),
            gate_closure(day) - pd.Timedelta(minutes=WINDOW_CLOSES_MIN_BEFORE_GATE))


def status(day: date | None = None) -> dict:
    """Is a signal due now? exists / too early / too late / due (cheap, no data needed)."""
    t = now()
    day = day or (t.tz_convert(BERLIN).date() + timedelta(days=1))
    opens, closes = window(day)
    if _paths(day)[1].exists():
        s = "exists"
    elif t < opens:
        s = "too early"
    elif t > closes:
        s = "too late"
    else:
        s = "due"
    return {"status": s, "day": str(day), "opens": opens.isoformat(), "closes": closes.isoformat()}


def signal(day: date | None = None, force: bool = False) -> dict:
    t = now()
    day = day or (t.tz_convert(BERLIN).date() + timedelta(days=1))
    csv_path, meta_path = _paths(day)
    st = status(day)
    if st["status"] != "due" and not force:
        return st
    as_of = min(t, issue_time(day))
    target, cols = dataset(day, day + timedelta(days=1), as_of=as_of)
    model, info, refit_reason = load_month_model(day, cols)
    loaded = model is not None
    if not loaded:
        try:
            model, info = fit_month_model(day, t, refit_reason)
        except ValueError as exc:
            return {"status": str(exc), "day": str(day)}
    cols = info["columns"]
    threshold, labelled_days = info["threshold_eur_mwh"], info["train_days"]
    # no blind trades (same rule as the backtest): write nothing, a later slot retries
    why = data_problem(target)
    if why:
        return {"status": f"not traded: {why}", "day": str(day)}
    pred = model.predict(target[cols])
    side = decide(pred, threshold)
    wx_age = {m: float(target[f"diag_wx_age_h_{m}"].iloc[0]) if f"diag_wx_age_h_{m}" in target else None
              for m in config.WEATHER_MODELS}
    out = pd.DataFrame({
        "ts_utc": target.index.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local": target.index.tz_convert(BERLIN).strftime("%Y-%m-%d %H:%M"),
        "side": side.astype(int),
        "size_mw": np.where(side != 0, config.SIZE_MW, 0.0),
        "pred_spread_eur_mwh": np.round(pred, 2),
    })
    meta = {
        "delivery_day": str(day), "started_at": t.isoformat(), "as_of": as_of.isoformat(),
        "gate_closure": gate_closure(day).isoformat(),
        "threshold_eur_mwh": threshold, "train_days": labelled_days, "features": len(cols),
        "quarter_hours": int(len(out)), "long": int((side > 0).sum()), "short": int((side < 0).sum()),
        "size_mw": config.SIZE_MW, "weather_age_h": wx_age,
        "spread_last_known_day": str(target["diag_spread_last_known_day"].iloc[0]),
        "hf_revisions": hf.revisions_used(),
        "model": {"file": f"models/{day:%Y-%m}.pkl.gz", "loaded": loaded, "trained_at": info["trained_at"],
                  "trained_for_day": info["trained_for_day"], "hf_revisions": info["hf_revisions"],
                  "refit_reason": info.get("refit_reason")},
    }
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(csv_path, index=False)
    written = now()                                  # lateness is judged when the file exists
    meta["generated_at"] = written.isoformat()
    meta["late"] = bool(written > window(day)[1])
    meta_path.write_text(json.dumps(meta, indent=1))
    LOG.info("signal %s: %d long, %d short, threshold %.1f EUR/MWh%s", day, meta["long"], meta["short"],
             threshold, " (LATE, not counted)" if meta["late"] else "")
    return {"status": "written", **meta}


def missing_days(signal_days: list[date], t: pd.Timestamp) -> list[str]:
    """Delivery days since the first signal whose window has closed without a signal file
    (no run started in time, or the data guard blocked every run). Listed in the record,
    so a gap can never pass for a quietly dropped day."""
    if not signal_days:
        return []
    today = t.tz_convert(BERLIN).date()
    last = today + timedelta(days=1) if t > window(today + timedelta(days=1))[1] else today
    have, out, d = set(signal_days), [], min(signal_days)
    while d <= last:
        if d not in have:
            out.append(str(d))
        d += timedelta(days=1)
    return out


def _counted(meta: dict) -> bool:
    """A signal counts only if it was finished inside the window, before gate closure."""
    if meta.get("late", False):
        return False
    try:
        return pd.Timestamp(meta["generated_at"]) < pd.Timestamp(meta["gate_closure"])
    except (KeyError, ValueError):
        return False


def settle() -> dict:
    """Recompute the ledger from all signal files whose ID-AEP is known."""
    t = now()
    da = store.read("da").set_index("ts")["da"].astype("float64")
    ida = store.read("id_aep").set_index("ts")["id_aep"].astype("float64")
    rows, pending, signal_days = [], [], []
    for meta_path in sorted(Path(config.SIGNALS_DIR).glob("*.json")):
        meta = json.loads(meta_path.read_text())
        day = date.fromisoformat(meta["delivery_day"])
        signal_days.append(day)
        sig = pd.read_csv(meta_path.with_suffix(".csv"))
        idx = pd.DatetimeIndex(pd.to_datetime(sig["ts_utc"], utc=True))
        prices = da.reindex(idx)
        exits = ida.reindex(idx)
        complete = exits.notna().sum() >= 0.9 * len(qh_index(day))
        if prices.isna().all() or not (complete or t >= spread_known_at(day) + pd.Timedelta(days=1)):
            pending.append(str(day))
            continue
        r = trading.pnl(sig["side"].to_numpy(), prices.to_numpy(), exits.to_numpy())
        rows.append({"day": str(day), "late": not _counted(meta), "generated_at": meta["generated_at"],
                     "qh_traded": int((r["mwh"] > 0).sum()), "mwh": float(r["mwh"].sum()),
                     "gross_eur": round(float(r["gross"].sum()), 2),
                     "costs_eur": round(float((r["fees"] + r["slippage"]).sum()), 2),
                     "net_eur": round(float(r["net"].sum()), 2), "missing_exit_qh": int(r["missing_exit"].sum())})
    ledger = pd.DataFrame(rows, columns=["day", "late", "generated_at", "qh_traded", "mwh", "gross_eur",
                                         "costs_eur", "net_eur", "missing_exit_qh"])
    live = Path(config.LIVE_DIR)
    live.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(live / "ledger.csv", index=False)
    missing = missing_days(signal_days, t)
    body = live_markdown(ledger, pending, missing)
    (live / "SUMMARY.md").write_text("# Live-Track-Record\n\n" + body)
    report.update_section(Path(config.README), "LIVE", body)
    counted = ledger[~ledger["late"].astype(bool)] if not ledger.empty else ledger
    return {"settled_days": int(len(counted)), "pending": pending, "missing": missing,
            "net_eur": round(float(counted["net_eur"].sum()), 2) if len(counted) else 0.0}


def live_markdown(ledger: pd.DataFrame, pending: list[str], missing: list[str] = ()) -> str:
    f = report._fmt
    counted = ledger[~ledger["late"].astype(bool)] if not ledger.empty else ledger
    late = ledger[ledger["late"].astype(bool)] if not ledger.empty else ledger
    late_note = f"\n\nNach 11:50 fertig und deshalb nicht gezählt: {', '.join(late['day'])}" if len(late) else ""
    if missing:
        late_note += ("\n\nKein Signal (kein Lauf rechtzeitig gestartet oder Data Guard, Grund im "
                      f"Actions-Log): {', '.join(missing)}")
    if counted.empty:
        return ("_Noch kein abgerechneter Tag. Signale liegen in `signals/`, abgerechnet wird, "
                "sobald der ID-AEP veröffentlicht ist._" + late_note
                + (f"\n\nWarten auf ID-AEP: {', '.join(pending)}" if pending else "") + "\n")
    d = counted.set_index("day")["net_eur"]
    cum = d.cumsum()
    mwh = float(counted["mwh"].sum())
    per = f" ({f(d.sum() / mwh, 2, True)} €/MWh)" if mwh else ""
    lines = [f"{len(counted)} Tage abgerechnet ({counted['day'].min()} bis {counted['day'].max()}): "
             f"netto {f(d.sum(), 0, True)} € auf {f(mwh)} MWh{per}. Tage im Plus: {int((d > 0).sum())} von {len(d)}. "
             f"t (HAC): {f(metrics.hac_t(d.to_numpy()), 2)}. Max. Drawdown: {f(metrics.max_drawdown(d))} €.", "",
             "| Liefertag | Signal fertig (UTC) | Viertelstunden | MWh | Netto € | kumuliert € |",
             "|---|---|---:|---:|---:|---:|"]
    for _, r in counted.tail(14).iterrows():
        gen = pd.Timestamp(r["generated_at"]).tz_convert("UTC").strftime("%Y-%m-%d %H:%M")
        lines.append(f"| {r['day']} | {gen} | {r['qh_traded']} | "
                     f"{f(r['mwh'], 1)} | {f(r['net_eur'], 0, True)} | {f(cum[r['day']], 0, True)} |")
    if late_note:
        lines.append("\n" + late_note.lstrip("\n"))
    if pending:
        lines.append(f"\nWarten auf ID-AEP: {', '.join(pending)}")
    return "\n".join(lines) + "\n"
