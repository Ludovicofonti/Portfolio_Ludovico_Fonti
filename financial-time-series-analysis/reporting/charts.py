"""Grafici diagnostici headless salvati come artefatti riproducibili."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save_diagnostic_charts(
    output_dir: str | Path,
    *,
    predictions: pd.DataFrame,
    pnl: pd.DataFrame,
    var_forecast,
) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    charts: dict[str, str] = {}

    recent = predictions.tail(500)
    fig, axis = plt.subplots(figsize=(12, 4))
    axis.plot(recent["date"], recent["actual"], label="Actual", linewidth=1)
    axis.plot(recent["date"], recent["forecast"], label="Forecast", linewidth=1)
    axis.axhline(0, color="black", linewidth=0.5)
    axis.set_title("Forecast out-of-sample")
    axis.legend()
    fig.tight_layout()
    forecast_path = path / "forecast_vs_actual.png"
    fig.savefig(forecast_path, dpi=150)
    plt.close(fig)
    charts["forecast_vs_actual"] = str(forecast_path)

    fig, axis = plt.subplots(figsize=(12, 4))
    axis.plot(pnl.index, pnl["cumulative_gross_return"], label="Gross")
    axis.plot(pnl.index, pnl["cumulative_net_return"], label="Net")
    axis.set_title("Performance cumulata prima e dopo i costi")
    axis.legend()
    fig.tight_layout()
    performance_path = path / "cumulative_performance.png"
    fig.savefig(performance_path, dpi=150)
    plt.close(fig)
    charts["cumulative_performance"] = str(performance_path)

    var = np.asarray(var_forecast, dtype=float)
    actual = predictions["actual"].to_numpy(float)
    valid = np.isfinite(var) & np.isfinite(actual)
    fig, axis = plt.subplots(figsize=(12, 4))
    dates = pd.to_datetime(predictions.loc[valid, "date"], utc=True)
    axis.plot(dates, actual[valid], label="Return", linewidth=0.8)
    axis.plot(dates, var[valid], label="VaR forecast", linewidth=1)
    breaches = actual[valid] < var[valid]
    axis.scatter(dates[breaches], actual[valid][breaches], color="red", s=12, label="Violation")
    axis.set_title("VaR rolling e violazioni")
    axis.legend()
    fig.tight_layout()
    risk_path = path / "var_violations.png"
    fig.savefig(risk_path, dpi=150)
    plt.close(fig)
    charts["var_violations"] = str(risk_path)
    return charts
