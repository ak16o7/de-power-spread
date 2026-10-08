"""Features for every quarter hour of delivery day D, built only from what was known
at the decision time (11:00 local on D-1; live: the earlier of that and now).

Every source is filtered by its own availability time here, and
tests/test_lookahead.py checks that changing or deleting anything published after
the decision time leaves the features unchanged.

Groups
- weather (per model): wind capacity-factor proxy on- and offshore, irradiance, clear-sky
  index, temperature, clouds; their revision over the last 24 h; model disagreement
- fundamentals proxy: wind and solar MW (proxy x installed capacity); with
  config.USE_LOAD_FORECAST (off by default) also the load forecast and residual load
- prices: day-ahead prices of D-1 (known since D-2 13:30)
- spread history: ID-AEP minus day-ahead of days known at decision time (D-3 and older)
- calendar: local quarter of the day, weekday, public holiday, sun elevation
"""
from __future__ import annotations

import logging
import warnings
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config, hf
from .util import BERLIN, days, issue_time, qh_index, slot

LOG = logging.getLogger(__name__)

RADIATION_LIKE = ("ghi", "clear")       # hour means of the preceding hour in Open-Meteo
WX_VARS = ("on_cf", "off_cf", "ghi", "clear", "temp", "cloud")
ONSHORE = [p for p, (_, _, k) in config.POINTS.items() if k == "onshore"]
OFFSHORE = [p for p, (_, _, k) in config.POINTS.items() if k == "offshore"]


