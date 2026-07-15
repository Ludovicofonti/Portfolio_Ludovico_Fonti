"""
legacy/report_business.py — Generatore storico di report business-oriented.

Trasforma i risultati quantitativi della pipeline in insight azionabili:
segnali condizionati, profilo di rischio e scenari con comunicazione prudente.

Output: reports/REPORT_BUSINESS_{ticker}_{date}.md
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(v: Any, decimals: int = 1, sign: bool = False) -> str:
    if v is None:
        return "N/D"
    try:
        f = float(v)
        prefix = "+" if sign and f > 0 else ""
        return f"{prefix}{f:.{decimals}f}%"
    except (TypeError, ValueError):
        return str(v)


def _currency(v: Any, symbol: str = "$", decimals: int = 0) -> str:
    if v is None:
        return "N/D"
    try:
        return f"{symbol}{float(v):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt(v: Any, decimals: int = 2) -> str:
    if v is None:
        return "N/D"
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return str(v)


# ---------------------------------------------------------------------------
# Semafori e segnali
# ---------------------------------------------------------------------------

def _traffic_light(value: float, low: float, high: float,
                   invert: bool = False) -> str:
    """
    Restituisce 🟢 / 🟡 / 🔴 in base alle soglie.
    Se invert=True, valori alti sono negativi (es. volatilità, VaR).
    """
    if invert:
        if value <= low:
            return "🟢"
        if value <= high:
            return "🟡"
        return "🔴"
    else:
        if value >= high:
            return "🟢"
        if value >= low:
            return "🟡"
        return "🔴"


def _vol_regime(sigma_annual: float) -> tuple[str, str, str]:
    """Classifica il regime di volatilità e restituisce (etichetta, colore, descrizione)."""
    pct = sigma_annual * 100
    if pct < 20:
        return "BASSA", "🟢", f"{_pct(pct)} — tipica di asset difensivi (es. obbligazioni, utility)"
    if pct < 50:
        return "MEDIA", "🟡", f"{_pct(pct)} — tipica di azioni growth o commodity"
    if pct < 100:
        return "ALTA", "🔴", f"{_pct(pct)} — tipica di asset ad alto rischio (es. crypto)"
    return "MOLTO ALTA", "🔴🔴", f"{_pct(pct)} — regime di stress estremo"


def _sharpe_label(sharpe: float | None) -> tuple[str, str]:
    if sharpe is None:
        return "N/D", ""
    if sharpe > 2.0:
        return "Eccellente", "🟢"
    if sharpe > 1.0:
        return "Buono", "🟢"
    if sharpe > 0.5:
        return "Accettabile", "🟡"
    if sharpe > 0.0:
        return "Debole", "🟡"
    return "Negativo", "🔴"


def _trend_signal(mu_annual: float, sigma_annual: float,
                  arima_fc_mean: float | None) -> tuple[str, str, str]:
    """
    Segnale di tendenza basato su drift storico + direzione ARIMA.
    Restituisce (label, emoji, descrizione).
    """
    drift_positive = mu_annual > 0
    fc_positive = arima_fc_mean is not None and arima_fc_mean > 0
    signal_ratio = mu_annual / sigma_annual if sigma_annual > 0 else 0

    if drift_positive and fc_positive:
        if signal_ratio > 0.3:
            return "RIALZISTA", "📈", "Drift storico positivo e modello ARIMA in accordo — momentum favorevole"
        return "LIEVEMENTE RIALZISTA", "📈", "Tendenza positiva ma con rapporto rendimento/rischio contenuto"
    if not drift_positive and not fc_positive:
        return "RIBASSISTA", "📉", "Drift storico negativo e modello ARIMA in accordo — pressione al ribasso"
    return "NEUTRO / INCERTO", "➡️", "Segnali contrastanti tra drift storico e previsione modello"


def _mc_scenario_summary(paths_final: np.ndarray | None, S0: float,
                          confidence: float) -> dict:
    """Calcola scenari percentili dalla distribuzione MC terminale."""
    if paths_final is None or len(paths_final) == 0:
        return {}
    returns_mc = (paths_final - S0) / S0
    alpha = 1 - confidence
    return {
        "p5":    float(np.percentile(returns_mc, 5)),
        "p25":   float(np.percentile(returns_mc, 25)),
        "p50":   float(np.percentile(returns_mc, 50)),
        "p75":   float(np.percentile(returns_mc, 75)),
        "p95":   float(np.percentile(returns_mc, 95)),
        "prob_positive": float(np.mean(returns_mc > 0)),
        "prob_loss_20": float(np.mean(returns_mc < -0.20)),
        "prob_gain_50": float(np.mean(returns_mc > 0.50)),
    }


# ---------------------------------------------------------------------------
# Costruzione sezioni
# ---------------------------------------------------------------------------

def _header(ctx: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ticker = ctx["ticker"]
    sigma_annual = ctx.get("sigma_annual", 0)
    vol_label, vol_icon, _ = _vol_regime(sigma_annual)
    mu_annual = ctx.get("mu_annual", 0)
    arima_fc = ctx.get("arima_fc_mean")
    trend_label, trend_icon, _ = _trend_signal(mu_annual, sigma_annual, arima_fc)

    return f"""# Analisi di Mercato — {ticker}
