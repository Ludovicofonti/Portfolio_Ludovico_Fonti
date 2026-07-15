from reporting.business_report import render_business_summary


def test_business_report_uses_tables_and_charts_instead_of_json_blocks():
    context = {
        "run_id": "run-1",
        "asset": "BTC-USDT",
        "task": "return",
        "model": "ridge_return",
        "horizon": 1,
        "data_start": "2026-01-01",
        "data_as_of": "2026-01-31",
        "forecast_observations": 100,
        "primary_metric": "mae",
        "baseline_comparison": {
            "model": {"mae": 0.9, "information_coefficient": 0.1},
            "best_baseline_name": "zero_return",
            "best_baseline": {"mae": 1.0},
            "diebold_mariano": {"p_value": 0.03, "conclusion": "modello migliore"},
        },
        "net_performance": {
            "cumulative_net_return": 0.04,
            "cumulative_gross_return": 0.05,
            "sharpe_ratio": 1.2,
            "maximum_drawdown": -0.02,
            "hit_rate": 0.55,
            "exposure": 0.3,
            "turnover": 12,
            "cost_drag": 0.01,
        },
        "cost_impact": {
            "optimistic": {"cumulative_net_return": 0.05, "sharpe_ratio": 1.4},
            "base": {"cumulative_net_return": 0.04, "sharpe_ratio": 1.2},
            "stress": {"cumulative_net_return": 0.01, "sharpe_ratio": 0.4},
        },
        "regime": {"low_volatility": {"count": 80, "sum": 0.03, "mean": 0.001, "std": 0.01}},
        "risk_threshold": {
            "conditional_coverage": {
                "coverage": {
                    "number_of_violations": 4,
                    "number_of_observations": 100,
                    "expected_violation_rate": 0.05,
                    "observed_violation_rate": 0.04,
                    "result": "pass",
                    "p_value": 0.6,
                }
            },
            "expected_shortfall": {"mean_exceedance_loss": -0.03, "mean_predicted_es": -0.025},
            "evt_pot": {"var": -0.04, "expected_shortfall": -0.06, "shape": 0.2},
        },
        "charts": {"cumulative_performance": "artifacts/run-1/cumulative_performance.png"},
    }
    promotion = {
        "promoted": True,
        "checks": {"beats_baseline": True, "positive_after_costs": True},
        "rejection_reasons": [],
    }

    report = render_business_summary(context, promotion)

    assert "| KPI | Valore | Interpretazione |" in report
    assert "![Performance cumulata netta e lorda](artifacts/run-1/cumulative_performance.png)" in report
    assert "~~~json" not in report
