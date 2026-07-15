"""Baseline VaR storico, normale, Student-t e filtered historical simulation."""

import numpy as np
import pandas as pd
from scipy import stats

from baselines.volatility import ewma_volatility


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    return float(pd.Series(returns).dropna().quantile(1 - confidence))


def normal_var(returns: pd.Series, confidence: float = 0.95) -> float:
    clean = pd.Series(returns).dropna()
    return float(clean.mean() + clean.std(ddof=1) * stats.norm.ppf(1 - confidence))


def student_t_var(returns: pd.Series, confidence: float = 0.95) -> float:
    clean = pd.Series(returns).dropna().to_numpy(dtype=float)
    dof, loc, scale = stats.t.fit(clean)
    return float(stats.t.ppf(1 - confidence, dof, loc=loc, scale=scale))


def filtered_historical_var(returns: pd.Series, confidence: float = 0.95, decay: float = 0.94) -> float:
    clean = pd.Series(returns).dropna()
    sigma_now = ewma_volatility(clean, decay)
    sigma = clean.ewm(alpha=1 - decay, adjust=False).std().replace(0, np.nan)
    standardized = (clean / sigma).dropna()
    return float(standardized.quantile(1 - confidence) * sigma_now)
