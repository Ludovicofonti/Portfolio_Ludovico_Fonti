"""Baseline direzionali e probabilistiche."""

import numpy as np
import pandas as pd


def always_long(train: pd.Series) -> int:
    return 1


def always_neutral(train: pd.Series) -> int:
    return 0


def last_direction(train: pd.Series, threshold: float = 0.0) -> int:
    value = float(pd.Series(train).dropna().iloc[-1])
    return int(np.sign(value)) if abs(value) > threshold else 0


def moving_average_signal(prices: pd.Series, short: int = 10, long: int = 30) -> int:
    clean = pd.Series(prices).dropna()
    return int(np.sign(clean.iloc[-short:].mean() - clean.iloc[-long:].mean()))


def historical_positive_probability(train: pd.Series, threshold: float = 0.0) -> float:
    clean = pd.Series(train).dropna()
    return float((clean > threshold).mean())
