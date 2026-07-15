"""Walk-forward rigoroso con gap, rolling/expanding e fitting dentro ogni fold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

import numpy as np
import pandas as pd

from features.leakage_checks import assert_disjoint


@dataclass(frozen=True)
class WalkForwardConfig:
    mode: str = "expanding"
    initial_train_size: int = 500
    test_size: int = 20
    step_size: int = 20
    gap_size: int = 0
    train_size: int | None = None
    allow_overlapping_forecasts: bool = False

    def __post_init__(self):
        if self.mode not in {"expanding", "rolling"}:
            raise ValueError("mode deve essere expanding o rolling")
        if min(self.initial_train_size, self.test_size, self.step_size) <= 0 or self.gap_size < 0:
            raise ValueError("Dimensioni walk-forward non valide")
        if not self.allow_overlapping_forecasts and self.step_size < self.test_size:
            raise ValueError("step_size < test_size produce forecast sovrapposti")
        if self.mode == "rolling" and not (self.train_size or self.initial_train_size):
            raise ValueError("rolling richiede train_size")


def temporal_splits(n_samples: int, config: WalkForwardConfig) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    test_start = config.initial_train_size + config.gap_size
    while test_start + config.test_size <= n_samples:
        train_end = test_start - config.gap_size
        train_start = 0 if config.mode == "expanding" else max(0, train_end - (config.train_size or config.initial_train_size))
        train = np.arange(train_start, train_end)
        test = np.arange(test_start, test_start + config.test_size)
        assert_disjoint(train, test)
        yield train, test
        test_start += config.step_size


def walk_forward_evaluate(
    features: pd.DataFrame,
    target: pd.Series,
    fit_predict: Callable[[pd.DataFrame, pd.Series, pd.DataFrame], np.ndarray],
    config: WalkForwardConfig,
    transformer_factory: Callable[[], object] | None = None,
) -> pd.DataFrame:
    """Ogni transformer viene creato/fittato esclusivamente sul training fold."""
    records: list[dict] = []
    for fold, (train_idx, test_idx) in enumerate(temporal_splits(len(features), config)):
        x_train, x_test = features.iloc[train_idx].copy(), features.iloc[test_idx].copy()
        y_train, y_test = target.iloc[train_idx].copy(), target.iloc[test_idx].copy()
        if transformer_factory:
            transformer = transformer_factory()
            x_train = pd.DataFrame(transformer.fit_transform(x_train), index=x_train.index)
            x_test = pd.DataFrame(transformer.transform(x_test), index=x_test.index)
        prediction = np.asarray(fit_predict(x_train, y_train, x_test)).reshape(-1)
        if len(prediction) != len(test_idx):
            raise ValueError("Il modello deve produrre una previsione per ogni riga di test")
        for idx, observed, forecast in zip(y_test.index, y_test, prediction):
            records.append({"date": idx, "actual": observed, "forecast": forecast,
                            "error": forecast - observed, "fold": fold,
                            "train_end": features.index[train_idx[-1]], "forecast_origin": features.index[test_idx[0]]})
    return pd.DataFrame(records)