### Report Business Intelligence

> **Data analisi:** {now}
> **Asset analizzato:** `{ticker}`
> **Periodo storico:** {ctx.get('start_date')} → {ctx.get('end_date')} ({ctx.get('n_obs', 'N/D')} sedute)
> **Prezzo di riferimento:** {_currency(ctx.get('S0'), decimals=2)}

---

> **Sintesi rapida:**
> Tendenza: {trend_icon} **{trend_label}** &nbsp;|&nbsp; Volatilità: {vol_icon} **{vol_label}** &nbsp;|&nbsp; Orizzonte analisi: **{ctx.get('mc_horizon', 252)} giorni**

---
"""


def _scorecard(ctx: dict) -> str:
    mu = ctx.get("mu_annual", 0)
    sigma = ctx.get("sigma_annual", 0)
    vol_label, vol_icon, _ = _vol_regime(sigma)
    sharpe_raw = None
    rm = ctx.get("risk_metrics")
    if rm:
        sharpe_raw = rm.get("sharpe_ratio")
    if sharpe_raw is None and sigma > 0:
        sharpe_raw = mu / sigma

    sharpe_label, sharpe_icon = _sharpe_label(sharpe_raw)
    arima_fc = ctx.get("arima_fc_mean")
    trend_label, trend_icon, _ = _trend_signal(mu, sigma, arima_fc)

    mc = ctx.get("mc_gbm", {})
    var_pct = abs(mc.get("VaR", 0)) * 100
    cvar_pct = abs(mc.get("CVaR", 0)) * 100

    var_icon = _traffic_light(var_pct, 20, 40, invert=True)
    cvar_icon = _traffic_light(cvar_pct, 30, 60, invert=True)
    ret_icon = _traffic_light(mu * 100, 5, 20)
    sharpe_icon_tl = _traffic_light(sharpe_raw or 0, 0.5, 1.0)

    fc_garch = ctx.get("garch_forecast_vol_pct")
    fc_garch_vs_hist = ""
    if fc_garch and sigma > 0:
        diff = fc_garch - sigma * 100
        fc_garch_vs_hist = f"({'+' if diff > 0 else ''}{diff:.1f}% vs storico)"

    return f"""## Scorecard Esecutiva

| KPI | Valore | Valutazione |
|---|---|---|
| Rendimento storico annuo | {_pct(mu * 100, sign=True)} | {ret_icon} |
| Volatilità annualizzata | {_pct(sigma * 100)} | {vol_icon} **{vol_label}** |
| Volatilità GARCH (forecast) | {_pct(fc_garch) if fc_garch else 'N/D'} {fc_garch_vs_hist} | |
| Sharpe Ratio | {_fmt(sharpe_raw)} | {sharpe_icon_tl} {sharpe_label} |
| Tendenza (modello) | {trend_label} | {trend_icon} |
| VaR 95% — {ctx.get('mc_horizon', 252)} giorni | {_pct(var_pct)} | {var_icon} |
| CVaR 95% — {ctx.get('mc_horizon', 252)} giorni | {_pct(cvar_pct)} | {cvar_icon} |

