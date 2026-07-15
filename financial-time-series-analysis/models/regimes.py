"""Classificazione descrittiva di regimi, stimata solo da dati passati."""

import numpy as np
import pandas as pd


def classify_regimes(returns: pd.Series, prices: pd.Series, window: int = 30) -> pd.DataFrame:
    momentum = returns.shift(1).rolling(window).sum()
    volatility = returns.shift(1).rolling(window).std()
    median_vol = volatility.shift(1).expanding().median()
    rolling_peak = prices.shift(1).rolling(window * 3).max()
    drawdown = prices.shift(1) / rolling_peak - 1
    frame = pd.DataFrame(index=returns.index)
    frame["trend_regime"] = np.select([momentum > 0, momentum < 0], ["bull", "bear"], default="range_bound")
    frame["volatility_regime"] = np.where(volatility > median_vol, "high_volatility", "low_volatility")
    frame["drawdown"] = drawdown
    frame["liquidity_stress_regime"] = np.where((volatility > median_vol * 1.5) & (drawdown < -0.10), "liquidity_stress", "normal")
    return frame
