import numpy as np
import pandas as pd
import pytest

from evaluation.walk_forward import WalkForwardConfig, temporal_splits, walk_forward_evaluate
from features.leakage_checks import LeakageError, assert_available_at_origin, causal_rolling


def test_gap_and_non_overlapping_splits():
    config = WalkForwardConfig(initial_train_size=10, test_size=3, step_size=3, gap_size=2)
    train, test = next(temporal_splits(30, config))
    assert train[-1] == 9
    assert test[0] == 12
    assert not set(train) & set(test)


def test_future_available_time_fails():
    frame = pd.DataFrame({"available_time": pd.to_datetime(["2024-01-01", "2024-01-03"], utc=True)})
    with pytest.raises(LeakageError):
        assert_available_at_origin(frame, pd.Timestamp("2024-01-02", tz="UTC"))


def test_causal_rolling_excludes_current_row():
    series = pd.Series([1.0, 2.0, 100.0])
    assert causal_rolling(series, 2).iloc[2] == 1.5


def test_transformer_is_fitted_per_fold():
    fitted_maxima = []
    class Transformer:
        def fit_transform(self, values):
            fitted_maxima.append(values.max().max()); return values
        def transform(self, values): return values
    x = pd.DataFrame({"x": np.arange(20.0)}); y = pd.Series(np.arange(20.0))
    cfg = WalkForwardConfig(initial_train_size=10, test_size=5, step_size=5)
    walk_forward_evaluate(x, y, lambda xt, yt, xv: np.repeat(yt.mean(), len(xv)), cfg, Transformer)
    assert fitted_maxima[0] == 9
