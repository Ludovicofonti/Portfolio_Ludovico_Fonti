"""
models/var_model.py — Vector Autoregression multi-asset.

Analisi:
  - Granger causality (A causa B?)
  - Impulse Response Function (IRF)
  - Forecast Error Variance Decomposition (FEVD)
"""

import warnings
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.stattools import grangercausalitytests


def build_returns_matrix(
    symbols: list[str],
    db_path: str = "finance.duckdb",
) -> pd.DataFrame:
    """Carica i rendimenti di più asset da DuckDB e li allinea per data."""
    import duckdb
    con = duckdb.connect(db_path, read_only=True)
    placeholders = ", ".join("?" * len(symbols))
    df = con.execute(
        f"SELECT date, symbol, log_return FROM analytics.fct_asset_returns "
        f"WHERE symbol IN ({placeholders}) ORDER BY date",
        symbols,
    ).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot(index="date", columns="symbol", values="log_return").dropna()
    return wide


def fit_var(
    returns_wide: pd.DataFrame,
    maxlags: int = 10,
    steps_ahead: int = 10,
) -> dict:
    """
    Fitta VAR con selezione automatica del lag tramite AIC.
    returns_wide: DataFrame con colonne = simboli, index = date.
    """
    print(f"  Fitting VAR (maxlags={maxlags})...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = VAR(returns_wide)
        result = model.fit(maxlags=maxlags, ic="aic")
    print(result.summary())
    lag = result.k_ar
    print(f"  Lag selezionato: {lag}")
    fc_input = returns_wide.values[-lag:]
    fc = result.forecast(fc_input, steps=steps_ahead)
    fc_df = pd.DataFrame(fc, columns=returns_wide.columns)
    return {
        "model": result,
        "lag": lag,
        "forecast": fc_df,
        "aic": result.aic,
    }


def granger_causality_matrix(
    returns_wide: pd.DataFrame, maxlag: int = 5
) -> pd.DataFrame:
    """
    Testa la causalità di Granger per ogni coppia (A → B).
    Restituisce una matrice di p-value (F-test al lag ottimale).
    """
    symbols = returns_wide.columns.tolist()
    matrix = pd.DataFrame(index=symbols, columns=symbols, dtype=float)
    for caused in symbols:
        for cause in symbols:
            if cause == caused:
                matrix.loc[caused, cause] = float("nan")
                continue
            data = returns_wide[[caused, cause]].dropna()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                test = grangercausalitytests(data, maxlag=maxlag, verbose=False)
            # Prende il p-value del test F al primo lag
            pval = test[1][0]["ssr_ftest"][1]
            matrix.loc[caused, cause] = round(pval, 4)
    print("\n=== Granger Causality (p-value, soglia 0.05) ===")
    print(f"  Riga = causato, Colonna = causa")
    print(matrix.to_string())
    return matrix


def plot_irf(result: dict, periods: int = 20, orth: bool = True) -> None:
    """Plotta le Impulse Response Function."""
    irf = result["model"].irf(periods)
    irf.plot(orth=orth)
    plt.suptitle("Impulse Response Function (IRF)", y=1.01)
    plt.tight_layout()
    plt.show()


def plot_fevd(result: dict, periods: int = 20) -> None:
    """Plotta la Forecast Error Variance Decomposition."""
    fevd = result["model"].fevd(periods)
    fevd.plot()
    plt.suptitle("Forecast Error Variance Decomposition (FEVD)", y=1.01)
    plt.tight_layout()
    plt.show()
