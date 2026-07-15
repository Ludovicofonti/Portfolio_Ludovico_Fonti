"""Primitive anti-leakage riutilizzabili da feature store e validazione."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


class LeakageError(ValueError):
    """Un dato non era disponibile al forecast origin."""


def assert_sorted_time(frame: pd.DataFrame, time_column: str = "event_time") -> None:
    values = pd.to_datetime(frame[time_column], utc=True)
    if not values.is_monotonic_increasing:
        raise LeakageError(f"{time_column} non è ordinata in modo crescente")
    if values.duplicated().any():
        raise LeakageError(f"{time_column} contiene duplicati")


def assert_available_at_origin(
    frame: pd.DataFrame,
    forecast_origin: str | pd.Timestamp | pd.Series,
    available_column: str = "available_time",
) -> None:
    available = pd.to_datetime(frame[available_column], utc=True)
    origin = pd.to_datetime(forecast_origin, utc=True)
    invalid = available > origin
    if bool(invalid.any()):
        raise LeakageError(f"{int(invalid.sum())} feature disponibili dopo il forecast origin")


def assert_target_absent(feature_columns: Iterable[str], target_columns: Iterable[str]) -> None:
    overlap = sorted(set(feature_columns) & set(target_columns))
    if overlap:
        raise LeakageError(f"Target presenti tra le feature: {', '.join(overlap)}")


def assert_disjoint(train_index: Iterable, test_index: Iterable) -> None:
    overlap = set(train_index) & set(test_index)
    if overlap:
        raise LeakageError(f"Split temporali sovrapposti: {len(overlap)} osservazioni")


def causal_rolling(series: pd.Series, window: int, method: str = "mean", **kwargs) -> pd.Series:
    """Rolling che esclude sempre la riga corrente/target tramite shift(1)."""
    rolling = series.shift(1).rolling(window=window, min_periods=window)
    if not hasattr(rolling, method):
        raise ValueError(f"Metodo rolling non supportato: {method}")
    return getattr(rolling, method)(**kwargs)
