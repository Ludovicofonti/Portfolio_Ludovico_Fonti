"""Feature derivate descrittive, senza trasformarle automaticamente in segnali."""

import numpy as np
import pandas as pd


def derivatives_features(frame: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    out = frame.copy()
    if "funding_rate" in out:
        history = out["funding_rate"].shift(1).rolling(window)
        out["funding_mean"] = history.mean()
        out["funding_zscore"] = (out["funding_rate"] - history.mean()) / history.std()
        out["cumulative_funding"] = out["funding_rate"].cumsum()
        out["funding_extreme_flag"] = out["funding_zscore"].abs().ge(2)
    if "open_interest" in out:
        oi = out["open_interest"].replace(0, np.nan)
        out["open_interest_change"] = oi.pct_change()
        out["open_interest_log_change"] = np.log(oi).diff()
        hist = oi.shift(1).rolling(window)
        out["open_interest_zscore"] = (oi - hist.mean()) / hist.std()
        out["open_interest_momentum"] = oi.pct_change(window)
        if "log_return" in out:
            out["return_open_interest_interaction"] = out["log_return"] * out["open_interest_change"]
    if {"spot_price", "perpetual_price"}.issubset(out.columns):
        out["basis_absolute"] = out["perpetual_price"] - out["spot_price"]
        out["basis_percent"] = out["basis_absolute"] / out["spot_price"]
        hist = out["basis_percent"].shift(1).rolling(window)
        out["basis_zscore"] = (out["basis_percent"] - hist.mean()) / hist.std()
    return out