---
"""


def _performance(ctx: dict) -> str:
    mu = ctx.get("mu_annual", 0)
    sigma = ctx.get("sigma_annual", 0)
    S0 = ctx.get("S0", 0)
    skew = ctx.get("skewness", 0)
    kurt = ctx.get("kurtosis", 0)
    horizon = ctx.get("mc_horizon", 252)
    days_label = f"{horizon} giorni ({horizon // 21} mesi ca.)"

    # Rendimento storico su vari orizzonti (da drift giornaliero)
    mu_daily = ctx.get("mean_return_daily", mu / 252)
    ret_1m = (1 + mu_daily) ** 21 - 1
    ret_3m = (1 + mu_daily) ** 63 - 1
    ret_1y = (1 + mu_daily) ** 252 - 1

    # Prezzo atteso in 1 anno (mediana log-normale)
    import math
    sigma_d = ctx.get("std_return_daily", sigma / 16)
    price_median_1y = S0 * math.exp(mu_daily * 252 - 0.5 * sigma_d**2 * 252)
    # ±1 deviazione standard annualizzata attorno alla mediana
    price_bull_1y = price_median_1y * math.exp(sigma)
    price_bear_1y = price_median_1y * math.exp(-sigma)

    skew_note = (
        "⚠️ **Asimmetria negativa** (skewness < −0.5): la distribuzione dei rendimenti tende verso "
        "perdite improvvise e ampie. Il rischio di coda sinistra è superiore a quanto suggerito dalla sola volatilità."
        if skew < -0.5
        else "⚠️ **Asimmetria positiva** (skewness > 0.5): rari guadagni molto elevati spostano la media verso l'alto — "
        "la performance mediana è tipicamente inferiore alla media aritmetica."
        if skew > 0.5
        else "La distribuzione dei rendimenti è approssimativamente simmetrica."
    )

    kurt_note = (
        "⚠️ **Code spesse** (curtosi > 3): eventi estremi — sia rialzi che ribassi bruschi — "
        "sono significativamente più frequenti di quanto previsto dalla distribuzione normale. "
        "Questo è il comportamento tipico di azioni, crypto e commodity."
        if kurt > 1
        else "La distribuzione dei rendimenti è vicina alla normalità per le code."
    )

    return f"""## 1. Performance Storica e Tendenza

### Rendimenti stimati (da media storica)

| Orizzonte | Rendimento atteso | Prezzo stimato |
|---|---|---|
| 1 mese (21 gg) | {_pct(ret_1m * 100, sign=True)} | {_currency(S0 * (1 + ret_1m), decimals=2)} |
| 3 mesi (63 gg) | {_pct(ret_3m * 100, sign=True)} | {_currency(S0 * (1 + ret_3m), decimals=2)} |
| 12 mesi (252 gg) | {_pct(ret_1y * 100, sign=True)} | {_currency(S0 * (1 + ret_1y), decimals=2)} |

> ⚠️ I rendimenti attesi sono stime basate sulla media storica — non previsioni garantite.
> La volatilità elevata implica un ampio ventaglio di esiti possibili (vedi scenari Monte Carlo).

### Prezzo target a 12 mesi (scenari deterministici)

| Scenario | Ipotesi | Prezzo target |
|---|---|---|
| 🐂 Ottimistico (drift + 1σ) | Mercato favorevole | {_currency(price_bull_1y, decimals=2)} |
| ➡️ Base (mediana log-normale) | Andamento in linea col passato | {_currency(price_median_1y, decimals=2)} |
| 🐻 Pessimistico (drift − 1σ) | Correzione di mercato | {_currency(price_bear_1y, decimals=2)} |

### Caratteristiche della distribuzione dei rendimenti

{skew_note}

{kurt_note}

---
"""


def _risk_profile(ctx: dict) -> str:
    sigma = ctx.get("sigma_annual", 0)
    mu = ctx.get("mu_annual", 0)
    S0 = ctx.get("S0", 0)
    confidence = ctx.get("mc_confidence", 0.95)
    horizon = ctx.get("mc_horizon", 252)
    conf_label = f"{confidence*100:.0f}%"

    vol_label, vol_icon, vol_desc = _vol_regime(sigma)

    mc = ctx.get("mc_gbm", {})
    var_pct = mc.get("VaR", 0)
    cvar_pct = mc.get("CVaR", 0)
    var_dollar = S0 * abs(var_pct)
    cvar_dollar = S0 * abs(cvar_pct)

    mc_g = ctx.get("mc_garch", {})
    var_g = mc_g.get("VaR") if mc_g else None
    cvar_g = mc_g.get("CVaR") if mc_g else None

    rm = ctx.get("risk_metrics")
    var_daily_pct = rm.get("var_95_daily_pct") if rm else None
    cvar_daily_pct = rm.get("cvar_95_daily_pct") if rm else None

    garch_fc_pct = ctx.get("garch_forecast_vol_pct")
    vol_trend = ""
    if garch_fc_pct:
        hist_pct = sigma * 100
        if garch_fc_pct > hist_pct * 1.1:
            vol_trend = f"🔺 **In aumento**: la volatilità attesa ({_pct(garch_fc_pct)}) supera la media storica ({_pct(hist_pct)}) — il mercato sta prezzando maggiore incertezza."
        elif garch_fc_pct < hist_pct * 0.9:
            vol_trend = f"🔻 **In calo**: la volatilità attesa ({_pct(garch_fc_pct)}) è inferiore alla media storica ({_pct(hist_pct)}) — il mercato si sta stabilizzando."
        else:
            vol_trend = f"➡️ **Stabile**: la volatilità attesa ({_pct(garch_fc_pct)}) è in linea con la media storica ({_pct(hist_pct)})."

    return f"""## 2. Profilo di Rischio

