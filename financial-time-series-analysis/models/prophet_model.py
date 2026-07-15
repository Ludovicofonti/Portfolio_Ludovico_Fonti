"""
models/prophet_model.py — Wrapper Prophet con cross-validation integrata.
"""

import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from prophet.plot import plot_cross_validation_metric


def fit_prophet(
    series: pd.Series,
    steps_ahead: int = 20,
    yearly_seasonality: bool = True,
    weekly_seasonality: bool = True,
    changepoint_prior_scale: float = 0.05,
) -> dict:
    """
    Adatta un modello Prophet alla serie di prezzi (non ai rendimenti).
    Prophet richiede un DataFrame con colonne 'ds' (date) e 'y' (valore).
    """
    print("  Fitting Prophet...")
    df_prophet = pd.DataFrame({"ds": series.index, "y": series.values}).reset_index(drop=True)
    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        changepoint_prior_scale=changepoint_prior_scale,
        interval_width=0.95,
    )
    model.fit(df_prophet)
    future = model.make_future_dataframe(periods=steps_ahead, freq="B")  # B = business days
    forecast = model.predict(future)
    return {
        "model": model,
        "forecast": forecast,
        "df_train": df_prophet,
    }


def prophet_cross_validate(
    result: dict,
    initial: str = "730 days",
    period: str = "90 days",
    horizon: str = "30 days",
) -> pd.DataFrame:
    """
    Cross-validation walk-forward Prophet.
    initial: dimensione del training set iniziale
    period: intervallo tra cutoff
    horizon: lunghezza del test set
    """
    print(f"  Prophet cross-validation (initial={initial}, period={period}, horizon={horizon})...")
    df_cv = cross_validation(
        result["model"], initial=initial, period=period, horizon=horizon, parallel="processes"
    )
    metrics = performance_metrics(df_cv)
    print("\n  Metriche cross-validation Prophet:")
    print(metrics[["horizon", "mae", "mape", "rmse"]].to_string(index=False))
    return metrics


def plot_prophet(result: dict, ticker: str = "") -> None:
    model, forecast = result["model"], result["forecast"]
    fig = model.plot(forecast)
    plt.title(f"Prophet Forecast — {ticker}")
    plt.tight_layout()
    plt.show()
    fig2 = model.plot_components(forecast)
    plt.suptitle(f"Prophet Components — {ticker}", y=1.01)
    plt.tight_layout()
    plt.show()
