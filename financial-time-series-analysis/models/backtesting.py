"""
models/backtesting.py — Walk-forward validation per modelli di serie storiche.

Metriche: MAE, RMSE, Huber loss, information coefficient e Direction Accuracy.
"""

import warnings
from typing import Callable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


def walk_forward_validation(
    model_fn: Callable[[pd.Series, int], np.ndarray],
    series: pd.Series,
    train_window: int = 500,
    test_window: int = 20,
    step: int = 20,
) -> pd.DataFrame:
    """
    Walk-forward validation: l'allenamento scorre di 'step' osservazioni alla volta.

    model_fn(train_series, steps_ahead) → np.ndarray di forecast

    Returns DataFrame con colonne: date, actual, forecast, error
    """
    records = []
    n = len(series)
    starts = range(train_window, n - test_window + 1, step)

    print(f"  Walk-forward: {len(list(starts))} finestre, train={train_window}, test={test_window}")
    for i, start in enumerate(starts):
        train = series.iloc[:start]
        test  = series.iloc[start: start + test_window]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fc = model_fn(train, test_window)
                # fc può essere ndarray o pd.Series
                fc_vals = np.array(fc).flatten()[:test_window]
                for j, (date, actual) in enumerate(test.items()):
                    if j < len(fc_vals):
                        records.append({
                            "date": date,
                            "actual": actual,
                            "forecast": fc_vals[j],
                            "error": fc_vals[j] - actual,
                            "window": i,
                        })
        except Exception as exc:
            print(f"  [WARN] Finestra {i} fallita: {exc}")
            continue

    return pd.DataFrame(records)


def compute_metrics(df: pd.DataFrame) -> dict:
    """Metriche sui rendimenti. La MAPE è intenzionalmente esclusa."""
    if df.empty:
        return {}
    actual   = df["actual"].values
    forecast = df["forecast"].values
    errors   = df["error"].values

    mae  = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))
    abs_error = np.abs(errors)
    delta = float(np.nanstd(actual)) or 1.0
    huber = float(np.mean(np.where(abs_error <= delta, 0.5 * errors**2, delta * (abs_error - 0.5 * delta))))
    ic = float(stats.pearsonr(actual, forecast).statistic) if len(actual) > 2 and np.std(actual) and np.std(forecast) else float("nan")

    # Direction accuracy: segno del forecast == segno dell'actual?
    dir_acc = float(np.mean(np.sign(actual) == np.sign(forecast)) * 100)

    metrics = {
        "MAE":  round(mae, 6),
        "RMSE": round(rmse, 6),
        "Huber_Loss": round(huber, 6),
        "Information_Coefficient": round(ic, 6),
        "Direction_Accuracy_%": round(dir_acc, 2),
        "N_forecasts": len(actual),
    }
    print("\n  Metriche Backtesting:")
    for k, v in metrics.items():
        print(f"    {k:<25} {v}")
    return metrics


def diebold_mariano_test(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    label_a: str = "Model A",
    label_b: str = "Model B",
) -> dict:
    """
    Diebold-Mariano test: verifica se le previsioni di A sono statisticamente
    migliori di quelle di B (H0: nessuna differenza nella loss function).

    Usa la squared error loss.
    """
    # Allinea per data
    merged = df_a[["date", "actual", "error"]].rename(columns={"error": "err_a"}).merge(
        df_b[["date", "error"]].rename(columns={"error": "err_b"}),
        on="date",
    )
    d = merged["err_a"]**2 - merged["err_b"]**2
    n = len(d)
    dm_stat = float(d.mean() / (d.std() / np.sqrt(n)))
    p_value = float(2 * (1 - stats.t.cdf(abs(dm_stat), df=n - 1)))
    conclusion = f"{label_b} è migliore" if dm_stat > 0 else f"{label_a} è migliore"
    print(f"\n  Diebold-Mariano test ({label_a} vs {label_b}):")
    print(f"    DM stat = {dm_stat:.4f}  p-value = {p_value:.4f}")
    print(f"    {'Rifiuta H0 → ' + conclusion if p_value < 0.05 else 'Non rifiuta H0 (nessuna differenza significativa)'}")
    return {"dm_stat": dm_stat, "p_value": p_value, "conclusion": conclusion}


def plot_backtest(df: pd.DataFrame, title: str = "Walk-forward Backtest") -> None:
    """Visualizza actual vs forecast sul periodo di validazione."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    axes[0].plot(df["date"], df["actual"],   color="steelblue",  linewidth=0.9, label="Actual")
    axes[0].plot(df["date"], df["forecast"], color="firebrick",  linewidth=0.9, linestyle="--", label="Forecast")
    axes[0].axhline(0, color="black", linewidth=0.5, linestyle=":")
    axes[0].set_title(title)
    axes[0].set_ylabel("Log Return")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[1].bar(df["date"], df["error"], color="darkorange", alpha=0.7, width=1.5)
    axes[1].axhline(0, color="black", linewidth=0.7)
    axes[1].set_title("Errore di previsione (forecast - actual)")
    axes[1].set_ylabel("Errore")
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
