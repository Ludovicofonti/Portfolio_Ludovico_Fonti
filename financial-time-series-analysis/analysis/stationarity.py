"""analysis/stationarity.py — Test ADF e KPSS."""

import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss


def test_adf(series: pd.Series, alpha: float = 0.05) -> dict:
    result = adfuller(series.dropna(), autolag="AIC")
    return {
        "test": "ADF",
        "statistic": result[0],
        "p_value": result[1],
        "lags_used": result[2],
        "critical_values": result[4],
        "is_stationary": result[1] < alpha,
    }


def test_kpss(series: pd.Series, alpha: float = 0.05) -> dict:
    stat, p_value, lags, crit = kpss(series.dropna(), regression="c", nlags="auto")
    return {
        "test": "KPSS",
        "statistic": stat,
        "p_value": p_value,
        "lags_used": lags,
        "critical_values": crit,
        "is_stationary": p_value >= alpha,
    }


def run_stationarity_tests(series: pd.Series, label: str = "Serie") -> None:
    print(f"\n{'='*60}")
    print(f"  TEST DI STAZIONARIETÀ — {label}")
    print(f"{'='*60}")

    adf = test_adf(series)
    print(f"\n[ADF]  Statistica: {adf['statistic']:.4f}  |  p-value: {adf['p_value']:.4f}")
    for k, v in adf["critical_values"].items():
        print(f"       Valore critico ({k}): {v:.4f}")
    print(f"       Conclusione: {'STAZIONARIA ✔' if adf['is_stationary'] else 'NON STAZIONARIA ✘'}")

    kpss_res = test_kpss(series)
    print(f"\n[KPSS] Statistica: {kpss_res['statistic']:.4f}  |  p-value: {kpss_res['p_value']:.4f}")
    for k, v in kpss_res["critical_values"].items():
        print(f"       Valore critico ({k}): {v:.4f}")
    print(f"       Conclusione: {'STAZIONARIA ✔' if kpss_res['is_stationary'] else 'NON STAZIONARIA ✘'}")

    print("\n  Interpretazione combinata:")
    if adf["is_stationary"] and kpss_res["is_stationary"]:
        print("  → Entrambi concordano: STAZIONARIA.")
    elif not adf["is_stationary"] and not kpss_res["is_stationary"]:
        print("  → Entrambi concordano: NON STAZIONARIA (radice unitaria).")
    elif adf["is_stationary"] and not kpss_res["is_stationary"]:
        print("  → AMBIGUO (trend-stazionaria, non livello-stazionaria).")
    else:
        print("  → AMBIGUO.")
    print(f"{'='*60}\n")
