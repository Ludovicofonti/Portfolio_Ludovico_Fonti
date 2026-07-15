"""
models/garch.py — GARCH, EGARCH, TARCH per la volatilità condizionale.
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from arch import arch_model

from models.validation import garch_diagnostics


def _fit_vol_model(series_pct: pd.Series, vol: str, p: int, q: int, dist: str) -> object:
    gm = arch_model(series_pct, vol=vol, p=p, q=q, dist=dist, rescale=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return gm.fit(disp="off", options={"maxiter": 500})


def fit_garch(
    series: pd.Series,
    p: int = 1,
    q: int = 1,
    dist: str = "t",
    steps_ahead: int = 10,
    periods_per_year: int = 252,
) -> dict:
    """GARCH(p,q) con distribuzione t di Student."""
    print(f"  Fitting GARCH({p},{q}) dist='{dist}'...")
    returns_pct = series * 100
    fitted = _fit_vol_model(returns_pct, "Garch", p, q, dist)
    print(fitted.summary())
    cond_vol = fitted.conditional_volatility / 100
    fc = fitted.forecast(horizon=steps_ahead, reindex=False)
    fc_vol = np.sqrt(fc.variance.values[-1]) / 100 * np.sqrt(periods_per_year)
    return {
        "model": fitted,
        "vol_type": f"GARCH({p},{q})",
        "conditional_vol": cond_vol,
        "conditional_vol_annual": cond_vol * np.sqrt(periods_per_year),
        "forecast_vol": fc_vol,
        "log_likelihood": fitted.loglikelihood,
        "aic": fitted.aic,
        "bic": fitted.bic,
        "diagnostics": garch_diagnostics({"model": fitted}),
    }


def fit_egarch(
    series: pd.Series,
    p: int = 1,
    q: int = 1,
    dist: str = "t",
    steps_ahead: int = 10,
    periods_per_year: int = 252,
) -> dict:
    """EGARCH(p,q) — cattura la leva (leverage effect)."""
    print(f"  Fitting EGARCH({p},{q}) dist='{dist}'...")
    returns_pct = series * 100
    fitted = _fit_vol_model(returns_pct, "EGARCH", p, q, dist)
    print(fitted.summary())
    cond_vol = fitted.conditional_volatility / 100
    fc = fitted.forecast(horizon=steps_ahead, reindex=False)
    fc_vol = np.sqrt(fc.variance.values[-1]) / 100 * np.sqrt(periods_per_year)
    return {
        "model": fitted,
        "vol_type": f"EGARCH({p},{q})",
        "conditional_vol": cond_vol,
        "conditional_vol_annual": cond_vol * np.sqrt(periods_per_year),
        "forecast_vol": fc_vol,
        "log_likelihood": fitted.loglikelihood,
        "aic": fitted.aic,
        "bic": fitted.bic,
        "diagnostics": garch_diagnostics({"model": fitted}),
    }


def fit_tarch(
    series: pd.Series,
    p: int = 1,
    q: int = 1,
    dist: str = "t",
    steps_ahead: int = 10,
    periods_per_year: int = 252,
) -> dict:
    """TARCH/GJR-GARCH — asimmetria degli shock negativi."""
    print(f"  Fitting TARCH({p},{q}) dist='{dist}'...")
    returns_pct = series * 100
    # arch_model con o=1 per GJR/TARCH
    gm = arch_model(returns_pct, vol="GARCH", p=p, o=1, q=q, dist=dist, rescale=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = gm.fit(disp="off", options={"maxiter": 500})
    print(fitted.summary())
    cond_vol = fitted.conditional_volatility / 100
    fc = fitted.forecast(horizon=steps_ahead, reindex=False)
    fc_vol = np.sqrt(fc.variance.values[-1]) / 100 * np.sqrt(periods_per_year)
    return {
        "model": fitted,
        "vol_type": f"TARCH({p},{q})",
        "conditional_vol": cond_vol,
        "conditional_vol_annual": cond_vol * np.sqrt(periods_per_year),
        "forecast_vol": fc_vol,
        "log_likelihood": fitted.loglikelihood,
        "aic": fitted.aic,
        "bic": fitted.bic,
        "diagnostics": garch_diagnostics({"model": fitted}),
    }


def compare_volatility_models(series: pd.Series, steps_ahead: int = 10, periods_per_year: int = 252) -> pd.DataFrame:
    """
    Fitta GARCH, EGARCH e TARCH e restituisce una tabella comparativa.
    Il modello migliore ha la log-likelihood più alta.
    """
    results = {}
    for name, fn in [("GARCH(1,1)", fit_garch), ("EGARCH(1,1)", fit_egarch), ("TARCH(1,1)", fit_tarch)]:
        try:
            r = fn(series, steps_ahead=steps_ahead, periods_per_year=periods_per_year)
            results[name] = {
                "log_lik": r["log_likelihood"],
                "aic": r["aic"],
                "bic": r["bic"],
                "vol_annualized_mean_%": float(r["conditional_vol_annual"].mean() * 100),
                "forecast_vol_mean_%": float(r["forecast_vol"].mean() * 100),
            }
        except Exception as exc:
            print(f"  [WARN] {name} fallito: {exc}")
    df = pd.DataFrame(results).T
    print("\n=== Confronto Modelli Volatilità ===")
    print(df.to_string())
    return df


def enrich_garch_diagnostics(result: dict) -> dict:
    """Aggiunge diagnostiche al dizionario risultato GARCH."""
    result = dict(result)
    result["diagnostics"] = garch_diagnostics(result)
    return result


def plot_garch_volatility(series: pd.Series, result: dict, ticker: str = "") -> None:
    cond_vol = result["conditional_vol_annual"]
    fc_vol = result["forecast_vol"]
    vol_type = result["vol_type"]
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    ax = axes[0]
    ax.plot(series.index, series.values, color="steelblue", alpha=0.5, linewidth=0.7, label="Log Returns")
    ax2 = ax.twinx()
    ax2.plot(cond_vol.index, cond_vol.values, color="firebrick", linewidth=1.2,
             label="Vol. condizionale (annualizzata)")
    ax2.set_ylabel("Volatilità annualizzata", color="firebrick")
    ax.set_title(f"{vol_type} — Volatilità Condizionale ({ticker})")
    ax.set_ylabel("Log Return")
    ax.legend(loc="upper left")
    ax2.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    ax3 = axes[1]
    horizons = np.arange(1, len(fc_vol) + 1)
    ax3.bar(horizons, fc_vol * 100, color="darkorange", alpha=0.8, edgecolor="black")
    ax3.set_title(f"Forecast Volatilità Annualizzata — prossimi {len(fc_vol)} giorni (%)")
    ax3.set_xlabel("Orizzonte (giorni)")
    ax3.set_ylabel("Volatilità annualizzata (%)")
    ax3.grid(True, alpha=0.3, axis="y")
    for i, v in enumerate(fc_vol * 100):
        ax3.text(horizons[i], v + 0.02, f"{v:.2f}%", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.show()
