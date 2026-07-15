"""
models/sarima.py — SARIMA / SARIMAX con variabili esogene opzionali.
"""

import warnings
from itertools import product

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX

from models.validation import residual_diagnostics


def select_sarima_order(
    series: pd.Series,
    p_range: range = range(0, 3),
    d: int = 0,
    q_range: range = range(0, 3),
    seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 7),
) -> tuple:
    """Grid search su (p, d, q) con stagionalità fissa — minimizza AIC."""
    print("  Ricerca ordine SARIMA ottimale (AIC)...")
    best_aic, best_order = np.inf, (1, d, 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p, q in product(p_range, q_range):
            if p == 0 and q == 0:
                continue
            try:
                m = SARIMAX(
                    series,
                    order=(p, d, q),
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False)
                if m.aic < best_aic:
                    best_aic, best_order = m.aic, (p, d, q)
            except Exception:
                continue
    S = seasonal_order
    print(f"  Ordine ottimale: SARIMA{best_order}×{S}  AIC={best_aic:.4f}")
    return best_order, seasonal_order


def fit_sarima(
    series: pd.Series,
    order: tuple[int, int, int] | None = None,
    seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 7),
    exog: pd.DataFrame | None = None,
    steps_ahead: int = 10,
) -> dict:
    """
    Fitta SARIMA o SARIMAX (con esogene).
    exog: DataFrame allineato a 'series' con variabili macro (VIX, yield spread, ecc.)
    """
    if order is None:
        order, seasonal_order = select_sarima_order(series, seasonal_order=seasonal_order)
    label = f"SARIMA{order}×{seasonal_order}"
    print(f"  Fitting {label}...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = SARIMAX(
            series,
            exog=exog,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)
    print(fitted.summary())
    fc = fitted.get_forecast(steps=steps_ahead)
    return {
        "model": fitted,
        "order": order,
        "seasonal_order": seasonal_order,
        "label": label,
        "forecast": fc.predicted_mean,
        "conf_int": fc.conf_int(alpha=0.05),
        "residuals": fitted.resid,
        "diagnostics": residual_diagnostics(fitted.resid),
        "aic": fitted.aic,
        "bic": fitted.bic,
    }


def plot_sarima_forecast(
    series: pd.Series, result: dict, ticker: str = "", last_n: int = 120
) -> None:
    fc, ci = result["forecast"], result["conf_int"]
    label = result["label"]
    tail = series.iloc[-last_n:]
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(tail.index, tail.values, color="steelblue", label="Storico", linewidth=0.9)
    ax.plot(fc.index, fc.values, color="seagreen", linestyle="--", linewidth=1.5,
            label=f"Forecast {label}")
    ax.fill_between(ci.index, ci.iloc[:, 0], ci.iloc[:, 1],
                    color="seagreen", alpha=0.2, label="IC 95%")
    ax.axhline(0, color="black", linewidth=0.7, linestyle=":")
    ax.set_title(f"{label} — Forecast ({ticker})")
    ax.set_ylabel("Log Return")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
