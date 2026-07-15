"""Peaks Over Threshold con Generalized Pareto Distribution."""

from __future__ import annotations

import numpy as np
from scipy import stats


def fit_peaks_over_threshold(returns, confidence: float = 0.99, threshold_quantile: float = 0.90) -> dict:
    losses = -np.asarray(returns, dtype=float)
    losses = losses[np.isfinite(losses)]
    if not 0.5 < threshold_quantile < confidence < 1:
        raise ValueError("Richiesto 0.5 < threshold_quantile < confidence < 1")
    threshold = float(np.quantile(losses, threshold_quantile))
    excesses = losses[losses > threshold] - threshold
    if len(excesses) < 20:
        raise ValueError("Servono almeno 20 exceedance per una stima EVT difendibile")
    shape, _, scale = stats.genpareto.fit(excesses, floc=0)
    tail_fraction = len(excesses) / len(losses)
    tail_probability = (1 - confidence) / tail_fraction
    quantile_excess = float(stats.genpareto.ppf(1 - tail_probability, shape, loc=0, scale=scale))
    var_loss = threshold + quantile_excess
    if shape >= 1:
        es_loss = float("inf")
    else:
        es_loss = (var_loss + scale - shape * threshold) / (1 - shape)
    return {"method": "POT-GPD", "threshold": threshold, "threshold_quantile": threshold_quantile,
            "n_observations": int(len(losses)), "n_exceedances": int(len(excesses)),
            "shape": float(shape), "scale": float(scale), "confidence": confidence,
            "var": float(-var_loss), "expected_shortfall": float(-es_loss),
            "finite_mean": bool(shape < 1), "stable_shape": bool(-0.5 < shape < 0.8)}