### Regime di Volatilità

{vol_icon} **{vol_label}** — {vol_desc}

{vol_trend}

### VaR e CVaR — Perdite Massime Attese

Il **VaR** (Value at Risk) misura la perdita massima che **non** viene superata nel {conf_label} degli scenari.
Il **CVaR** (Expected Shortfall) misura invece la perdita media **nei scenari peggiori** oltre il VaR.

#### Orizzonte {horizon} giorni (~{horizon // 21} mesi) — Simulazione Monte Carlo

| Misura | GBM classico | GARCH (vol. dinamica) |
|---|---|---|
| VaR {conf_label} | {_pct(abs(var_pct)*100)} | {_pct(abs(var_g)*100) if var_g else 'N/D'} |
| CVaR {conf_label} | {_pct(abs(cvar_pct)*100)} | {_pct(abs(cvar_g)*100) if cvar_g else 'N/D'} |
| Perdita VaR su posizione da $10.000 | {_currency(10000 * abs(var_pct), decimals=0)} | {_currency(10000 * abs(var_g), decimals=0) if var_g else 'N/D'} |
| Perdita CVaR su posizione da $10.000 | {_currency(10000 * abs(cvar_pct), decimals=0)} | {_currency(10000 * abs(cvar_g), decimals=0) if cvar_g else 'N/D'} |

> Il modello GARCH cattura la volatilità dinamica ("volatility clustering"): nei periodi di crisi
> la volatilità si impenna rapidamente. Il VaR GARCH è tipicamente **più conservativo e realistico**
> rispetto al GBM.

#### VaR giornaliero storico (da dati reali)

| Misura | 1 giorno |
|---|---|
| VaR storico 95% | {_pct(var_daily_pct) if var_daily_pct is not None else 'N/D'} |
| CVaR storico 95% | {_pct(cvar_daily_pct) if cvar_daily_pct is not None else 'N/D'} |
| Perdita VaR su $10.000 | {_currency(10000 * abs(var_daily_pct / 100), decimals=0) if var_daily_pct is not None else 'N/D'} |

> Il VaR giornaliero storico è calcolato sul 5° percentile dei rendimenti effettivamente osservati
> — non assume alcuna distribuzione teorica.

---
"""


def _monte_carlo_scenarios(ctx: dict) -> str:
    S0 = ctx.get("S0", 0)
    confidence = ctx.get("mc_confidence", 0.95)
    horizon = ctx.get("mc_horizon", 252)
    n_sims = ctx.get("mc_sims", 1000)
    conf_label = f"{confidence*100:.0f}%"

    sc = ctx.get("mc_scenarios", {})
    if not sc:
        return f"""## 3. Scenari Monte Carlo ({n_sims} simulazioni)

*Dati di scenario non disponibili.*

---
"""

    p5   = sc.get("p5", 0)
    p25  = sc.get("p25", 0)
    p50  = sc.get("p50", 0)
    p75  = sc.get("p75", 0)
    p95  = sc.get("p95", 0)
    prob_pos  = sc.get("prob_positive", 0)
    prob_loss = sc.get("prob_loss_20", 0)
    prob_gain = sc.get("prob_gain_50", 0)

    def _price(r): return _currency(S0 * (1 + r), decimals=2)
    def _r(r): return _pct(r * 100, sign=True)

    upside = S0 * (1 + p95) - S0
    downside = S0 - S0 * (1 + p5)
    risk_reward = abs(upside / downside) if downside != 0 else None
    rr_label = f"**{risk_reward:.2f}x**" if risk_reward else "N/D"
    rr_note = (
        f"Per ogni euro potenzialmente perso nel worst-case, c'è la possibilità di guadagnarne {risk_reward:.2f} nel best-case."
        if risk_reward else ""
    )

    return f"""## 3. Scenari Monte Carlo ({n_sims} simulazioni — {horizon} giorni)

La simulazione Monte Carlo modella **{n_sims} possibili traiettorie** di prezzo future
basandosi sui parametri storici (drift e volatilità).

### Distribuzione dei risultati a {horizon} giorni

| Scenario | Percentile | Rendimento | Prezzo finale |
|---|---|---|---|
| 🔴 Estremo negativo | 5° | {_r(p5)} | {_price(p5)} |
| 🟡 Conservativo | 25° | {_r(p25)} | {_price(p25)} |
| ➡️ Mediano | 50° | {_r(p50)} | {_price(p50)} |
| 🟢 Ottimistico | 75° | {_r(p75)} | {_price(p75)} |
| 🟢 Estremo positivo | 95° | {_r(p95)} | {_price(p95)} |

