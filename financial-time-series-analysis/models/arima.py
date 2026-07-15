"""
models/arima.py — ARIMA per la media condizionale dei rendimenti.
Refactoring da models.py con lettura opzionale da DuckDB.
"""

import warnings
from itertools import product

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox

from models.validation import residual_diagnostics


def load_returns_from_db(symbol: str, db_path: str = "finance.duckdb") -> pd.Series:
    """Carica i rendimenti logaritmici di un asset da DuckDB."""
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute(
        "SELECT date, log_return FROM analytics.fct_asset_returns "
        "WHERE symbol = ? ORDER BY date",
        [symbol],
    ).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["log_return"].dropna()


def select_arima_order(
    series: pd.Series,
    p_range: range = range(0, 4),
    d: int = 0,
    q_range: range = range(0, 4),
) -> tuple[int, int, int]:
    """Grid search su (p, d, q) minimizzando AIC."""
    print("  Ricerca ordine ARIMA ottimale (AIC)...")
    best_aic, best_order = np.inf, (1, d, 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p, q in product(p_range, q_range):
            if p == 0 and q == 0:
                continue
            try:
                m = ARIMA(series, order=(p, d, q)).fit()
                if m.aic < best_aic:
                    best_aic, best_order = m.aic, (p, d, q)
            except Exception:
                continue
    print(f"  Ordine ottimale: ARIMA{best_order}  AIC={best_aic:.4f}")
    return best_order


def fit_arima(
    series: pd.Series,
    order: tuple[int, int, int] | None = None,
    steps_ahead: int = 10,
) -> dict:
    """Adatta ARIMA e produce forecast."""
    if order is None:
        order = select_arima_order(series)
    print(f"  Fitting ARIMA{order}...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ARIMA(series, order=order).fit()
    print(fitted.summary())
    lb = acorr_ljungbox(fitted.resid, lags=[10, 20], return_df=True)
    print("\n  Ljung-Box (p > 0.05 → white noise):\n", lb.to_string())
    fc = fitted.get_forecast(steps=steps_ahead)
    return {
        "model": fitted,
        "order": order,
        "forecast": fc.predicted_mean,
        "conf_int": fc.conf_int(alpha=0.05),
        "residuals": fitted.resid,
        "diagnostics": residual_diagnostics(fitted.resid),
        "aic": fitted.aic,
        "bic": fitted.bic,
    }


def plot_arima_forecast(
    series: pd.Series, result: dict, ticker: str = "", last_n: int = 120
) -> None:
    fc, ci, order = result["forecast"], result["conf_int"], result["order"]
    tail = series.iloc[-last_n:]
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    ax = axes[0]
    ax.plot(tail.index, tail.values, color="steelblue", label="Storico", linewidth=0.9)
    ax.plot(fc.index, fc.values, color="firebrick", linestyle="--", linewidth=1.5,
            label=f"Forecast ARIMA{order}")
    ax.fill_between(ci.index, ci.iloc[:, 0], ci.iloc[:, 1],
                    color="firebrick", alpha=0.2, label="IC 95%")
    ax.axhline(0, color="black", linewidth=0.7, linestyle=":")
    ax.set_title(f"ARIMA{order} — Forecast ({ticker})")
    ax.set_ylabel("Log Return")
    ax.legend()
    ax.grid(True, alpha=0.3)
    resid = result["residuals"]
    axes[1].plot(resid.index, resid.values, color="darkorange", linewidth=0.7, alpha=0.8)
    axes[1].axhline(0, color="black", linewidth=0.7, linestyle=":")
    axes[1].set_title("Residui ARIMA")
    axes[1].set_ylabel("Residuo")
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
