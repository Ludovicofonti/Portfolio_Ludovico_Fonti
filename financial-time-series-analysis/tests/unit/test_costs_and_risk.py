import numpy as np
import pandas as pd

from evaluation.risk_backtesting import conditional_coverage_test, expected_shortfall_backtest, kupiec_test
from strategy.execution import backtest_after_costs, cost_sensitivity
from strategy.transaction_costs import TransactionCostModel


def test_backtest_decomposes_costs_and_lags_signal():
    index = pd.date_range("2024-01-01", periods=4, freq="D")
    returns = pd.Series([0.01, 0.02, -0.01, 0.01], index=index)
    positions = pd.Series([1.0, 1.0, -1.0, -1.0], index=index)
    model = TransactionCostModel(taker_fee_bps=10, minimum_slippage_bps=2,
                                 default_spread_bps=4, include_funding=True)
    result, metrics = backtest_after_costs(returns, positions, model, funding_rate=0.0001)
    assert result.iloc[0].position == 0
    assert {"gross_pnl", "commission_cost", "spread_cost", "slippage_cost", "funding_cost", "net_pnl"} <= set(result)
    assert result.net_pnl.sum() < result.gross_pnl.sum()
    assert "maximum_drawdown" in metrics


def test_forward_target_can_disable_an_extra_execution_shift():
    index = pd.date_range("2025-01-01", periods=3, freq="h")
    returns = pd.Series([0.01, 0.01, 0.01], index=index)
    positions = pd.Series([1.0, 1.0, 1.0], index=index)
    pnl, _ = backtest_after_costs(
        returns, positions, TransactionCostModel(), execution_lag=0
    )
    assert pnl["position"].tolist() == [1.0, 1.0, 1.0]


def test_cost_sensitivity_rejects_optimistic_only_profit():
    index = pd.date_range("2024-01-01", periods=10, freq="D")
    returns = pd.Series(0.0005, index=index); positions = pd.Series([1, -1] * 5, index=index)
    model = TransactionCostModel(taker_fee_bps=10, minimum_slippage_bps=5, default_spread_bps=5)
    analysis = cost_sensitivity(returns, positions, model)
    assert set(["optimistic", "base", "stress", "economically_useful"]) <= set(analysis)


def test_var_and_es_backtests_return_required_diagnostics():
    rng = np.random.default_rng(7); returns = rng.normal(0, 1, 2000); var = np.full(2000, -1.6448536)
    kupiec = kupiec_test(returns, var, confidence=0.95)
    assert kupiec["number_of_observations"] == 2000
    assert "likelihood_ratio" in conditional_coverage_test(returns, var)
    es = expected_shortfall_backtest(returns, var, np.full(2000, -2.06))
    assert es["violations"] > 0