### Probabilità implicite

| Evento | Probabilità stimata |
|---|---|
| Rendimento positivo a {horizon} giorni | **{_pct(prob_pos * 100, decimals=0)}** |
| Perdita superiore al 20% | **{_pct(prob_loss * 100, decimals=1)}** |
| Guadagno superiore al 50% | **{_pct(prob_gain * 100, decimals=1)}** |

### Rapporto rischio/opportunità

Potenziale upside (P95 vs prezzo attuale): **{_currency(upside, decimals=0)}**
Potenziale downside (P5 vs prezzo attuale): **{_currency(downside, decimals=0)}**
Risk/Reward ratio: {rr_label}

{rr_note}

> ⚠️ Le probabilità stimate assumono che il comportamento futuro ricalchi quello passato.
> Eventi strutturali (cambi regolativi, shock macro, crisi di liquidità) non sono catturati dal modello.

---
"""


def _model_signals(ctx: dict) -> str:
    mu = ctx.get("mu_annual", 0)
    sigma = ctx.get("sigma_annual", 0)
    arima_fc = ctx.get("arima_fc_mean")
    sarima_fc = ctx.get("sarima_fc_mean")
    trend_label, trend_icon, trend_desc = _trend_signal(mu, sigma, arima_fc)

    bt_a = ctx.get("backtest_arima", {})
    bt_s = ctx.get("backtest_sarima", {})
    direction_tests = ctx.get("direction_tests", {})
    da_a = bt_a.get("Direction_Accuracy_%")
    da_s = bt_s.get("Direction_Accuracy_%")
    best_da = max(da_a or 0, da_s or 0)
    best_model = "ARIMA" if (da_a or 0) >= (da_s or 0) else "SARIMA"

    da_icon = _traffic_light(best_da, 52, 60)

    arima_dir = ""
    if arima_fc is not None:
        arima_dir = "📈 **positivo**" if arima_fc > 0 else "📉 **negativo**"

    sarima_dir = ""
    if sarima_fc is not None:
        sarima_dir = "📈 **positivo**" if sarima_fc > 0 else "📉 **negativo**"

    garch_fc = ctx.get("garch_forecast_vol_pct")
    garch_hist = sigma * 100
    vol_signal = ""
    if garch_fc:
        if garch_fc > garch_hist * 1.15:
            vol_signal = "🔺 Volatilità in **aumento** — il modello anticipa turbolenza nei prossimi giorni"
        elif garch_fc < garch_hist * 0.85:
            vol_signal = "🔻 Volatilità in **calo** — il modello prevede un periodo di stabilità relativa"
        else:
            vol_signal = "➡️ Volatilità **stabile** — nessuna variazione significativa attesa"

    best_test = direction_tests.get(best_model, {})
    p_value = best_test.get("p_value")
    significant = best_test.get("significant", False)
    p_text = f" p-value binomiale = {p_value:.4f}." if p_value is not None else ""
    reliability_note = (
        f"Il modello {best_model} indovina la **direzione** del mercato nel **{_pct(best_da)}** dei giorni testati."
        f" {da_icon}{p_text} "
        + (
            "Il vantaggio direzionale risulta statisticamente significativo, ma va comunque verificato con costi di transazione e P&L."
            if significant
            else "Il vantaggio direzionale non è dimostrato statisticamente: le previsioni vanno usate come indicazione debole, non come segnale operativo autonomo."
        )
    )

    return f"""## 4. Segnali dai Modelli Quantitativi

> I segnali sono derivati dai modelli statistici (ARIMA, SARIMA, GARCH) e devono essere
> integrati con analisi fondamentale e contesto macroeconomico.

### Segnale di Tendenza

{trend_icon} **{trend_label}**
{trend_desc}

| Modello | Direzione forecast | Rendimento medio atteso (prossimi {ctx.get('forecast_steps', 20)} gg) |
|---|---|---|
| ARIMA | {arima_dir if arima_dir else 'N/D'} | {_pct((arima_fc or 0) * 100, decimals=4, sign=True)} per giorno |
| SARIMA | {sarima_dir if sarima_dir else 'N/D'} | {_pct((sarima_fc or 0) * 100, decimals=4, sign=True)} per giorno |

> I modelli ARIMA/SARIMA prevedono i **rendimenti** (variazioni percentuali), non i livelli di prezzo.
> Previsioni puntuali di rendimento per orizzonti > 5 giorni hanno tipicamente bassa affidabilità
> su asset ad alta volatilità — l'intervallo di confidenza si allarga rapidamente.

