"""analysis/decomposition.py — Decomposizione stagionale."""

import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose


def decompose_series(series: pd.Series, period: int = 252, title: str = "Serie") -> None:
    if len(series.dropna()) < 2 * period:
        period = max(2, len(series) // 3)
        print(f"  [WARN] Serie corta, period ridotto a {period}.")

    decomp = seasonal_decompose(series.dropna(), model="additive", period=period,
                                extrapolate_trend="freq")
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    components = [
        (series, "Osservata", "steelblue"),
        (decomp.trend, "Trend", "firebrick"),
        (decomp.seasonal, "Stagionalità", "seagreen"),
        (decomp.resid, "Residuo", "darkorange"),
    ]
    for ax, (data, label, color) in zip(axes, components):
        ax.plot(data.index, data.values, color=color, linewidth=0.9)
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)
    axes[0].set_title(f"Decomposizione Stagionale — {title} (period={period})")
    plt.tight_layout()
    plt.show()
