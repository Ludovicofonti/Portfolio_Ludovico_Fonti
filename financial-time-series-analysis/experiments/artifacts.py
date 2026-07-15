"""Salvataggio locale di configurazioni, metriche, previsioni e residui."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def save_artifacts(run_dir: str | Path, *, configuration: dict, metrics: dict,
                   predictions: pd.DataFrame | None = None, residuals: pd.Series | None = None) -> Path:
    path = Path(run_dir); path.mkdir(parents=True, exist_ok=True)
    (path / "configuration.json").write_text(json.dumps(configuration, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (path / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True, default=str), encoding="utf-8")
    if predictions is not None: predictions.to_csv(path / "predictions.csv", index=True)
    if residuals is not None: residuals.rename("residual").to_csv(path / "residuals.csv", index=True)
    return path
