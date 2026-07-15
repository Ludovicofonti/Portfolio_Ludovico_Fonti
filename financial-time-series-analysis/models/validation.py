"""
models/validation.py - Diagnostica e validazione statistica dei modelli.

Le funzioni qui dentro separano la valutazione metodologica dalla stima dei
modelli: baseline naive, diagnostica residui, test direzionali, DM corretto e
backtest VaR.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch


def residual_diagnostics(residuals: pd.Series | np.ndarray, lags: list[int] | None = None) -> dict:
    """Diagnostica standard sui residui di ARIMA/SARIMA."""
    if lags is None:
        lags = [10, 20]
    resid = pd.Series(residuals).dropna()
    lb = acorr_ljungbox(resid, lags=lags, return_df=True)
    arch_stat, arch_pvalue, _, _ = het_arch(resid, nlags=min(10, max(1, len(resid) // 10)))
    jb_stat, jb_pvalue = stats.jarque_bera(resid)
    return {
        "ljung_box": {
            int(idx): {
                "stat": float(row["lb_stat"]),
                "p_value": float(row["lb_pvalue"]),
                "white_noise": bool(row["lb_pvalue"] >= 0.05),
            }
            for idx, row in lb.iterrows()
        },
        "arch_lm": {
            "stat": float(arch_stat),
            "p_value": float(arch_pvalue),
            "has_arch_effect": bool(arch_pvalue < 0.05),
        },
        "jarque_bera": {
            "stat": float(jb_stat),
            "p_value": float(jb_pvalue),
            "normal_residuals": bool(jb_pvalue >= 0.05),
        },
    }


def garch_diagnostics(result: dict, lags: list[int] | None = None) -> dict:
    """Diagnostica su residui standardizzati e persistenza di un modello GARCH."""
    if lags is None:
        lags = [10, 20]
    fitted = result.get("model")
    if fitted is None:
        return {}

    std_resid = pd.Series(fitted.std_resid).replace([np.inf, -np.inf], np.nan).dropna()
    lb_resid = acorr_ljungbox(std_resid, lags=lags, return_df=True)
    lb_sq = acorr_ljungbox(std_resid**2, lags=lags, return_df=True)
    params = fitted.params
    alpha = float(params.get("alpha[1]", 0.0))
    beta = float(params.get("beta[1]", 0.0))
    gamma = float(params.get("gamma[1]", 0.0))
    persistence = alpha + beta + 0.5 * gamma

    def _table(lb: pd.DataFrame) -> dict:
        return {
            int(idx): {
                "stat": float(row["lb_stat"]),
                "p_value": float(row["lb_pvalue"]),
                "passes": bool(row["lb_pvalue"] >= 0.05),
            }
            for idx, row in lb.iterrows()
        }

    return {
        "params": {str(k): float(v) for k, v in params.items()},
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
        "persistence": float(persistence),
        "stationary_variance": bool(persistence < 1.0),
        "ljung_box_std_resid": _table(lb_resid),
        "ljung_box_squared_std_resid": _table(lb_sq),
    }


def naive_forecast_validation(
    series: pd.Series,
    train_window: int = 500,
    test_window: int = 20,
    step: int = 20,
) -> dict[str, pd.DataFrame]:
    """Crea baseline walk-forward: zero-return e media storica expanding."""
    records_zero = []
    records_mean = []
    n = len(series)
    for i, start in enumerate(range(train_window, n - test_window + 1, step)):
        train = series.iloc[:start]
        test = series.iloc[start:start + test_window]
        mean_fc = float(train.mean())
        for date, actual in test.items():
            records_zero.append({
                "date": date,
                "actual": actual,
                "forecast": 0.0,
                "error": -actual,
                "window": i,
            })
            records_mean.append({
                "date": date,
                "actual": actual,
                "forecast": mean_fc,
                "error": mean_fc - actual,
                "window": i,
            })
    return {
        "Zero Return": pd.DataFrame(records_zero),
        "Historical Mean": pd.DataFrame(records_mean),
    }


def direction_accuracy_test(df: pd.DataFrame, expected_prob: float = 0.5) -> dict:
    """Test binomiale sulla Direction Accuracy."""
    valid = df[["actual", "forecast"]].dropna()
    hits = (np.sign(valid["actual"].values) == np.sign(valid["forecast"].values)).astype(int)
    n = int(len(hits))
    successes = int(hits.sum())
    if n == 0:
        return {"n": 0, "successes": 0, "accuracy_pct": None, "p_value": None, "significant": False}
    res = stats.binomtest(successes, n, expected_prob, alternative="greater")
    return {
        "n": n,
        "successes": successes,
        "accuracy_pct": float(successes / n * 100),
        "p_value": float(res.pvalue),
        "significant": bool(res.pvalue < 0.05),
    }


def diebold_mariano_hac(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    label_a: str = "Model A",
    label_b: str = "Model B",
    loss: str = "squared",
    horizon: int = 1,
) -> dict:
    """
    Diebold-Mariano con varianza HAC/Newey-West sulla differenza di loss.

    H0: uguale accuratezza predittiva. Statistica positiva => B migliore.
    """
    merged = df_a[["date", "error"]].rename(columns={"error": "err_a"}).merge(
        df_b[["date", "error"]].rename(columns={"error": "err_b"}),
        on="date",
    )
    if merged.empty:
        return {}
    if loss == "absolute":
        d = np.abs(merged["err_a"].values) - np.abs(merged["err_b"].values)
    else:
        d = merged["err_a"].values**2 - merged["err_b"].values**2

    n = len(d)
    d_mean = float(np.mean(d))
    lag = max(0, min(horizon - 1, int(math.floor(n ** 0.25))))
    centered = d - d_mean
    gamma0 = float(np.mean(centered * centered))
    long_run_var = gamma0
    for k in range(1, lag + 1):
        gamma = float(np.mean(centered[k:] * centered[:-k]))
        weight = 1 - k / (lag + 1)
        long_run_var += 2 * weight * gamma
    long_run_var = max(long_run_var, 1e-12)
    dm_stat = d_mean / math.sqrt(long_run_var / n)
    p_value = float(2 * (1 - stats.norm.cdf(abs(dm_stat))))
    conclusion = f"{label_b} migliore" if dm_stat > 0 else f"{label_a} migliore"
    return {
        "dm_stat": float(dm_stat),
        "p_value": p_value,
        "hac_lag": lag,
        "loss": loss,
        "n": int(n),
        "conclusion": conclusion,
        "significant": bool(p_value < 0.05),
    }


def var_backtest(returns: pd.Series, var_level: float, confidence: float = 0.95) -> dict:
    """
    Backtest Kupiec POF per una soglia VaR sui rendimenti.

    var_level deve essere espresso come rendimento soglia, es. -0.04.
    """
    clean = pd.Series(returns).dropna()
    breaches = clean < var_level
    n = int(len(clean))
    x = int(breaches.sum())
    expected_prob = 1 - confidence
    expected_breaches = n * expected_prob
    observed_prob = x / n if n else float("nan")
    if n == 0:
        return {}
    if x == 0 or x == n:
        lr_pof = float("nan")
        p_value = float("nan")
    else:
        lr_pof = -2 * (
            (n - x) * math.log((1 - expected_prob) / (1 - observed_prob))
            + x * math.log(expected_prob / observed_prob)
        )
        p_value = float(1 - stats.chi2.cdf(lr_pof, df=1))
    return {
        "confidence": confidence,
        "var_level": float(var_level),
        "n": n,
        "breaches": x,
        "expected_breaches": float(expected_breaches),
        "breach_rate_pct": float(observed_prob * 100),
        "kupiec_lr": float(lr_pof) if not math.isnan(lr_pof) else None,
        "kupiec_p_value": p_value if not math.isnan(p_value) else None,
        "valid_coverage": bool(p_value >= 0.05) if not math.isnan(p_value) else None,
    }


def summarize_model_validation(backtests: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Raccoglie Direction Accuracy test per un set di backtest."""
    return {
        name: direction_accuracy_test(df)
        for name, df in backtests.items()
        if df is not None and not df.empty
    }
