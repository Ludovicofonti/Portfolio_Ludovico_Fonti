"""Kelly frazionale prudenziale e volatility targeting."""

import numpy as np


def fractional_kelly(edge: float, variance: float, fraction: float = 0.25, maximum: float = 0.25) -> dict:
    full = edge / variance if variance > 0 else 0.0
    return {"full_kelly": full, "half_kelly": full * 0.5, "quarter_kelly": full * 0.25,
            "prudential_kelly": float(np.clip(full * fraction, -maximum, maximum)), "maximum": maximum}


def volatility_target(forecast_volatility: float, target_volatility: float = 0.15, maximum: float = 1.0) -> float:
    return float(np.clip(target_volatility / forecast_volatility, 0, maximum)) if forecast_volatility > 0 else 0.0
