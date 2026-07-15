"""analysis/correlogram.py — ACF e PACF."""

import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf


def plot_acf_pacf(series: pd.Series, lags: int = 40, title: str = "Serie") -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    plot_acf(series.dropna(), lags=lags, ax=axes[0], alpha=0.05)
    axes[0].set_title(f"ACF — {title}")
    axes[0].set_xlabel("Lag")
    plot_pacf(series.dropna(), lags=lags, ax=axes[1], alpha=0.05, method="ywm")
    axes[1].set_title(f"PACF — {title}")
    axes[1].set_xlabel("Lag")
    plt.suptitle("Correlogramma: p (PACF) e q (ACF)", y=1.02)
    plt.tight_layout()
    plt.show()
