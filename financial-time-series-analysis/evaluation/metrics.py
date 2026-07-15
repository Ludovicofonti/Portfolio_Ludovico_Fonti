"""Metriche coerenti con la natura del target; nessuna MAPE sui rendimenti."""

from __future__ import annotations

import numpy as np
from scipy import stats


def regression_metrics(actual, predicted, huber_delta: float = 1.0) -> dict:
    y = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    mask = np.isfinite(y) & np.isfinite(p)
    y, p = y[mask], p[mask]
    if not len(y):
        return {}
    error = p - y
    absolute = np.abs(error)
    huber = np.where(absolute <= huber_delta, 0.5 * error**2, huber_delta * (absolute - 0.5 * huber_delta))
    pearson = stats.pearsonr(y, p).statistic if len(y) > 2 and np.std(y) and np.std(p) else np.nan
    rank = stats.spearmanr(y, p).statistic if len(y) > 2 and np.std(y) and np.std(p) else np.nan
    return {"mae": float(absolute.mean()), "rmse": float(np.sqrt(np.mean(error**2))),
            "huber_loss": float(huber.mean()), "information_coefficient": float(pearson),
            "rank_correlation": float(rank), "n": int(len(y))}


def qlike(actual_variance, predicted_variance, epsilon: float = 1e-12) -> float:
    actual = np.maximum(np.asarray(actual_variance, dtype=float), epsilon)
    predicted = np.maximum(np.asarray(predicted_variance, dtype=float), epsilon)
    return float(np.mean(actual / predicted + np.log(predicted)))


def pinball_loss(actual, quantile_predictions, quantile: float) -> float:
    error = np.asarray(actual, dtype=float) - np.asarray(quantile_predictions, dtype=float)
    return float(np.mean(np.maximum(quantile * error, (quantile - 1) * error)))


def classification_metrics(actual, probability, threshold: float = 0.5) -> dict:
    y = np.asarray(actual, dtype=int)
    prob = np.clip(np.asarray(probability, dtype=float), 1e-12, 1 - 1e-12)
    pred = (prob >= threshold).astype(int)
    tp, tn = int(((y == 1) & (pred == 1)).sum()), int(((y == 0) & (pred == 0)).sum())
    fp, fn = int(((y == 0) & (pred == 1)).sum()), int(((y == 1) & (pred == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    denominator = np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / denominator) if denominator else 0.0
    positive, negative = prob[y == 1], prob[y == 0]
    roc_auc = float((positive[:, None] > negative).mean() + 0.5 * (positive[:, None] == negative).mean()) if len(positive) and len(negative) else np.nan
    order = np.argsort(-prob); sorted_y = y[order]; tp_curve = np.cumsum(sorted_y); fp_curve = np.cumsum(1 - sorted_y)
    precision_curve = tp_curve / np.maximum(tp_curve + fp_curve, 1); recall_curve = tp_curve / max(int((y == 1).sum()), 1)
    pr_auc = float(np.trapezoid(precision_curve, recall_curve)) if (y == 1).any() else np.nan
    return {"balanced_accuracy": float((recall + specificity) / 2), "precision": precision,
            "recall": recall, "f1": f1, "mcc": float(mcc),
            "roc_auc": roc_auc, "pr_auc": pr_auc,
            "brier_score": float(np.mean((prob - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(prob) + (1 - y) * np.log(1 - prob)))}