# --------------------------------------------------------------------------- physics helpers
def cos_zenith(times: pd.DatetimeIndex, lat, lon) -> np.ndarray:
    """Cosine of the solar zenith angle (NOAA approximation). lat/lon: scalars or arrays."""
    t = pd.DatetimeIndex(times).tz_convert("UTC")
    hour = t.hour + t.minute / 60
    g = 2 * np.pi / 365 * (t.dayofyear - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                       - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    hour, eqtime, decl = np.asarray(hour), np.asarray(eqtime), np.asarray(decl)
    ha = np.radians((hour * 60 + eqtime + 4 * np.asarray(lon)) / 4 - 180)
    la = np.radians(np.asarray(lat))
    return np.asarray(np.sin(la) * np.sin(decl) + np.cos(la) * np.cos(decl) * np.cos(ha))


def clear_sky_ghi(cz: np.ndarray) -> np.ndarray:
    cz = np.clip(np.asarray(cz, dtype="float64"), 0, None)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(cz > 0.01, 1098 * cz * np.exp(-0.057 / np.maximum(cz, 0.01)), 0.0)


def wind_cf(ws_kmh: np.ndarray) -> np.ndarray:
    """Generic turbine power curve: cut-in 3 m/s, rated 12 m/s, cut-out 25 m/s."""
    v = np.asarray(ws_kmh, dtype="float64") / 3.6
    cf = np.clip((v - 3.0) / 9.0, 0.0, 1.0) ** 3
    return np.where(v >= 25.0, 0.0, cf)


# --------------------------------------------------------------------------- weather
def prepare_weather(wx: pd.DataFrame) -> pd.DataFrame:
    """Per-row derived values (capacity-factor proxy, clear-sky index) once for the whole frame."""
    if wx.empty:
        return wx
    wx = wx.sort_values(["valid", "available_at"], kind="stable").reset_index(drop=True)
    ws = next(c for c in wx.columns if c.startswith("wind_speed_"))
    wx["cf"] = wind_cf(wx[ws].to_numpy(dtype="float64"))
    lat = wx["point"].map({p: v[0] for p, v in config.POINTS.items()}).to_numpy(dtype="float64")
    lon = wx["point"].map({p: v[1] for p, v in config.POINTS.items()}).to_numpy(dtype="float64")
    centre = pd.DatetimeIndex(wx["valid"]) - pd.Timedelta(minutes=30)   # hour mean of preceding hour
    cs = clear_sky_ghi(cos_zenith(centre, lat, lon))
    ghi = wx["shortwave_radiation"].to_numpy(dtype="float64")
    wx["clear"] = np.where(cs > 50, ghi / np.maximum(cs, 1.0), np.nan)
    wx["onshore"] = wx["point"].isin(ONSHORE)
    return wx


def weather_as_of(wx: pd.DataFrame, lo: pd.Timestamp, hi: pd.Timestamp, as_of: pd.Timestamp,
                  min_lead_h: float = config.MIN_LEAD_H, valid_us: np.ndarray | None = None) -> pd.DataFrame:
    """Hourly aggregates for valid times in [lo, hi] from the newest forecast per point and
    valid time that (a) was available at `as_of` and (b) was made >= min_lead_h before valid."""
    if wx.empty:
        return pd.DataFrame(columns=list(WX_VARS) + ["available_at"])
    v = valid_us if valid_us is not None else pd.DatetimeIndex(wx["valid"]).as_unit("us").asi8
    lo_us, hi_us = pd.DatetimeIndex([lo, hi]).as_unit("us").asi8
    i0, i1 = np.searchsorted(v, lo_us, "left"), np.searchsorted(v, hi_us, "right")
    w = wx.iloc[i0:i1]
    w = w[(w["available_at"] <= as_of) & (w["lead_h"] >= min_lead_h)]
    if w.empty:
        return pd.DataFrame(columns=list(WX_VARS) + ["available_at"])
    # newest value per point, valid time and variable: a newer run with a gap in one
    # variable must not blank out an older run that has it
    w = w.sort_values("available_at", kind="stable")
    keys = ["point", "valid"]
    sel = {var: w.loc[w[var].notna(), [*keys, "onshore", "available_at", var]].drop_duplicates(keys, keep="last")
           for var in ("cf", "shortwave_radiation", "clear", "temperature_2m", "cloud_cover")}
    on = {v: x[x["onshore"]].groupby("valid")[v].mean() for v, x in sel.items()}
    cf = sel["cf"]
    agg = pd.DataFrame({
        "on_cf": on["cf"],
        "off_cf": cf[~cf["onshore"]].groupby("valid")["cf"].mean(),
        "ghi": on["shortwave_radiation"],
        "clear": on["clear"],
        "temp": on["temperature_2m"],
        "cloud": on["cloud_cover"],
        "available_at": cf.groupby("valid")["available_at"].max(),
    })
    return agg.sort_index()


def to_quarter_hours(hourly: pd.DataFrame, qh: pd.DatetimeIndex) -> pd.DataFrame:
    """Interpolate hourly aggregates to quarter-hour centres; never bridge gaps > 3 h."""
    out = pd.DataFrame(index=qh)
    centres = (qh + pd.Timedelta(minutes=7.5)).as_unit("us").asi8
    if hourly.empty:
        for c in WX_VARS:
            out[c] = np.nan
        return out
    hours = pd.DatetimeIndex(hourly.index).as_unit("us").asi8
    max_gap = 3 * 3600 * 10**6
    for c in WX_VARS:
        shift = 30 * 60 * 10**6 if c in RADIATION_LIKE else 0
        fp = hourly[c].to_numpy(dtype="float64")
        ok = ~np.isnan(fp)
        if ok.sum() < 2:
            out[c] = np.nan
            continue
        xp, yp = hours[ok] - shift, fp[ok]
        vals = np.interp(centres, xp, yp, left=np.nan, right=np.nan)
        right = np.clip(np.searchsorted(xp, centres), 1, len(xp) - 1)
        out[c] = np.where(xp[right] - xp[right - 1] <= max_gap, vals, np.nan)
    return out


def _nanmean(a, axis=None):
    """nanmean without 'Mean of empty slice' warnings (all-NaN gives NaN)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmean(a, axis=axis)


def _nanstd(a):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanstd(a)


# --------------------------------------------------------------------------- history matrices
def day_slot_matrix(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    """Rows = delivery day, columns = local quarter 0..95 (repeated October hour averaged)."""
    m = panel.groupby(["day", "slot"])[col].mean().unstack("slot")
    return m.reindex(columns=range(96))


def _holidays(years: list[int]) -> set[date]:
    """Nationwide public holidays (regional ones such as Corpus Christi are not included)."""
    import holidays   # required dependency: a silent fallback would change the features
    return set(holidays.country_holidays("DE", years=years).keys())


# --------------------------------------------------------------------------- builder
def build(panel: pd.DataFrame, start: date, end: date, as_of: pd.Timestamp | None = None,
          weather: dict[str, pd.DataFrame] | None = None, use_load_forecast: bool | None = None,
          archive_only: bool = False) -> pd.DataFrame:
    """Feature rows for every quarter hour of delivery days [start, end).

    panel: output of panel.build covering at least 30 days before `start`.
    as_of: live use; the decision time is then min(as_of, 11:00 on D-1).
    weather: {model: hf.weather(...)} to reuse; loaded here if None.
    use_load_forecast: default config.USE_LOAD_FORECAST.
    archive_only: weather as the previous-runs archive has it (robustness variant).
    """
    use_load = config.USE_LOAD_FORECAST if use_load_forecast is None else use_load_forecast
    if weather is None:
        weather = {m: hf.weather(m, start - timedelta(days=2), end + timedelta(days=1), archive_only)
                   for m in config.WEATHER_MODELS}
    wx = {m: prepare_weather(w) for m, w in weather.items()}
    vus = {m: (pd.DatetimeIndex(w["valid"]).as_unit("us").asi8 if not w.empty else None) for m, w in wx.items()}
    spread_m = day_slot_matrix(panel, "spread")
    da_m = day_slot_matrix(panel, "da")
    spread_known = {d: t for d, t in zip(panel["day"], panel["spread_known_at"])}
    da_known = {d: t for d, t in zip(panel["day"], panel["da_known_at"])}
    hol = _holidays(sorted({start.year, end.year, start.year - 1}))
    load_da = panel["load_da"] if "load_da" in panel else pd.Series(dtype="float64")
    rows = []
    for d in days(start, end):
        qh = qh_index(d)
        decision = issue_time(d) if as_of is None else min(issue_time(d), as_of)
        f = pd.DataFrame(index=qh)
        f.index.name = "ts"
        # weather
        lo, hi = qh[0] - pd.Timedelta(hours=3), qh[-1] + pd.Timedelta(hours=3)
        means: dict[str, list[np.ndarray]] = {v: [] for v in ("on_cf", "off_cf", "ghi")}
        for m, w in wx.items():
            now_h = weather_as_of(w, lo, hi, decision, valid_us=vus[m])
            prev_h = weather_as_of(w, lo, hi, decision - pd.Timedelta(hours=24), valid_us=vus[m])
            cur = to_quarter_hours(now_h, qh)
            prev = to_quarter_hours(prev_h, qh)
            for v in WX_VARS:
                f[f"{m}_{v}"] = cur[v].to_numpy()
            for v in ("on_cf", "off_cf", "ghi"):
                f[f"{m}_rev_{v}"] = (cur[v] - prev[v]).to_numpy()
                means[v].append(cur[v].to_numpy())
            age = (decision - now_h["available_at"].max()) / pd.Timedelta(hours=1) if not now_h.empty else np.nan
            f[f"diag_wx_age_h_{m}"] = age
        if len(wx) >= 2:
            a, b = list(wx)[:2]
            for v in ("on_cf", "off_cf", "ghi"):
                f[f"dis_{v}"] = f[f"{b}_{v}"] - f[f"{a}_{v}"]
        # fundamentals proxy (MW)
        cap = hf.capacity_mw(qh)
        on_cf = _nanmean(np.vstack(means["on_cf"]), axis=0) if means["on_cf"] else np.nan
        off_cf = _nanmean(np.vstack(means["off_cf"]), axis=0) if means["off_cf"] else np.nan
        ghi = _nanmean(np.vstack(means["ghi"]), axis=0) if means["ghi"] else np.nan
        f["wind_on_mw"] = on_cf * cap["wind_on"].to_numpy()
        f["wind_off_mw"] = off_cf * cap["wind_off"].to_numpy()
        f["solar_mw"] = ghi / 1000.0 * cap["solar"].to_numpy()
        f["ren_mw"] = f[["wind_on_mw", "wind_off_mw", "solar_mw"]].sum(axis=1, min_count=1)
        if use_load:
            f["load_da"] = load_da.reindex(qh).to_numpy(dtype="float64") if len(load_da) else np.nan
            f["resload_mw"] = f["load_da"] - f["ren_mw"]
        # day-ahead prices of D-1
        s = slot(qh)
        prev_day = d - timedelta(days=1)
        if prev_day in da_m.index and da_known.get(prev_day, decision + pd.Timedelta(days=1)) <= decision:
            row = da_m.loc[prev_day].to_numpy(dtype="float64")
            f["da_prev_slot"] = row[s]
            f["da_prev_mean"] = _nanmean(row)
            f["da_prev_std"] = _nanstd(row)
            f["da_prev_shape"] = row[s] - _nanmean(row)
        else:
            for c in ("da_prev_slot", "da_prev_mean", "da_prev_std", "da_prev_shape"):
                f[c] = np.nan
        # spread history: only days whose ID-AEP was known at the decision time
        known = [k for k in spread_m.index if k < d and spread_known.get(k, decision + pd.Timedelta(days=1)) <= decision]
        hist = spread_m.loc[known[-28:]] if known else spread_m.iloc[0:0]
        h14, h7 = hist.iloc[-14:], hist.iloc[-7:]
        f["sp_slot_mean14"] = _nanmean(h14.to_numpy(dtype="float64"), axis=0)[s] if len(h14) else np.nan
        f["sp_slot_mean28"] = _nanmean(hist.to_numpy(dtype="float64"), axis=0)[s] if len(hist) else np.nan
        f["sp_slot_last"] = hist.iloc[-1].to_numpy(dtype="float64")[s] if len(hist) else np.nan
        f["sp_mean7"] = _nanmean(h7.to_numpy(dtype="float64")) if len(h7) else np.nan
        f["sp_absmean7"] = _nanmean(np.abs(h7.to_numpy(dtype="float64"))) if len(h7) else np.nan
        f["diag_spread_last_known_day"] = str(known[-1]) if known else ""
        # calendar
        loc = qh.tz_convert(BERLIN)
        f["slot"] = s
        f["dow"] = loc.dayofweek
        f["holiday"] = int(d in hol or loc[0].dayofweek >= 5)
        f["cos_zenith"] = cos_zenith(qh + pd.Timedelta(minutes=7.5), *config.DE_CENTER)
        f["diag_decision_time"] = decision
        f["day"] = d
        rows.append(f)
    out = pd.concat(rows) if rows else pd.DataFrame()
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if not c.startswith("diag_") and c != "day"]
