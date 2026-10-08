"""A synthetic world with the same file layout as the real sources. For tests and the demo
only -- every number it produces is made up.

The world: a market that prices day-ahead with ICON-EU only, while the true weather is
better estimated by averaging ICON-EU and ECMWF. So ECMWF-minus-ICON predicts the
renewable surprise, and the surprise moves the intraday price. That is a planted,
learnable signal (alpha=True). With alpha=False the spread is pure noise and nothing
should make money after costs.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, store
from .features import clear_sky_ghi, cos_zenith, wind_cf
from .util import local

VARS_COMMON = ("shortwave_radiation", "direct_radiation", "diffuse_radiation", "temperature_2m",
               "cloud_cover", "snow_depth")
MODEL_SPEC = {"icon_eu": ("wind_speed_120m", "wind_direction_120m", 4.5),
              "ecmwf_ifs": ("wind_speed_100m", "wind_direction_100m", 8.5)}
CAP_GW = {"Solar AC": 110.0, "Wind onshore": 66.0, "Wind offshore": 10.0}


def _ar1(rng, n, phi, sigma):
    e = rng.normal(0, sigma * np.sqrt(1 - phi ** 2), n)
    x = np.empty(n)
    x[0] = rng.normal(0, sigma)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def make(data_dir: Path, hf_dir: Path, start: date, end: date, alpha: bool = True, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    a = start - timedelta(days=40)
    b = end + timedelta(days=3)
    hours = pd.date_range(local(a), local(b), freq="h", inclusive="left")
    n = len(hours)
    pts = list(config.POINTS)
    # ---- truth: national wind regime + local noise; clouds; sun
    regime = 25 + _ar1(rng, n, 0.97, 12)
    ws_true = {p: np.clip(regime * (1.25 if config.POINTS[p][2] == "offshore" else 1.0)
                          + _ar1(rng, n, 0.8, 4), 0, None) for p in pts}
    cloud_true = np.clip(0.5 + _ar1(rng, n, 0.95, 0.3), 0, 1)
    cs = {p: clear_sky_ghi(cos_zenith(hours - pd.Timedelta(minutes=30), *config.POINTS[p][:2])) for p in pts}
    ghi_true = {p: cs[p] * (1 - 0.75 * cloud_true) for p in pts}
    # ---- weather forecasts per model and lead (errors persistent in time, mostly national)
    err = {}
    for m in MODEL_SPEC:
        for lead, sig in ((1, 6.0), (2, 9.0)):
            err[(m, lead)] = (_ar1(rng, n, 0.9, sig), _ar1(rng, n, 0.9, 0.12 * lead))
    for m, (ws_col, wd_col, delay) in MODEL_SPEC.items():
        rows = []
        for lead in (1, 2):
            e_ws, e_cl = err[(m, lead)]
            cl = np.clip(cloud_true + e_cl, 0, 1)
            for p in pts:
                ghi = cs[p] * (1 - 0.75 * cl)
                rows.append(pd.DataFrame({
                    "point": p, "valid": hours, "lead_days": np.int8(lead),
                    "shortwave_radiation": ghi.astype("float32"), "direct_radiation": (0.6 * ghi).astype("float32"),
                    "diffuse_radiation": (0.4 * ghi).astype("float32"),
                    "temperature_2m": np.float32(10.0), "cloud_cover": (100 * cl).astype("float32"),
                    "snow_depth": np.float32(0.0),
                    ws_col: np.clip(ws_true[p] + e_ws + rng.normal(0, 1.5, n), 0, None).astype("float32"),
                    wd_col: np.float32(250.0), "wind_gusts_10m": np.float32(np.nan), "surface_pressure": np.float32(1013.0),
                }))
        df = pd.concat(rows, ignore_index=True)
        df["available_at"] = df["valid"] - pd.to_timedelta(df["lead_days"].astype(int) * 24, unit="h") \
            + pd.Timedelta(hours=delay)
        df["fetched_at"] = pd.Timestamp("2026-10-01", tz="UTC")
        df["point"] = df["point"].astype("string")
        for (y, mo), g in df.groupby([df["valid"].dt.year, df["valid"].dt.month]):
            p = hf_dir / f"weather/previous_runs/{m}/{y}/{y}-{mo:02d}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            g.to_parquet(p, index=False)
    # ---- capacity
    months = pd.date_range(pd.Timestamp(a.year - 1, 1, 1, tz="UTC"), pd.Timestamp(b.year, 12, 1, tz="UTC"), freq="MS")
    cap = pd.concat([pd.DataFrame({"month": months, "type": t, "gw": g, "seen_at": pd.Timestamp("2026-10-01", tz="UTC")})
                     for t, g in CAP_GW.items()], ignore_index=True)
    (hf_dir / "capacity").mkdir(parents=True, exist_ok=True)
    cap.to_parquet(hf_dir / "capacity/latest.parquet", index=False)
    # ---- quarter-hour world
    qh = pd.date_range(local(a), local(b), freq="15min", inclusive="left")
    def hourly_to_qh(x):
        return np.interp(qh.asi8, (hours + pd.Timedelta(minutes=30)).asi8, x)
    on = [p for p in pts if config.POINTS[p][2] == "onshore"]
    off = [p for p in pts if config.POINTS[p][2] == "offshore"]
    def ren(ws, ghi):
        w_on = CAP_GW["Wind onshore"] * 1000 * np.mean([wind_cf(ws[p]) for p in on], axis=0)
        w_off = CAP_GW["Wind offshore"] * 1000 * np.mean([wind_cf(ws[p]) for p in off], axis=0)
        sol = CAP_GW["Solar AC"] * 1000 * 0.85 * np.mean([ghi[p] for p in on], axis=0) / 1000
        return hourly_to_qh(w_on), hourly_to_qh(w_off), hourly_to_qh(sol)
    act = ren(ws_true, ghi_true)
    # market expectation at the auction: ICON lead-1 if out by 11:00 D-1, else lead-2
    loc_hour = hours.tz_convert("Europe/Berlin")
    hours_into_day = np.asarray(loc_hour.hour + loc_hour.minute / 60, dtype="float64")
    use_l1 = hours_into_day <= 6.0
    e_ws_mkt = np.where(use_l1, err[("icon_eu", 1)][0], err[("icon_eu", 2)][0])
    e_cl_mkt = np.where(use_l1, err[("icon_eu", 1)][1], err[("icon_eu", 2)][1])
    def weather_with(e_ws, e_cl):
        cl = np.clip(cloud_true + e_cl, 0, 1)
        return ({p: np.clip(ws_true[p] + e_ws, 0, None) for p in pts}, {p: cs[p] * (1 - 0.75 * cl) for p in pts})
    mkt = ren(*weather_with(e_ws_mkt, e_cl_mkt))
    # TSO day-ahead forecast (18:00, used only ex post): fresher weather, so it keeps
    # only part of the market's error plus its own
    tso = ren(*weather_with(0.4 * e_ws_mkt + _ar1(rng, n, 0.9, 2.5), 0.4 * e_cl_mkt + _ar1(rng, n, 0.9, 0.05)))
    ren_act, ren_mkt = sum(act), sum(mkt)
    loc = qh.tz_convert("Europe/Berlin")
    hod = np.asarray(loc.hour + loc.minute / 60, dtype="float64")
    load_act = 55000 + 9000 * np.sin((hod - 7) / 24 * 2 * np.pi) + _ar1(rng, len(qh), 0.99, 1500)
    load_da = load_act + _ar1(rng, len(qh), 0.95, 1200)
    da = 70 + 0.0025 * (load_da - ren_mkt) + 8 * np.sin(hod / 24 * 2 * np.pi) + rng.normal(0, 5, len(qh))
    if alpha:
        spread = (-3.0 * (ren_act - ren_mkt) / 1000 + 2.0 * (load_act - load_da) / 1000
                  + 1.5 * np.cos(hod / 24 * 2 * np.pi) + rng.standard_t(4, len(qh)) * 6)
    else:
        spread = rng.standard_t(4, len(qh)) * 10
    id_aep = da + spread
    id_aep[rng.random(len(qh)) < 0.005] = np.nan
    # ---- write the local cache (only delivery days start..end) and the HF entsoe layout
    keep = (qh >= local(start)) & (qh < local(end))
    old = config.DATA_DIR
    config.DATA_DIR = str(data_dir)
    try:
        store.upsert("da", pd.DataFrame({"ts": qh[keep], "da": da[keep]}))
        store.upsert("load", pd.DataFrame({"ts": qh[keep], "load_actual": load_act[keep], "load_da": load_da[keep]}))
        store.upsert("id_aep", pd.DataFrame({"ts": qh[keep], "id_aep": id_aep[keep]}))
    finally:
        config.DATA_DIR = old
    for stream, vals in (("a75", act), ("a69_da", tso)):
        long = pd.concat([pd.DataFrame({"area": "DE", "psr": psr, "ts": qh, "mw": v,
                                        "fetched_at": pd.Timestamp("2026-10-01", tz="UTC")})
                          for psr, v in zip(("wind_on", "wind_off", "solar"), vals)], ignore_index=True)
        for (y, mo), g in long.groupby([long["ts"].dt.year, long["ts"].dt.month]):
            p = hf_dir / f"entsoe/{stream}/DE/{y}/{y}-{mo:02d}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            g.to_parquet(p, index=False)
