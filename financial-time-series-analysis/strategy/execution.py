"""Backtest causale: il segnale a t viene eseguito da t+1 e valutato dopo i costi."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .portfolio_metrics import portfolio_metrics
from .transaction_costs import TransactionCostModel


def backtest_after_costs(
    returns: pd.Series,
    target_positions: pd.Series,
    cost_model: TransactionCostModel,
    spread_bps: pd.Series | float | None = None,
    funding_rate: pd.Series | float = 0.0,
    borrow_rate: pd.Series | float = 0.0,
    volatility: pd.Series | float = 0.0,
    periods_per_year: int = 365,
    execution_lag: int = 1,
) -> tuple[pd.DataFrame, dict]:
    if execution_lag < 0:
        raise ValueError("execution_lag deve essere non negativo")
    index = returns.index
    position = target_positions.reindex(index).fillna(0.0).shift(execution_lag).fillna(0.0).clip(-1, 1)
    turnover = position.diff().abs().fillna(position.abs())
    spread = cost_model.default_spread_bps if spread_bps is None else spread_bps
    spread = pd.Series(spread, index=index, dtype=float) if np.isscalar(spread) else spread_bps.reindex(index).fillna(cost_model.default_spread_bps)
    funding = pd.Series(funding_rate, index=index, dtype=float) if np.isscalar(funding_rate) else funding_rate.reindex(index).fillna(0.0)
    borrow = pd.Series(borrow_rate, index=index, dtype=float) if np.isscalar(borrow_rate) else borrow_rate.reindex(index).fillna(0.0)
    vol = pd.Series(volatility, index=index, dtype=float) if np.isscalar(volatility) else volatility.reindex(index).fillna(0.0)
    fee_bps = cost_model.taker_fee_bps
    slippage_bps = cost_model.slippage_bps(volatility=vol, position_size=turnover)
    result = pd.DataFrame(index=index)
    result["position"] = position
    result["turnover"] = turnover
    result["gross_pnl"] = position * returns.fillna(0.0)
    result["commission_cost"] = turnover * fee_bps / 10_000
    result["spread_cost"] = turnover * spread / 20_000
    result["slippage_cost"] = turnover * slippage_bps / 10_000
    result["funding_cost"] = position * funding if cost_model.include_funding else 0.0
    result["borrow_cost"] = position.clip(upper=0).abs() * borrow
    cost_columns = ["commission_cost", "spread_cost", "slippage_cost", "funding_cost", "borrow_cost"]
    result["net_pnl"] = result["gross_pnl"] - result[cost_columns].sum(axis=1)
    result["cumulative_gross_return"] = (1 + result["gross_pnl"]).cumprod() - 1
    result["cumulative_net_return"] = (1 + result["net_pnl"]).cumprod() - 1
    return result, portfolio_metrics(result, periods_per_year)


def cost_sensitivity(returns, positions, model, scenarios=("optimistic", "base", "stress"), **kwargs) -> dict:
    analyses = {}
    for scenario in scenarios:
        pnl, metrics = backtest_after_costs(returns, positions, model.scenario(scenario), **kwargs)
        analyses[scenario] = {"pnl": pnl, "metrics": metrics}
    base_ok = analyses.get("base", {}).get("metrics", {}).get("cumulative_net_return", -np.inf) > 0
    stress_ok = analyses.get("stress", {}).get("metrics", {}).get("cumulative_net_return", -np.inf) > 0
    analyses["economically_useful"] = bool(base_ok and stress_ok)
    return analyses
