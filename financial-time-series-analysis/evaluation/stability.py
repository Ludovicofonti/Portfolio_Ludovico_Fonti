"""Stabilità delle metriche fra fold, anni, asset e regimi."""

import numpy as np
import pandas as pd


def fold_stability(values) -> dict:
    clean = pd.Series(values, dtype=float).dropna()
    if clean.empty:
        return {}
    mean, std = float(clean.mean()), float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
    score = 1 / (1 + abs(std / mean)) if mean else 0.0
    return {"mean": mean, "std": std, "worst": float(clean.min()), "best": float(clean.max()),
            "positive_fold_share": float((clean > 0).mean()), "stability_score": float(score)}


def grouped_performance(frame: pd.DataFrame, pnl_column: str = "net_pnl", groups=("regime", "year", "asset")) -> dict:
    return {group: frame.groupby(group)[pnl_column].agg(["count", "mean", "sum", "std"]).to_dict("index")
            for group in groups if group in frame.columns}
