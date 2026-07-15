"""Regole di calendario e annualizzazione specifiche per asset."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import annualization_factor, get_asset_config


def annualized_volatility(returns: pd.Series, symbol: str, frequency: str | None = None) -> float:
    """Annualizza senza assumere 252 periodi per ogni mercato."""
    return float(pd.Series(returns).dropna().std(ddof=1) * np.sqrt(annualization_factor(symbol, frequency)))


def expected_frequency(symbol: str) -> str:
    return str(get_asset_config(symbol)["primary_frequency"])


def missing_intervals(index: pd.DatetimeIndex, frequency: str, trades_24_7: bool) -> pd.DatetimeIndex:
    """Per mercati 24/7 ogni buco è un'anomalia, non una chiusura."""
    if not trades_24_7 or len(index) < 2:
        return pd.DatetimeIndex([])
    expected = pd.date_range(index.min(), index.max(), freq=frequency, tz=index.tz)
    return expected.difference(index)
