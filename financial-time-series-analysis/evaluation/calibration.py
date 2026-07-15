"""Calibrazione probabilistica."""

import numpy as np


def expected_calibration_error(actual, probability, bins: int = 10) -> float:
    y, p = np.asarray(actual, int), np.asarray(probability, float)
    edges = np.linspace(0, 1, bins + 1)
    error = 0.0
    for lower, upper in zip(edges[:-1], edges[1:]):
        mask = (p >= lower) & (p < upper if upper < 1 else p <= upper)
        if mask.any():
            error += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(error)
