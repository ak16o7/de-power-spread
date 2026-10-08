"""Everything that defines the experiment lives here. Change it here, nowhere else.

Nothing here is secret: API credentials come from the environment only.
"""
from __future__ import annotations

import os
from datetime import date

# --------------------------------------------------------------------------- period
# Day-ahead runs in quarter hours since delivery day 2025-10-01. One regime, so the
# backtest starts there. Earlier data (hourly day-ahead) is a different market.
START = date.fromisoformat(os.environ.get("DPS_START", "2025-10-01"))

# --------------------------------------------------------------------------- decision
ISSUE_HOUR = 11            # local time on D-1; the day-ahead auction closes at 12:00
GATE_CLOSURE_HOUR = 12     # a live signal after this is marked late and never counted

# What is known when, as local times relative to the delivery day d of the value.
# Day-ahead prices of day d: results ~12:45 on d-1. 13:30 leaves margin.
DA_KNOWN_HOURS_AFTER_PREV_MIDNIGHT = 13.5
# ID-AEP of day d: published once a day. We count it as known from 00:00 on d+2,
# i.e. at the 11:00 decision on D-1 the newest known spread is day D-3. Conservative.
SPREAD_KNOWN_DAYS_AFTER = 2
# Day-ahead load forecast (ENTSO-E A65/A01): by regulation published at the latest two
# hours before day-ahead gate closure, i.e. 10:00 on D-1. Switch off to drop it.
USE_LOAD_FORECAST = os.environ.get("DPS_USE_LOAD_FORECAST", "1") != "0"

# --------------------------------------------------------------------------- trading
SIZE_MW = 10.0                      # fixed position per traded quarter hour
FEE_EUR_MWH_PER_LEG = 0.25          # assumption, not an exchange fee schedule
SLIPPAGE_EUR_MWH = 1.0              # charged against you on the ID-AEP exit
MISSING_EXIT_PENALTY_EUR_MWH = 10.0 # ID-AEP undefined (< 500 MW traded): assumed loss
SLIPPAGE_GRID = (0.0, 1.0, 2.0, 5.0)
# Robustness: PnL if the spread were capped at +-cap EUR/MWh. A strategy whose profit
# disappears under the cap lives off a few price spikes, not off a repeatable edge.
SPIKE_CAPS = (500.0, 200.0, 100.0)

# --------------------------------------------------------------------------- model
THRESHOLD_GRID = (0.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0)  # |predicted spread| in EUR/MWh
MIN_TRAIN_DAYS = 60       # first test month needs this many labelled days before it
VALIDATION_DAYS = 28      # newest labelled days of each training window pick the threshold
TARGET_CLIP_QUANTILES = (0.01, 0.99)  # winsorise spikes in the training target only
MODEL_PARAMS = dict(loss="squared_error", learning_rate=0.05, max_iter=300, max_leaf_nodes=31,
                    min_samples_leaf=200, l2_regularization=1.0, random_state=0)

# --------------------------------------------------------------------------- weather
HF_DATASET = os.environ.get("DPS_HF_DATASET", "akderekaan/de-power-forecast-data")
WEATHER_MODELS = ("icon_eu", "ecmwf_ifs")
# Only forecasts made at least this long before their valid time. The archive
# (Open-Meteo previous runs) only has these; live runs are filtered the same way,
# so backtest and live see the same kind of forecast.
MIN_LEAD_H = 24
DE_CENTER = (51.2, 10.4)
POINTS = {  # name: (lat, lon, kind) -- same 16 points as de-power-forecast
    "SH": (54.3, 9.7, "onshore"), "NI_W": (52.9, 7.8, "onshore"), "NI_O": (52.6, 10.2, "onshore"),
    "MV": (53.8, 12.3, "onshore"), "BB": (52.4, 13.7, "onshore"), "ST": (52.0, 11.7, "onshore"),
    "NRW": (51.5, 7.5, "onshore"), "HE": (50.6, 9.0, "onshore"), "TH_SN": (51.0, 12.5, "onshore"),
    "RP_SL": (49.8, 7.3, "onshore"), "BW": (48.6, 9.0, "onshore"), "BY_N": (49.6, 11.2, "onshore"),
    "BY_S": (48.2, 12.0, "onshore"), "NS_BORKUM": (54.0, 6.5, "offshore"),
    "NS_HELGO": (54.5, 7.6, "offshore"), "OS_ARKONA": (54.8, 14.0, "offshore"),
}
CAPACITY_TYPE = {"solar": "Solar AC", "wind_on": "Wind onshore", "wind_off": "Wind offshore"}
CAPACITY_LAG_MONTHS = 2   # recent months are revised later, so use the value two months back

# --------------------------------------------------------------------------- sources
ENTSOE_ENDPOINT = "https://web-api.tp.entsoe.eu/api"
EIC_DE_LU = "10Y1001A1001A82H"   # bidding zone (prices)
EIC_DE = "10Y1001A1001A83F"      # Germany (load)
NTP_TOKEN_URL = "https://identity.netztransparenz.de/users/connect/token"
NTP_BASE_URL = os.environ.get("NTP_BASE_URL", "https://ds.netztransparenz.de/api/v1/data")
USER_AGENT = "de-power-spread/0.1 (+https://github.com/ak16o7/de-power-spread)"

# --------------------------------------------------------------------------- paths
DATA_DIR = os.environ.get("DPS_DATA_DIR", "data")
REPORTS_DIR = os.environ.get("DPS_REPORTS_DIR", "reports")
SIGNALS_DIR = os.environ.get("DPS_SIGNALS_DIR", "signals")
LIVE_DIR = os.environ.get("DPS_LIVE_DIR", "live")
README = os.environ.get("DPS_README", "README.md")
