"""Baseline di volatilità causali."""

import numpy as np
import pandas as pd


def rolling_volatility(train: pd.Series, window: int = 30) -> float:
    return float(pd.Series(train).dropna().iloc[-window:].std(ddof=1))


def ewma_volatility(train: pd.Series, decay: float = 0.94) -> float:
    values = pd.Series(train).dropna().to_numpy(dtype=float)
    variance = float(np.var(values, ddof=1))
    for value in values:
        variance = decay * variance + (1 - decay) * value**2
    return float(np.sqrt(max(variance, 0.0)))


def last_period_volatility(realized_volatility: pd.Series) -> float:
    return float(pd.Series(realized_volatility).dropna().iloc[-1])


def mean_realized_volatility(realized_volatility: pd.Series) -> float:
    return float(pd.Series(realized_volatility).dropna().mean())
