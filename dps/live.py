"""Live track record: a signal for tomorrow before the auction, settled once the ID-AEP is out.

signal: runs between 10:45 and 11:50 local (GitHub Actions, several cron slots; the first
        one that lands writes the file). Same procedure as the backtest: the model of the
        delivery month (labels known at the decision time of the month's first day,
        threshold from the same validation rule), features from data available at
        min(now, 11:00 D-1). No signal on a day the data guard blocks (model.data_problem,
        same rule as the backtest). A signal finished after 11:50 is marked late and never
        counted. The push to GitHub and the Actions run log are the public proof that it
        existed before the 12:00 auction.
settle: books every counted signal whose ID-AEP is known, with the same PnL function as
        the backtest, into live/ledger.csv and the README.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, hf, metrics, report, store, trading
from .backtest import dataset, fit_for_day
from .model import data_problem, decide
from .util import BERLIN, gate_closure, issue_time, now, qh_index, spread_known_at

LOG = logging.getLogger(__name__)
WINDOW_OPENS_MIN_BEFORE_ISSUE = 15     # 10:45 local
WINDOW_CLOSES_MIN_BEFORE_GATE = 10     # 11:50 local


def _paths(day: date) -> tuple[Path, Path]:
    base = Path(config.SIGNALS_DIR) / f"{day:%Y-%m-%d}"
    return base.with_suffix(".csv"), base.with_suffix(".json")


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
    hist, cols = dataset(config.START, day)
    try:
        model, threshold, labelled_days = fit_for_day(hist, cols, day)
    except ValueError as exc:
        return {"status": str(exc), "day": str(day)}
    target, _ = dataset(day, day + timedelta(days=1), as_of=as_of)
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
    rows, pending = [], []
    for meta_path in sorted(Path(config.SIGNALS_DIR).glob("*.json")):
        meta = json.loads(meta_path.read_text())
        day = date.fromisoformat(meta["delivery_day"])
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
    body = live_markdown(ledger, pending)
    (live / "SUMMARY.md").write_text("# Live-Track-Record\n\n" + body)
    report.update_section(Path(config.README), "LIVE", body)
    counted = ledger[~ledger["late"].astype(bool)] if not ledger.empty else ledger
    return {"settled_days": int(len(counted)), "pending": pending,
            "net_eur": round(float(counted["net_eur"].sum()), 2) if len(counted) else 0.0}


def live_markdown(ledger: pd.DataFrame, pending: list[str]) -> str:
    f = report._fmt
    counted = ledger[~ledger["late"].astype(bool)] if not ledger.empty else ledger
    late = ledger[ledger["late"].astype(bool)] if not ledger.empty else ledger
    late_note = f"\n\nNach 11:50 fertig und deshalb nicht gezählt: {', '.join(late['day'])}" if len(late) else ""
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
