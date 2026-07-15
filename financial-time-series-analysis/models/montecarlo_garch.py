"""
models/montecarlo_garch.py — Monte Carlo con volatilità dinamica GARCH.

A differenza del GBM classico (sigma costante), la volatilità cambia
ogni giorno secondo il processo GARCH stimato sui dati storici.
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from arch import arch_model

from models.montecarlo import compute_var_cvar


def simulate_garch_mc(
    series: pd.Series,
    S0: float,
    T: int = 252,
    n_sims: int = 1000,
    p: int = 1,
    q: int = 1,
    dist: str = "t",
    seed: int | None = 42,
) -> np.ndarray:
    """
    Simula n_sims traiettorie di PREZZO usando la volatilità dinamica GARCH.

    1. Stima GARCH sui rendimenti storici → parametri omega, alpha, beta
    2. Per ogni sim e ogni passo t:
       sigma²_t = omega + alpha * eps²_{t-1} + beta * sigma²_{t-1}
       r_t ~ N(0, sigma_t)
       S_t = S_{t-1} * exp(r_t)

    Returns ndarray (T+1, n_sims)
    """
    returns_pct = series * 100
    gm = arch_model(returns_pct, vol="Garch", p=p, q=q, dist=dist, rescale=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = gm.fit(disp="off", options={"maxiter": 500})

    params = fitted.params
    omega = params.get("omega", 0.01)
    alpha = params.get("alpha[1]", 0.05)
    beta  = params.get("beta[1]", 0.90)
    # Varianza iniziale = varianza condizionale all'ultimo osservato
    sigma2_init = float(fitted.conditional_volatility.iloc[-1] ** 2)

    rng = np.random.default_rng(seed)
    prices = np.zeros((T + 1, n_sims))
    prices[0] = S0
    sigma2 = np.full(n_sims, sigma2_init)

    for t in range(1, T + 1):
        z = rng.standard_normal(n_sims)
        eps = np.sqrt(sigma2) * z              # in % scale
        r_pct = eps                            # rendimenti simulati (%)
        r = r_pct / 100                        # riporta a scala originale
        prices[t] = prices[t - 1] * np.exp(r)
        sigma2 = omega + alpha * eps**2 + beta * sigma2

    return prices


def compare_mc_vs_garch_mc(
    series: pd.Series,
    S0: float,
    T: int = 252,
    n_sims: int = 1000,
    confidence: float = 0.95,
) -> None:
    """
    Confronta VaR/CVaR tra GBM classico e MC-GARCH.
    """
    from models.montecarlo import simulate_gbm

    mu = float(series.mean() * 252)
    sigma = float(series.std() * np.sqrt(252))

    print(f"  GBM params: mu={mu:.4f}, sigma={sigma:.4f}")
    paths_gbm = simulate_gbm(S0, mu, sigma, T=T, n_sims=n_sims)
    paths_garch = simulate_garch_mc(series, S0, T=T, n_sims=n_sims)

    gbm_stats   = compute_var_cvar(paths_gbm,   S0, confidence)
    garch_stats = compute_var_cvar(paths_garch, S0, confidence)

    print(f"\n{'='*50}")
    print(f"  Confronto VaR/CVaR a {confidence*100:.0f}% — orizzonte {T} giorni")
    print(f"{'='*50}")
    print(f"  {'Metrica':<20} {'GBM':>10} {'GARCH-MC':>10}")
    print(f"  {'-'*40}")
    for key in ["VaR", "CVaR", "mean_terminal_return", "std_terminal_return"]:
        print(f"  {key:<20} {gbm_stats[key]:>10.4f} {garch_stats[key]:>10.4f}")
    print(f"{'='*50}")

    # Plot comparativo
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for ax, paths, label, color in [
        (axes[0], paths_gbm,   "GBM (σ costante)",      "steelblue"),
        (axes[1], paths_garch, "MC-GARCH (σ dinamica)", "darkorange"),
    ]:
        terminal = paths[-1]
        var = np.percentile(terminal, (1 - confidence) * 100)
        ax.hist(terminal, bins=60, color=color, alpha=0.7, edgecolor="white")
        ax.axvline(var, color="firebrick", linewidth=2, linestyle="--",
                   label=f"VaR {confidence*100:.0f}% = {var:.2f}")
        ax.axvline(terminal.mean(), color="seagreen", linewidth=2,
                   label=f"Media = {terminal.mean():.2f}")
        ax.set_title(f"Dist. terminale — {label}")
        ax.set_xlabel("Prezzo")
        ax.legend()
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
