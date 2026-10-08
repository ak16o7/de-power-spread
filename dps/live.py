"""Live track record: a signal for tomorrow before the auction, settled once the ID-AEP is out.

signal: runs between 10:45 and 11:50 local (GitHub Actions, several cron slots; the first
        one that lands writes the file). Uses only data available at min(now, 11:00 D-1),
        the same rule as the backtest. The commit time on GitHub is the proof that the
        signal existed before the 12:00 auction.
settle: books every signal whose ID-AEP is known, with the same PnL function as the
        backtest, into live/ledger.csv and the README.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, metrics, report, store, trading
from .backtest import dataset
from .model import decide, train_and_select
from .util import BERLIN, gate_closure, issue_time, now, qh_index, spread_known_at

LOG = logging.getLogger(__name__)
WINDOW_OPENS_MIN_BEFORE_ISSUE = 15     # 10:45 local
WINDOW_CLOSES_MIN_BEFORE_GATE = 10     # 11:50 local


def _paths(day: date) -> tuple[Path, Path]:
    base = Path(config.SIGNALS_DIR) / f"{day:%Y-%m-%d}"
    return base.with_suffix(".csv"), base.with_suffix(".json")


def signal(day: date | None = None, force: bool = False) -> dict:
    t = now()
    day = day or (t.tz_convert(BERLIN).date() + timedelta(days=1))
    csv_path, meta_path = _paths(day)
    if meta_path.exists() and not force:
        return {"status": "exists", "day": str(day)}
    opens = issue_time(day) - pd.Timedelta(minutes=WINDOW_OPENS_MIN_BEFORE_ISSUE)
    closes = gate_closure(day) - pd.Timedelta(minutes=WINDOW_CLOSES_MIN_BEFORE_GATE)
    late = t > closes
    if not force and t < opens:
        return {"status": "too early", "day": str(day), "opens": opens.isoformat()}
    if not force and late:
        return {"status": "too late", "day": str(day), "closed": closes.isoformat()}
    as_of = min(t, issue_time(day))
    hist, cols = dataset(config.START, day)
    train = hist[hist["spread_known_at"] <= as_of]
    labelled_days = train.dropna(subset=["spread"])["day"].nunique()
    if labelled_days < config.MIN_TRAIN_DAYS:
        return {"status": f"not enough history ({labelled_days} labelled days)", "day": str(day)}
    model, threshold, _ = train_and_select(train, cols)
    target, _ = dataset(day, day + timedelta(days=1), as_of=as_of)
    pred = model.predict(target[cols])
    side = decide(pred, threshold)
    out = pd.DataFrame({
        "ts_utc": target.index.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local": target.index.tz_convert(BERLIN).strftime("%Y-%m-%d %H:%M"),
        "side": side.astype(int),
        "size_mw": np.where(side != 0, config.SIZE_MW, 0.0),
        "pred_spread_eur_mwh": np.round(pred, 2),
    })
    meta = {
        "delivery_day": str(day), "generated_at": t.isoformat(), "as_of": as_of.isoformat(),
        "gate_closure": gate_closure(day).isoformat(), "late": bool(late),
        "threshold_eur_mwh": threshold, "train_days": int(labelled_days), "features": len(cols),
        "quarter_hours": int(len(out)), "long": int((side > 0).sum()), "short": int((side < 0).sum()),
        "size_mw": config.SIZE_MW,
    }
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(csv_path, index=False)
    meta_path.write_text(json.dumps(meta, indent=1))
    LOG.info("signal %s: %d long, %d short, threshold %.1f EUR/MWh%s", day, meta["long"], meta["short"],
             threshold, " (LATE, not counted)" if late else "")
    return {"status": "written", **meta}


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
        rows.append({"day": str(day), "late": meta.get("late", False), "generated_at": meta["generated_at"],
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
    if counted.empty:
        return ("_Noch kein abgerechneter Tag. Signale liegen in `signals/`, abgerechnet wird, "
                "sobald der ID-AEP veröffentlicht ist._" + (f"\n\nOffen: {', '.join(pending)}" if pending else "") + "\n")
    d = counted.set_index("day")["net_eur"]
    cum = d.cumsum()
    mwh = float(counted["mwh"].sum())
    per = f" ({f(d.sum() / mwh, 2, True)} €/MWh)" if mwh else ""
    lines = [f"{len(counted)} Tage abgerechnet ({counted['day'].min()} bis {counted['day'].max()}): "
             f"netto {f(d.sum(), 0, True)} € auf {f(mwh)} MWh{per}. Tage im Plus: {int((d > 0).sum())} von {len(d)}. "
             f"t (HAC): {f(metrics.hac_t(d.to_numpy()), 2)}. Max. Drawdown: {f(float((cum - cum.cummax()).min()))} €.", "",
             "| Liefertag | Signal erstellt (UTC) | Viertelstunden | MWh | Netto € | kumuliert € |",
             "|---|---|---:|---:|---:|---:|"]
    for _, r in counted.tail(14).iterrows():
        lines.append(f"| {r['day']} | {str(r['generated_at'])[:16].replace('T', ' ')} | {r['qh_traded']} | "
                     f"{f(r['mwh'], 1)} | {f(r['net_eur'], 0, True)} | {f(cum[r['day']], 0, True)} |")
    late = ledger[ledger["late"].astype(bool)]
    if len(late):
        lines.append(f"\nNach 11:50 erzeugt und deshalb nicht gezählt: {', '.join(late['day'])}")
    if pending:
        lines.append(f"\nWarten auf ID-AEP: {', '.join(pending)}")
    return "\n".join(lines) + "\n"
