"""
models/montecarlo.py — Simulazione Monte Carlo con GBM (Geometric Brownian Motion).

Calcola VaR e CVaR dalla distribuzione delle traiettorie simulate.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def simulate_gbm(
    S0: float,
    mu: float,
    sigma: float,
    T: int = 252,
    dt: float = 1 / 252,
    n_sims: int = 1000,
    seed: int | None = 42,
) -> np.ndarray:
    """
    Simula n_sims traiettorie di prezzo usando il Geometric Brownian Motion.

    dS = S * (mu*dt + sigma*sqrt(dt)*Z)   con Z ~ N(0,1)

    Parametri
    ---------
    S0     : prezzo iniziale
    mu     : drift annualizzato (rendimento medio atteso)
    sigma  : volatilità annualizzata
    T      : numero di passi (default 252 = 1 anno di trading)
    dt     : incremento temporale (default 1/252)
    n_sims : numero di simulazioni

    Returns
    -------
    ndarray di shape (T+1, n_sims) — prezzi simulati
    """
    rng = np.random.default_rng(seed)
    prices = np.zeros((T + 1, n_sims))
    prices[0] = S0
    Z = rng.standard_normal((T, n_sims))
    for t in range(1, T + 1):
        prices[t] = prices[t - 1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z[t - 1])
    return prices


def compute_var_cvar(
    simulated_prices: np.ndarray,
    S0: float,
    confidence: float = 0.95,
) -> dict:
    """
    Calcola VaR e CVaR dalla distribuzione terminale delle simulazioni.

    VaR   = perdita massima non superata con probabilità 'confidence'
    CVaR  = perdita media oltre il VaR (Expected Shortfall)
    """
    terminal_prices = simulated_prices[-1]
    returns = (terminal_prices - S0) / S0  # rendimenti sul periodo
    alpha = 1 - confidence
    var = float(np.percentile(returns, alpha * 100))
    cvar = float(returns[returns <= var].mean())
    return {
        "VaR": var,
        "CVaR": cvar,
        "confidence": confidence,
        "n_sims": simulated_prices.shape[1],
        "horizon_steps": simulated_prices.shape[0] - 1,
        "mean_terminal_return": float(returns.mean()),
        "std_terminal_return": float(returns.std()),
    }


def plot_gbm(
    simulated_prices: np.ndarray,
    ticker: str = "",
    confidence: float = 0.95,
    max_paths: int = 200,
) -> None:
    """Visualizza le traiettorie GBM con distribuzione terminale e VaR."""
    terminal = simulated_prices[-1]
    var = np.percentile(terminal, (1 - confidence) * 100)
    steps = np.arange(simulated_prices.shape[0])

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Pannello 1 — traiettorie
    ax = axes[0]
    n_show = min(max_paths, simulated_prices.shape[1])
    ax.plot(steps, simulated_prices[:, :n_show], alpha=0.15, linewidth=0.5, color="steelblue")
    ax.plot(steps, simulated_prices.mean(axis=1), color="firebrick", linewidth=2, label="Media")
    ax.set_title(f"GBM Monte Carlo — {ticker}\n({simulated_prices.shape[1]} simulazioni, T={len(steps)-1} giorni)")
    ax.set_xlabel("Giorni")
    ax.set_ylabel("Prezzo")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Pannello 2 — distribuzione terminale
    ax2 = axes[1]
    ax2.hist(terminal, bins=60, color="steelblue", alpha=0.7, edgecolor="white")
    ax2.axvline(var, color="firebrick", linewidth=2, linestyle="--",
                label=f"VaR {confidence*100:.0f}% = {var:.2f}")
    ax2.axvline(terminal.mean(), color="seagreen", linewidth=2,
                label=f"Media = {terminal.mean():.2f}")
    ax2.set_title("Distribuzione Prezzi Terminali")
    ax2.set_xlabel("Prezzo")
    ax2.set_ylabel("Frequenza")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