### Segnale di Volatilità (GARCH)

{vol_signal if vol_signal else 'Dati GARCH non disponibili.'}

| | Valore |
|---|---|
| Volatilità storica annualizzata | {_pct(garch_hist)} |
| Volatilità GARCH forecast | {_pct(garch_fc) if garch_fc else 'N/D'} |

### Affidabilità del Modello (Backtesting)

{reliability_note}

| Metrica | ARIMA | SARIMA |
|---|---|---|
| Direction Accuracy | {_pct(da_a)} | {_pct(da_s)} |
| MAE (errore medio) | {_fmt(bt_a.get('MAE'), 4) if bt_a.get('MAE') else 'N/D'} | {_fmt(bt_s.get('MAE'), 4) if bt_s.get('MAE') else 'N/D'} |
| p-value direzionale | {_fmt(direction_tests.get('ARIMA', {}).get('p_value'), 4)} | {_fmt(direction_tests.get('SARIMA', {}).get('p_value'), 4)} |

---
"""


def _risk_adjusted_performance(ctx: dict) -> str:
    mu = ctx.get("mu_annual", 0)
    sigma = ctx.get("sigma_annual", 0)

    rm = ctx.get("risk_metrics")
    sharpe_raw = rm.get("sharpe_ratio") if rm else None
    if sharpe_raw is None and sigma > 0:
        sharpe_raw = mu / sigma

    sharpe_label, sharpe_icon = _sharpe_label(sharpe_raw)
    vol_label, _, _ = _vol_regime(sigma)

    # Calman ratio proxy (rendimento / max drawdown): non abbiamo max drawdown diretto
    # Mostriamo confronto rendimento vs benchmark rough
    calmar_note = ""

    # Benchmark informale
    sp500_typical_sharpe = 0.5
    sharpe_diff = (sharpe_raw or 0) - sp500_typical_sharpe
    benchmark_note = (
        f"Il Sharpe ratio di {_fmt(sharpe_raw)} è **{abs(sharpe_diff):.2f} punti "
        f"{'sopra' if sharpe_diff > 0 else 'sotto'}** il benchmark tipico dell'S&P 500 (~0.5)."
        if sharpe_raw is not None
        else ""
    )

    # Return/risk table
    return_on_risk = mu / sigma if sigma > 0 else None

    return f"""## 5. Performance Aggiustata per il Rischio

### Sharpe Ratio

{sharpe_icon} **{sharpe_label}** — Sharpe = {_fmt(sharpe_raw)}

| Sharpe Ratio | Interpretazione |
|---|---|
| > 2.0 | Eccellente — rendimento molto elevato per unità di rischio |
| 1.0 – 2.0 | Buono — giustifica l'esposizione al rischio |
| 0.5 – 1.0 | Accettabile — rendimento adeguato ma migliorabile |
| 0 – 0.5 | Debole — il rendimento a malapena compensa il rischio |
| < 0 | Negativo — l'asset non compensa nemmeno il tasso privo di rischio |

{benchmark_note}

### Efficienza del Portafoglio

| Metrica | Valore | Note |
|---|---|---|
| Rendimento annuo storico | {_pct(mu * 100)} | Stimato dalla media dei log-return |
| Volatilità annua | {_pct(sigma * 100)} | Deviazione standard annualizzata |
| Rendimento per unità di rischio | {_fmt(return_on_risk, 3) if return_on_risk else 'N/D'} | Rendimento / volatilità (Sharpe semplificato, rf=0) |
| Regime di volatilità | **{vol_label}** | Classificazione per confronto tra asset class |

> **Nota sul Sharpe ratio:** utilizza rf = 0. Con un tasso privo di rischio positivo
> (es. Fed Funds rate), il Sharpe si ridurrebbe di conseguenza.

---
"""


def _recommendations(ctx: dict) -> str:
    promotion = ctx.get("promotion", {})
    if not promotion.get("promoted", False):
        reasons = ", ".join(promotion.get("rejection_reasons", [])) or "gate di validazione non disponibile"
        return f"""## 6. Indicazione condizionata al modello

**Il modello non è promosso al report operativo.**

Condizioni non superate: {reasons}.

Le stime restano disponibili nel report tecnico per finalità di ricerca, ma non vengono
tradotte in sizing, raccomandazioni, prezzi target o stop-loss.

