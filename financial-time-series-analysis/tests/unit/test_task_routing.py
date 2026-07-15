import numpy as np
import pytest

from pipelines.platform import ResearchOptions, _resolved_model, _target_column, _task_metrics


@pytest.mark.parametrize(
    ("task", "horizon", "target", "model"),
    [
        ("return", 4, "target_return_4", "ridge_return"),
        ("direction", 24, "target_direction_24", "ridge_direction"),
        ("volatility", 24, "target_volatility_24", "garch_student_t_1_1"),
        ("tail", 24, "target_tail_return_24", "ridge_tail"),
    ],
)
def test_task_target_and_auto_model(task, horizon, target, model):
    options = ResearchOptions(task=task, horizon=horizon)
    assert _target_column(options) == target
    assert _resolved_model(options) == model


def test_volatility_requires_24_period_target():
    with pytest.raises(ValueError, match="richiede --horizon 24"):
        _target_column(ResearchOptions(task="volatility", horizon=1))


def test_task_specific_metrics():
    direction = _task_metrics("direction", [0, 1, 1], [0.2, 0.8, 0.7])
    volatility = _task_metrics("volatility", [0.1, 0.2], [0.11, 0.19])
    tail = _task_metrics("tail", [-0.2, -0.1], [-0.18, -0.12])

    assert 0 <= direction["brier_score"] <= 1
    assert np.isfinite(volatility["qlike"])
    assert "pinball_loss_05" in tail
