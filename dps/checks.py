"""Checks of the data itself, the part a unit test cannot cover.

The lookahead test proves that the code respects every `available_at`. Whether those
stamps are true is a property of the data. Where the dataset has both kinds of forecasts
(previous runs and complete recorded runs), it can be tested:

1. Which run does a previous-runs value come from? Each day-N value is compared with
   every complete run for the same point and valid time, on all variables. A value that
   is identical to exactly one run identifies that run. If those runs were all made at
   least N * 24 h before the valid time, the archive is no fresher than it claims.
2. How fast are runs really published? For runs recorded live, available_at is the
   measured time; it must stay below the conservative bound the archive rows use.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, hf
from .util import now

LOG = logging.getLogger(__name__)
SKIP = {"point", "valid", "available_at", "fetched_at", "lead_days", "run", "source", "lead"}


def weather_vintage(model: str, start: date, end: date) -> dict:
    a, b = start - timedelta(days=3), end + timedelta(days=3)
    prev = hf._read(hf._month_patterns(f"weather/previous_runs/{model}", a, b, yearly_dir=True))
    runs = hf._read(hf._month_patterns(f"weather/runs/{model}", a - timedelta(days=3), b, yearly_dir=False))
    if prev.empty or runs.empty:
        return {"model": model, "note": "no overlap of previous runs and complete runs"}
    prev["valid"] = pd.to_datetime(prev["valid"], utc=True)
    for c in ("valid", "run", "available_at"):
        runs[c] = pd.to_datetime(runs[c], utc=True)
    runs["lead"] = ((runs["valid"] - runs["run"]) / pd.Timedelta(hours=1)).round().astype(int)
    num = [c for c in prev.columns if c in runs.columns and c not in SKIP and pd.api.types.is_numeric_dtype(prev[c])]
    # the overlap: valid times that both kinds cover, with every lead of the runs present
    lo = max(runs["run"].min() + pd.Timedelta(days=3), prev["valid"].min())
    hi = min(prev["valid"].max(), runs["valid"].max())
    prev = prev[(prev["valid"] >= lo) & (prev["valid"] <= hi)]
    prev = prev.assign(point=prev["point"].astype(str))
    runs = runs.assign(point=runs["point"].astype(str))
    out = {"model": model, "overlap": [str(lo), str(hi)], "variables": len(num), "lead_days": {}}
    for ld in sorted(int(x) for x in prev["lead_days"].unique()):
        p = prev[prev["lead_days"] == ld][["point", "valid", *num]]
        mg = p.merge(runs[["point", "valid", "lead", *num]], on=["point", "valid"], suffixes=("_p", "_r"))
        same = np.ones(len(mg), bool)
        compared = np.zeros(len(mg))
        for c in num:   # compare where both have a value; some variables exist in only one kind
            x, y = mg[f"{c}_p"].to_numpy(dtype="float64"), mg[f"{c}_r"].to_numpy(dtype="float64")
            both = ~np.isnan(x) & ~np.isnan(y)
            same &= ~both | (np.abs(x - y) < 1e-6)
            compared += both
        same &= compared >= 5
        hits = mg[same].groupby(["point", "valid"])["lead"].agg(["min", "size"])
        unique = hits[hits["size"] == 1]["min"]
        pairs = int(p.groupby(["point", "valid"]).ngroups)
        out["lead_days"][str(ld)] = {
            "pairs": pairs, "identified": int(len(unique)), "ambiguous": int((hits["size"] > 1).sum()),
            "lead_h": ({q: int(unique.quantile(v)) for q, v in (("min", 0), ("median", 0.5), ("max", 1))}
                       if len(unique) else None),
            "fresher_than_claimed": int((unique < 24 * ld).sum()),
        }
    if "source" in runs:
        live = runs[runs["source"].astype(str) == "live"]
        if len(live):
            first = live.groupby("run")["available_at"].min()
            d = (first - pd.Series(first.index, index=first.index)) / pd.Timedelta(hours=1)
            out["live_publication_delay_h"] = {"runs": int(len(d)), "min": round(float(d.min()), 2),
                                               "max": round(float(d.max()), 2),
                                               "assumed_for_archive": config.ARCHIVE_DELAY_H.get(model)}
    return out


def run(start: date | None = None, end: date | None = None) -> dict:
    start = start or config.START
    end = end or now().date()
    res = {"generated_at": now().isoformat(), "weather": [weather_vintage(m, start, end) for m in config.WEATHER_MODELS],
           "hf_revisions": hf.revisions_used()}
    p = Path(config.REPORTS_DIR) / "checks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1, default=str))
    LOG.info("checks: %s", json.dumps(res["weather"]))
    return res


def markdown(res: dict | None) -> str:
    if not res:
        return "_Datenprüfung noch nicht gerechnet (`python -m dps checks`)._\n"
    from .report import _fmt
    L = ["| Wettermodell | Gültigkeitszeiten | Archivwert | Werte geprüft | genau einem Lauf zuzuordnen | "
         "Vorlauf dieses Laufs (min / Median / max) | frischer als behauptet |",
         "|---|---|---|---:|---:|---:|---:|"]
    delays = []
    for w in res.get("weather", []):
        ov = w.get("overlap") or ["", ""]
        span = f"{str(ov[0])[:10]} bis {str(ov[1])[:10]}"
        for ld, v in (w.get("lead_days") or {}).items():
            lh = v.get("lead_h") or {}
            L.append(f"| {w['model']} | {span} | Tag {ld} (behauptet ≥ {24 * int(ld)} h) | {_fmt(v['pairs'])} | "
                     f"{_fmt(v['identified'])} | {lh.get('min', '–')} / {lh.get('median', '–')} / {lh.get('max', '–')} h | "
                     f"{v['fresher_than_claimed']} |")
        d = w.get("live_publication_delay_h")
        if d:
            delays.append(f"{w['model']} {_fmt(d['min'], 1)} bis {_fmt(d['max'], 1)} h nach Laufstart ({d['runs']} Läufe; "
                          f"das Archiv setzt {_fmt(d['assumed_for_archive'], 1)} h an)")
    L.append("\nEin Archivwert gilt als zugeordnet, wenn er in allen Variablen, die beide Datenarten haben, exakt "
             "einem einzigen vollständigen Lauf gleicht. „Frischer als behauptet“ zählt Werte aus einem Lauf mit "
             "kürzerem Vorlauf als angegeben. Verglichen wird fast nur mit nachgeladenen Läufen, denn das Archiv "
             "endet, kurz nachdem der Live-Mitschnitt beginnt. Die live mitgeschnittenen Läufe liefern dafür die "
             "gemessene Veröffentlichungszeit.")
    if delays:
        L.append("Gemessen: " + "; ".join(delays) + ".")
    return "\n".join(L) + "\n"
