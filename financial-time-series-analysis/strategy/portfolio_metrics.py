"""Metriche economiche calcolate sulla serie netta."""

import numpy as np
import pandas as pd


def portfolio_metrics(backtest: pd.DataFrame, periods_per_year: int) -> dict:
    net = backtest["net_pnl"].fillna(0.0)
    gross = backtest["gross_pnl"].fillna(0.0)
    equity = (1 + net).cumprod()
    drawdown = equity / equity.cummax() - 1
    downside = net[net < 0].std(ddof=1)
    annual_return = float(equity.iloc[-1] ** (periods_per_year / max(len(net), 1)) - 1) if len(net) else 0.0
    annual_vol = float(net.std(ddof=1) * np.sqrt(periods_per_year))
    sharpe = float(net.mean() / net.std(ddof=1) * np.sqrt(periods_per_year)) if net.std(ddof=1) else 0.0
    sortino = float(net.mean() / downside * np.sqrt(periods_per_year)) if downside else 0.0
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0
    wins, losses = net[net > 0], net[net < 0]
    total_cost = float((gross - net).sum())
    return {
        "cumulative_gross_return": float((1 + gross).prod() - 1),
        "cumulative_net_return": float(equity.iloc[-1] - 1) if len(equity) else 0.0,
        "annualized_return": annual_return, "annualized_volatility": annual_vol,
        "sharpe_ratio": sharpe, "sortino_ratio": sortino,
        "calmar_ratio": annual_return / abs(max_drawdown) if max_drawdown else 0.0,
        "maximum_drawdown": max_drawdown, "turnover": float(backtest["turnover"].sum()),
        "exposure": float(backtest["position"].abs().mean()), "hit_rate": float((net > 0).mean()),
        "profit_factor": float(wins.sum() / abs(losses.sum())) if losses.sum() else float("inf"),
        "average_win": float(wins.mean()) if len(wins) else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "gain_to_pain_ratio": float(net.sum() / abs(losses.sum())) if losses.sum() else float("inf"),
        "cost_drag": total_cost, "funding_drag": float(backtest["funding_cost"].sum()),
    }
