"""Costruzione separata di target return, direction, volatility e tail risk."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def _future_values(series: pd.Series, horizon: int) -> pd.DataFrame:
    return pd.concat([series.shift(-step) for step in range(1, horizon + 1)], axis=1)


def build_targets(
    frame: pd.DataFrame,
    horizons: Iterable[int] = (1, 4, 24),
    price_column: str = "close",
    neutral_threshold: float | dict[int, float] = 0.0,
    tail_loss_threshold: float = -0.05,
) -> pd.DataFrame:
    """Aggiunge target futuri senza usarli come feature contemporanee."""
    result = frame.copy()
    log_price = np.log(result[price_column].astype(float))
    one_step_returns = log_price.diff()
    for horizon in horizons:
        if horizon <= 0:
            raise ValueError("Gli orizzonti devono essere positivi")
        future_return = log_price.shift(-horizon) - log_price
        threshold = neutral_threshold.get(horizon, 0.0) if isinstance(neutral_threshold, dict) else neutral_threshold
        result[f"target_return_{horizon}"] = future_return
        direction = pd.Series(np.select(
            [future_return > threshold, future_return < -threshold], [1, -1], default=0
        ), index=result.index, dtype="Int8")
        result[f"target_direction_{horizon}"] = direction.where(future_return.notna())
        future_path = _future_values(one_step_returns, horizon)
        result[f"target_volatility_{horizon}"] = np.sqrt(future_path.pow(2).sum(axis=1, min_count=horizon))
        tail = (future_return <= tail_loss_threshold).astype("Int8")
        result[f"target_tail_loss_{horizon}"] = tail.where(future_return.notna())
    return result
