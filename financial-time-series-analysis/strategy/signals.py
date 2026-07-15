"""Traduzione esplicita forecast→posizione con zona neutrale coerente coi costi."""

import numpy as np


def return_to_position(predicted_return, expected_cost: float, confidence=None, min_confidence: float = 0.0):
    values = np.asarray(predicted_return, dtype=float)
    position = np.where(values > expected_cost, 1.0, np.where(values < -expected_cost, -1.0, 0.0))
    if confidence is not None:
        position = np.where(np.asarray(confidence) >= min_confidence, position, 0.0)
    return position
