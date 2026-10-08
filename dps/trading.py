"""PnL of a day-ahead position closed at the ID-AEP. Used by backtest and live alike.

side = +1: buy day-ahead, sell at ID-AEP -> earns ID-AEP - DA (the spread)
side = -1: sell day-ahead, buy back at ID-AEP -> earns DA - ID-AEP
The position is flat before delivery: no imbalance, no balancing-energy exposure.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

QH_HOURS = 0.25


def pnl(side, da, id_aep, size_mw: float = config.SIZE_MW, fee: float = config.FEE_EUR_MWH_PER_LEG,
        slippage: float = config.SLIPPAGE_EUR_MWH, penalty: float = config.MISSING_EXIT_PENALTY_EUR_MWH) -> pd.DataFrame:
    """Per quarter hour: mwh, gross, fees, slippage, net (EUR) and whether the exit price was missing.

    Missing ID-AEP (< 500 MW traded in the quarter hour): the position was opened anyway,
    so it is charged `penalty` EUR/MWh instead of a market result. Never silently dropped.
    """
    side = np.asarray(side, dtype="float64")
    da = np.asarray(da, dtype="float64")
    ida = np.asarray(id_aep, dtype="float64")
    traded = (side != 0) & ~np.isnan(da)
    missing = traded & np.isnan(ida)
    mwh = np.where(traded, np.abs(side) * size_mw * QH_HOURS, 0.0)
    gross = np.where(traded & ~missing, side * (ida - da), 0.0) * size_mw * QH_HOURS
    gross = np.where(missing, -penalty * mwh, gross)
    fees = 2 * fee * mwh
    slip = np.where(missing, 0.0, slippage * mwh)
    return pd.DataFrame({"mwh": mwh, "gross": gross, "fees": fees, "slippage": slip,
                         "net": gross - fees - slip, "missing_exit": missing})
