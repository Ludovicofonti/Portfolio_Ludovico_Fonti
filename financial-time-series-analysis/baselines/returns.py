"""Baseline per forecast di rendimento/prezzo."""

import pandas as pd


def zero_return(train: pd.Series, horizon: int = 1) -> float:
    return 0.0


def historical_mean(train: pd.Series, horizon: int = 1) -> float:
    return float(pd.Series(train).dropna().mean())


def rolling_mean(train: pd.Series, horizon: int = 1, window: int = 30) -> float:
    return float(pd.Series(train).dropna().iloc[-window:].mean())


def last_observed_return(train: pd.Series, horizon: int = 1) -> float:
    return float(pd.Series(train).dropna().iloc[-1])


def random_walk_price(train_prices: pd.Series, horizon: int = 1) -> float:
    return float(pd.Series(train_prices).dropna().iloc[-1])
