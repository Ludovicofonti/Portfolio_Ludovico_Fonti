from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

import pipelines.platform as platform
from pipelines.platform import ResearchOptions, run_research


def test_real_mart_shape_runs_to_report_and_registry(tmp_path, monkeypatch):
    rng = np.random.default_rng(42)
    rows = 620
    origin = pd.date_range("2025-01-01", periods=rows, freq="h", tz="UTC")
    returns = rng.normal(0, 0.005, rows)
    target = np.roll(returns, -1)
    target[-1] = np.nan
    frame = pd.DataFrame({
        "symbol": "BTCUSDT",
        "interval": "1h",
        "forecast_origin": origin,
        "available_time": origin,
        "quality_flag": "valid",
        "return_1": returns,
        "high_low_range": np.abs(returns) * 2,
        "close_open_return": returns * 0.7,
        "taker_buy_ratio": rng.uniform(0.3, 0.7, rows),
        "funding_rate": 0.0,
        "funding_zscore": 0.0,
        "open_interest_change": rng.normal(0, 0.001, rows),
        "open_interest_zscore": rng.normal(0, 1, rows),
        "close": 100 * np.exp(np.cumsum(returns)),
        "target_return_1": target,
    })
    database = tmp_path / "finance.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("create schema analytics")
        connection.register("source_frame", frame)
        connection.execute("create table analytics.fct_model_dataset as select * from source_frame")

    monkeypatch.setattr(platform, "PROJECT_ROOT", tmp_path)
    summary = run_research(ResearchOptions(database=str(database)))

    assert summary["forecast_observations"] > 0
    assert summary["promotion"]["promoted"] in {True, False}
    assert Path(summary["reports"]["technical"]).exists()
    assert Path(summary["reports"]["business"]).exists()
    assert Path(summary["artifact_path"]).joinpath("predictions.csv").exists()
    assert Path(summary["charts"]["forecast_vs_actual"]).exists()
    with duckdb.connect(str(tmp_path / "data" / "experiments.duckdb"), read_only=True) as connection:
        status = connection.execute(
            "select status from experiment_runs where run_id = ?", [summary["run_id"]]
        ).fetchone()[0]
    assert status == "completed"
