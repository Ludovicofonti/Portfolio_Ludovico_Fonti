import numpy as np
import pandas as pd

from evaluation.walk_forward import WalkForwardConfig, walk_forward_evaluate
from features.targets import build_targets
from reporting.business_report import promotion_decision
from strategy.execution import backtest_after_costs
from strategy.transaction_costs import TransactionCostModel


def test_feature_to_walkforward_to_net_backtest():
    rng = np.random.default_rng(42); returns = rng.normal(0, 0.01, 80)
    prices = 100 * np.exp(np.cumsum(returns)); index = pd.date_range("2024-01-01", periods=80, freq="h")
    data = build_targets(pd.DataFrame({"close": prices}, index=index), horizons=[1]).dropna()
    x = pd.DataFrame({"lag_return": np.log(data.close).diff().shift(1)}, index=data.index).fillna(0)
    y = data.target_return_1
    cfg = WalkForwardConfig(initial_train_size=40, test_size=10, step_size=10, gap_size=1)
    result = walk_forward_evaluate(x, y, lambda xt, yt, xv: np.repeat(yt.mean(), len(xv)), cfg)
    positions = pd.Series(np.sign(result.forecast.values), index=pd.DatetimeIndex(result.date))
    realized = pd.Series(result.actual.values, index=pd.DatetimeIndex(result.date))
    pnl, metrics = backtest_after_costs(realized, positions, TransactionCostModel(taker_fee_bps=5), periods_per_year=8760)
    decision = promotion_decision(model_metric=1, baseline_metric=2, higher_is_better=False,
                                  net_return=metrics["cumulative_net_return"], stability_score=0.8,
                                  calibration_score=0.8)
    assert len(pnl) == len(result)
    assert "promoted" in decision
