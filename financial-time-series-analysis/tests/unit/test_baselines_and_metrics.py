import numpy as np
import pandas as pd

from baselines.risk import historical_var, normal_var
from baselines.returns import historical_mean, last_observed_return, zero_return
from evaluation.metrics import classification_metrics, qlike, regression_metrics


def test_return_baselines():
    series = pd.Series([0.1, -0.1, 0.2])
    assert zero_return(series) == 0
    assert np.isclose(historical_mean(series), series.mean())
    assert last_observed_return(series) == 0.2


def test_metrics_exclude_mape_and_include_ic():
    metrics = regression_metrics([0.0, 1.0, 2.0], [0.0, 1.1, 1.9])
    assert "information_coefficient" in metrics
    assert all("mape" not in name.lower() for name in metrics)
    assert qlike([1, 2], [1, 2]) < qlike([1, 2], [4, 4])


def test_classification_and_var_baselines():
    metrics = classification_metrics([0, 0, 1, 1], [0.1, 0.4, 0.7, 0.9])
    assert metrics["balanced_accuracy"] == 1.0
    returns = pd.Series(np.linspace(-0.10, 0.10, 101))
    assert historical_var(returns) < 0
    assert normal_var(returns) < 0
