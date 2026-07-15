"""analysis/rolling.py — Rolling statistics."""

import pandas as pd
import matplotlib.pyplot as plt


def plot_rolling_statistics(
    series: pd.Series, windows: list[int] = [20, 60], title: str = "Serie"
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    colors = ["red", "green", "orange"]
    axes[0].plot(series.index, series.values, color="steelblue", alpha=0.6, linewidth=0.8, label=title)
    for i, w in enumerate(windows):
        axes[0].plot(series.index, series.rolling(w).mean(), color=colors[i % len(colors)],
                     linewidth=1.5, label=f"MA({w})")
    axes[0].set_title(f"{title} — Medie Mobili")
    axes[0].set_ylabel("Valore")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    for i, w in enumerate(windows):
        axes[1].plot(series.index, series.rolling(w).std(), color=colors[i % len(colors)],
                     linewidth=1.2, label=f"Vol. realizzata ({w}g)")
    axes[1].set_title("Volatilità Realizzata (std. rolling)")
    axes[1].set_ylabel("Std Dev")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