---
"""
    mu = ctx.get("mu_annual", 0)
    sigma = ctx.get("sigma_annual", 0)
    S0 = ctx.get("S0", 0)
    confidence = ctx.get("mc_confidence", 0.95)
    horizon = ctx.get("mc_horizon", 252)

    mc = ctx.get("mc_gbm", {})
    var_pct = abs(mc.get("VaR", 0))
    cvar_pct = abs(mc.get("CVaR", 0))

    rm = ctx.get("risk_metrics")
    sharpe_raw = rm.get("sharpe_ratio") if rm else None
    if sharpe_raw is None and sigma > 0:
        sharpe_raw = mu / sigma

    arima_fc = ctx.get("arima_fc_mean")
    vol_label, _, _ = _vol_regime(sigma)
    trend_label, _, _ = _trend_signal(mu, sigma, arima_fc)
    sharpe_l, _ = _sharpe_label(sharpe_raw)

    garch_fc = ctx.get("garch_forecast_vol_pct")

    # Position sizing: Kelly semplificato
    sigma_d = ctx.get("std_return_daily", sigma / 16)
    mu_d = ctx.get("mean_return_daily", mu / 252)
    kelly = mu_d / (sigma_d ** 2) if sigma_d > 0 else None
    kelly_capped = min(kelly, 1.0) if kelly and kelly > 0 else None
    kelly_note = (
        f"Il **criterio di Kelly semplificato** produce una frazione teorica pari a circa "
        f"**{kelly_capped*100:.0f}%** del capitale disponibile (cappata al 100%). "
        "È una stima aggressiva basata su media e varianza storiche: in pratica andrebbe ridotta "
        "fortemente (es. fractional Kelly) e validata con P&L, drawdown e costi."
        if kelly_capped
        else "Il criterio di Kelly non produce un segnale positivo con il profilo attuale."
    )

    # Stop-loss suggerito: CVaR daily
    var_daily = rm.get("var_95_daily_pct") if rm else None
    stop_note = (
        f"Un **livello di stop-loss** da {_pct(abs(var_daily) * 2)} (2× VaR giornaliero 95%) "
        f"corrisponderebbe a {_currency(S0 * abs(var_daily) / 50, decimals=2)} su un'esposizione di {_currency(S0, decimals=2)}."
        if var_daily is not None
        else ""
    )

    # Build bullets
    bullets = []

    if trend_label in ("RIALZISTA", "LIEVEMENTE RIALZISTA"):
        bullets.append("📈 Il segnale di tendenza è **positivo**: il contesto storico supporta un bias long, con gestione attiva del rischio.")
    elif trend_label == "RIBASSISTA":
        bullets.append("📉 Il segnale di tendenza è **negativo**: valutare riduzione dell'esposizione o copertura (hedge) prima di aggiungere posizioni.")
    else:
        bullets.append("➡️ Il segnale di tendenza è **neutro**: attendere conferma direzionale prima di assumere posizioni direzionali rilevanti.")

    if vol_label in ("ALTA", "MOLTO ALTA"):
        bullets.append(f"🔴 La volatilità è **{vol_label.lower()}** ({_pct(sigma*100)}): dimensionare le posizioni in modo conservativo e mantenere liquidità per margini.")
    else:
        bullets.append(f"🟡 La volatilità ({_pct(sigma*100)}) è nella norma per questa categoria di asset.")

    if sharpe_raw is not None and sharpe_raw > 1.0:
        bullets.append(f"🟢 Il profilo rischio/rendimento è **{sharpe_l.lower()}** (Sharpe = {_fmt(sharpe_raw)}): l'asset ha storicamente remunerato adeguatamente il rischio.")
    elif sharpe_raw is not None and sharpe_raw < 0.3:
        bullets.append(f"🔴 Il profilo rischio/rendimento è **debole** (Sharpe = {_fmt(sharpe_raw)}): considerare asset alternativi con migliore efficienza.")

    if garch_fc and garch_fc > sigma * 100 * 1.15:
        bullets.append("⚠️ La volatilità GARCH **aumenterà** rispetto alla media storica: ridurre esposizione o aumentare hedge in opzioni/futures.")

    bullets.append(f"📊 Il VaR {confidence*100:.0f}% su {horizon} giorni è **{_pct(var_pct*100)}**: su una posizione da $100.000 la perdita attesa nel 5% dei casi peggiori è ~${100000*var_pct:,.0f}.")

    bullets_text = "\n".join(f"- {b}" for b in bullets)

    return f"""## 6. Indicazioni condizionate al modello

### Evidenze condizionate alle ipotesi

{bullets_text}

### Position Sizing

{kelly_note}

**Soglia di rischio analizzata:** {stop_note}

### Caveat importanti

| Limitazione | Impatto |
|---|---|
| Media storica ≠ rendimento futuro | Il drift passato può invertirsi — non è una previsione |
| GBM assume normalità e costanza | Sottostima rischi in periodi di crisi |
| Nessun contesto macro | Tassi, inflazione, sentiment non sono nei modelli |
| Analisi monovariata | Non considera correlazioni con altri asset in portafoglio |
| Validazione predittiva incompleta | I segnali devono battere baseline naive, costi e test statistici out-of-sample |

---
"""


def _glossary() -> str:
    return """## 7. Glossario

| Termine | Definizione semplificata |
|---|---|
| **Rendimento logaritmico** | Variazione percentuale del prezzo calcolata come ln(P_t / P_{t-1}). È additivo nel tempo ed è lo standard in finanza quantitativa. |
| **Volatilità annualizzata** | Deviazione standard dei rendimenti giornalieri moltiplicata per √252. Misura quanto il prezzo oscilla in un anno tipico. |
| **VaR (Value at Risk)** | La perdita massima che non viene superata in X% degli scenari su un dato orizzonte temporale. Non dice quanto si perde *oltre* tale soglia. |
| **CVaR / Expected Shortfall** | La perdita media nei scenari peggiori oltre il VaR. È preferito dalle autorità regolamentari (Basilea III/IV) perché cattura il rischio di coda. |
| **Sharpe Ratio** | Rendimento annuo diviso per la volatilità annua (con rf = 0). Misura quante unità di rendimento si ottengono per ogni unità di rischio. |
| **ARIMA** | Modello statistico che prevede i rendimenti futuri basandosi sui rendimenti passati e sugli errori di previsione passati. |
| **GARCH** | Modello che stima la volatilità *condizionale*: la varianza cambia nel tempo in funzione degli shock recenti ("volatility clustering"). |
| **Monte Carlo** | Simulazione di migliaia di possibili percorsi futuri del prezzo, generati campionando casualmente i rendimenti. Produce una distribuzione di esiti. |
| **Drift** | La tendenza media di lungo periodo del prezzo (componente deterministica del moto browniano geometrico). |
| **Backtesting** | Verifica delle previsioni su dati storici *non usati* per l'addestramento del modello (out-of-sample). |
| **Direction Accuracy** | Percentuale di volte in cui il modello predice correttamente se il mercato salirà o scenderà. Valore di riferimento: 50% = caso puro. |

---

*Report generato automaticamente da `report_business.py` — Financial Time Series Platform.*
Questo documento non costituisce consulenza finanziaria né una raccomandazione di acquisto o vendita.
"""


# ---------------------------------------------------------------------------
# Entry point pubblico
# ---------------------------------------------------------------------------

def generate_business_report(ctx: dict, paths_final: "np.ndarray | None" = None,
                              output_dir: str = "reports") -> str:
    """
    Genera il report business in Markdown e lo salva su disco.

    Parameters
    ----------
    ctx : dict
        Stesso dizionario usato da generate_report() (report tecnico), arricchito
        con campi aggiuntivi:
          - arima_fc_mean   : float  — rendimento medio forecast ARIMA
          - sarima_fc_mean  : float  — rendimento medio forecast SARIMA
          - garch_forecast_vol_pct : float  — volatilità GARCH forecast media (%)
          - mc_scenarios    : dict   — output di _mc_scenario_summary()
    paths_final : np.ndarray, optional
        Array 1D dei prezzi terminali delle simulazioni Monte Carlo (paths[-1]).
        Se fornito, i percentili vengono ricalcolati.
    output_dir : str
        Cartella di destinazione.

    Returns
    -------
    str
        Percorso del file salvato.
    """
    # Arricchisci ctx con scenari MC se disponibili
    if paths_final is not None and len(paths_final) > 0:
        ctx = dict(ctx)
        ctx["mc_scenarios"] = _mc_scenario_summary(
            paths_final, ctx.get("S0", 0), ctx.get("mc_confidence", 0.95)
        )

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    ticker_safe = ctx.get("ticker", "UNKNOWN").replace("-", "_").replace("^", "")
    filename = f"REPORT_BUSINESS_{ticker_safe}_{date_str}.md"
    filepath = os.path.join(output_dir, filename)

    sections = [
        _header(ctx),
        _scorecard(ctx),
        _performance(ctx),
        _risk_profile(ctx),
        _monte_carlo_scenarios(ctx),
        _model_signals(ctx),
        _risk_adjusted_performance(ctx),
        _recommendations(ctx),
        _glossary(),
    ]

    content = "\n".join(sections)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n{'='*60}")
    print(f"  REPORT BUSINESS salvato in: {filepath}")
    print(f"{'='*60}\n")
    return filepath
