"""
legacy/report.py — Generatore storico di report narrativo in Markdown.

Raccoglie tutti i risultati della pipeline (stazionarietà, ARIMA, SARIMA,
GARCH, backtesting, Monte Carlo) e produce un documento interpretativo
salvato in reports/REPORT_{ticker}_{date}.md
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers di formattazione
# ---------------------------------------------------------------------------

def _fmt(v: Any, decimals: int = 4) -> str:
    """Formatta un numero float in modo leggibile."""
    if v is None:
        return "N/D"
    try:
        return f"{float(v):.{decimals}f}"
    except (TypeError, ValueError):
        return str(v)


def _pct(v: Any, decimals: int = 2) -> str:
    """Formatta come percentuale."""
    if v is None:
        return "N/D"
    try:
        return f"{float(v):.{decimals}f}%"
    except (TypeError, ValueError):
        return str(v)


def _bool_icon(b: bool | None) -> str:
    if b is None:
        return "N/D"
    if bool(b):
        return "✔ Sì"
    return "✘ No"


def _stationary_label(adf: dict, kpss: dict) -> str:
    a = adf.get("is_stationary")
    k = kpss.get("is_stationary")
    if a and k:
        return "**Stazionaria** (entrambi i test concordano)"
    if not a and not k:
        return "**Non stazionaria** (entrambi i test concordano — presenza di radice unitaria)"
    if a and not k:
        return "**Ambigua** (ADF: staz. | KPSS: non staz.) — possibile stazionarietà attorno a un trend"
    return "**Ambigua** (ADF: non staz. | KPSS: staz.)"


def _interpret_dir_acc(da: float) -> str:
    if da >= 60:
        return f"buona ({_pct(da)}) — il modello predice correttamente la direzione in più del 60% dei casi"
    if da >= 52:
        return f"moderata ({_pct(da)}) — lieve vantaggio informativo rispetto al caso"
    return f"scarsa ({_pct(da)}) — non significativamente meglio del lancio di una moneta"


def _interpret_var(var_pct: float, cvar_pct: float, horizon: int, confidence: float) -> str:
    conf_label = f"{confidence*100:.0f}%"
    return (
        f"Nel {conf_label} degli scenari simulati, la perdita sull'orizzonte di "
        f"{horizon} giorni di trading non supera il **{_pct(abs(var_pct) * 100)}** del valore iniziale. "
        f"Nei scenari peggiori (oltre il VaR) la perdita media attesa (**CVaR / Expected Shortfall**) "
        f"è pari al **{_pct(abs(cvar_pct) * 100)}**."
    )


def _best_garch(vol_comparison) -> str:
    """Restituisce il nome del modello con log-likelihood più alta."""
    try:
        return str(vol_comparison["log_lik"].idxmax())
    except Exception:
        return "N/D"


def _fmt_pvalue(p_value: Any) -> str:
    if p_value is None:
        return "N/D"
    try:
        p = float(p_value)
        return "<0.0001" if p < 0.0001 else f"{p:.4f}"
    except (TypeError, ValueError):
        return str(p_value)


def _lb_summary(diagnostics: dict, key: str = "ljung_box") -> str:
    lb = diagnostics.get(key, {}) if diagnostics else {}
    rows = []
    for lag, values in lb.items():
        status = "OK" if values.get("p_value", 0) >= 0.05 else "Autocorr."
        rows.append(f"lag {lag}: p={_fmt_pvalue(values.get('p_value'))} ({status})")
    return "; ".join(rows) if rows else "N/D"


# ---------------------------------------------------------------------------
# Sezioni del report
# ---------------------------------------------------------------------------

def _section_header(n: int, title: str) -> str:
    return f"\n## {n}. {title}\n"


def _build_metadata(ctx: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""# Report di Analisi — {ctx['ticker']}

> **Generato il:** {now}
> **Periodo dati:** {ctx['start_date']} → {ctx['end_date']}
> **Osservazioni:** {ctx['n_obs']} giorni di trading
> **Prezzo corrente ({ctx['ticker']}):** {_fmt(ctx['S0'], 2)}
> **Orizzonte di forecast:** {ctx['forecast_steps']} giorni
> **Simulazioni Monte Carlo:** {ctx['mc_sims']} percorsi × {ctx['mc_horizon']} giorni

---
"""


def _build_executive_summary(ctx: dict) -> str:
    adf_ret = ctx.get("adf_returns", {})
    kpss_ret = ctx.get("kpss_returns", {})
    arima = ctx.get("arima", {})
    sarima = ctx.get("sarima", {})
    bt_a = ctx.get("backtest_arima", {})
    bt_s = ctx.get("backtest_sarima", {})
    mc = ctx.get("mc_gbm", {})
    garch = ctx.get("garch", {})

    stationary_label = _stationary_label(adf_ret, kpss_ret)
    best_bt = "ARIMA" if bt_a.get("MAE", 1) <= bt_s.get("MAE", 1) else "SARIMA"
    var_val = mc.get("VaR", 0)
    cvar_val = mc.get("CVaR", 0)
    fc_vol = garch.get("forecast_vol")
    fc_vol_mean = float(fc_vol.mean() * 100) if fc_vol is not None else None

    return f"""{_section_header(0, "Executive Summary")}
| Indicatore | Valore |
|---|---|
| Stazionarietà dei rendimenti | {stationary_label} |
| Modello ARIMA selezionato | `ARIMA{arima.get('order', 'N/D')}` (AIC = {_fmt(arima.get('aic'), 2)}) |
| Modello SARIMA selezionato | `{sarima.get('label', 'N/D')}` (AIC = {_fmt(sarima.get('aic'), 2)}) |
| Modello migliore (backtest MAE) | **{best_bt}** |
| Rendimento atteso annualizzato | {_pct(ctx.get('mu_annual', 0) * 100, 2)} |
| Volatilità storica annualizzata | {_pct(ctx.get('sigma_annual', 0) * 100, 2)} |
| Volatilità GARCH forecast | {_pct(fc_vol_mean, 2) if fc_vol_mean else 'N/D'} |
| VaR {ctx.get('mc_confidence', 0.95)*100:.0f}% Monte Carlo ({ctx.get('mc_horizon', 252)}g) | {_pct(abs(var_val) * 100, 2)} |
| CVaR {ctx.get('mc_confidence', 0.95)*100:.0f}% Monte Carlo ({ctx.get('mc_horizon', 252)}g) | {_pct(abs(cvar_val) * 100, 2)} |

---
"""


def _build_descriptive(ctx: dict) -> str:
    mu_d = ctx.get("mean_return_daily", 0)
    std_d = ctx.get("std_return_daily", 0)
    sk = ctx.get("skewness", 0)
    kurt = ctx.get("kurtosis", 0)

    sk_interp = (
        "positiva (coda destra più pesante — rari guadagni estremi)"
        if sk > 0.3
        else "negativa (coda sinistra più pesante — rischio di perdite estreme)" if sk < -0.3
        else "approssimativamente simmetrica"
    )
    kurt_interp = (
        f"**leptocurtica** (curtosi = {_fmt(kurt, 2)}): code più spesse della normale, "
        "eventi estremi più frequenti del previsto (fat tails tipici dei mercati finanziari)"
        if kurt > 1
        else f"approssimativamente normale (curtosi = {_fmt(kurt, 2)})"
    )

    return f"""{_section_header(1, "Statistiche Descrittive dei Rendimenti")}
| Metrica | Valore |
|---|---|
| Media giornaliera | {_fmt(mu_d, 6)} |
| Deviazione standard giornaliera | {_fmt(std_d, 6)} |
| Rendimento atteso annualizzato (×252) | {_pct(ctx.get('mu_annual', 0) * 100, 2)} |
| Volatilità annualizzata (×√252) | {_pct(ctx.get('sigma_annual', 0) * 100, 2)} |
| Asimmetria (Skewness) | {_fmt(sk, 4)} |
| Eccesso di curtosi (Kurtosis) | {_fmt(kurt, 4)} |

**Interpretazione:**

- **Asimmetria:** {sk_interp}.
- **Distribuzione:** {kurt_interp}.
- Un rendimento atteso annualizzato di {_pct(ctx.get('mu_annual', 0) * 100, 2)} va interpretato con cautela:
  la media storica dei rendimenti logaritmici è un estimatore rumoroso del rendimento futuro,
  soprattutto su orizzonti brevi.

---
"""


def _build_stationarity(ctx: dict) -> str:
    adf_p = ctx.get("adf_prices", {})
    kpss_p = ctx.get("kpss_prices", {})
    adf_r = ctx.get("adf_returns", {})
    kpss_r = ctx.get("kpss_returns", {})

    def _row(label, adf, kpss):
        sl = _stationary_label(adf, kpss)
        return (
            f"| {label} | {_fmt(adf.get('statistic'), 4)} | {_fmt(adf.get('p_value'), 4)} | "
            f"{_bool_icon(adf.get('is_stationary'))} | "
            f"{_fmt(kpss.get('statistic'), 4)} | {_fmt(kpss.get('p_value'), 4)} | "
            f"{_bool_icon(kpss.get('is_stationary'))} | {sl} |"
        )

    adf_r_stat = adf_r.get("is_stationary", False)
    kpss_r_stat = kpss_r.get("is_stationary", False)

    if adf_r_stat and kpss_r_stat:
        conclusion = (
            "I rendimenti logaritmici risultano **stazionari** in base a entrambi i test. "
            "Questo è il risultato atteso e desiderato: conferma che è corretto modellare "
            "i *rendimenti* (e non i prezzi) con ARIMA e GARCH senza necessità di differenziazione "
            "aggiuntiva (d = 0)."
        )
    elif not adf_r_stat and not kpss_r_stat:
        conclusion = (
            "Attenzione: i rendimenti logaritmici mostrano segni di **non stazionarietà**. "
            "Questo è inusuale e potrebbe indicare la presenza di regimi strutturali nel periodo analizzato. "
            "Considerare una differenziazione o modelli a regime (MS-GARCH)."
        )
    else:
        conclusion = (
            "Il risultato è **ambiguo**: i due test danno conclusioni contrastanti. "
            "Questo accade spesso in presenza di trend deboli o break strutturali. "
            "I rendimenti logaritmici vengono comunque trattati come stazionari per la modellazione."
        )

    return f"""{_section_header(2, "Test di Stazionarietà (ADF & KPSS)")}
**Contesto teorico:**
- **ADF** (Augmented Dickey-Fuller): H₀ = presenza di radice unitaria (non stazionaria).
  Un p-value < 0.05 consente di rifiutare H₀ → la serie è stazionaria.
- **KPSS**: H₀ = serie stazionaria. Un p-value < 0.05 rifiuta H₀ → la serie è non stazionaria.
- I due test sono complementari: idealmente concordano entrambi.

| Serie | ADF stat | ADF p-val | ADF staz. | KPSS stat | KPSS p-val | KPSS staz. | Conclusione |
|---|---|---|---|---|---|---|---|
{_row("Prezzi", adf_p, kpss_p)}
{_row("Rendimenti Log", adf_r, kpss_r)}

**Interpretazione:**

I prezzi di un asset finanziario seguono tipicamente un **random walk** (processo integrato di ordine 1),
quindi ci si aspetta che siano non stazionari — confermato dai test sui prezzi.
I rendimenti logaritmici, calcolati come $r_t = \\ln(p_t / p_{{t-1}})$, rimuovono la tendenza
stocastica rendendo la serie analizzabile con modelli stazionari.

{conclusion}

---
"""


def _build_arima(ctx: dict) -> str:
    ar = ctx.get("arima", {})
    order = ar.get("order", (1, 0, 1))
    p, d, q = order
    aic = ar.get("aic")
    bic = ar.get("bic")
    fc_steps = ctx.get("forecast_steps", 20)
    diag = ar.get("diagnostics", {})
    arch = diag.get("arch_lm", {})
    jb = diag.get("jarque_bera", {})

    # Ljung-Box: non abbiamo i valori nella struttura, descriviamo il test
    p_interp = (
        "La componente AR(p) cattura la dipendenza lineare dei rendimenti dai propri valori passati."
        if p > 0
        else "Nessuna componente autoregressiva (p=0): i rendimenti passati non aiutano a spiegare quelli correnti."
    )
    q_interp = (
        "La componente MA(q) cattura l'effetto degli shock passati (errori di previsione)."
        if q > 0
        else "Nessuna componente moving average (q=0)."
    )

    return f"""{_section_header(3, "Modello ARIMA — Media Condizionale")}
**Ordine selezionato:** `ARIMA({p}, {d}, {q})`

| Metrica | Valore |
|---|---|
| Ordine (p, d, q) | ({p}, {d}, {q}) |
| AIC | {_fmt(aic, 4)} |
| BIC | {_fmt(bic, 4) if bic else 'N/D'} |
| Integrazione (d) | {d} — serie già stazionaria, nessuna differenziazione necessaria |
| Orizzonte forecast | {fc_steps} giorni |
| Ljung-Box residui | {_lb_summary(diag)} |
| ARCH-LM residui | p = {_fmt_pvalue(arch.get('p_value'))} |
| Jarque-Bera residui | p = {_fmt_pvalue(jb.get('p_value'))} |

**Interpretazione:**

L'ordine è stato selezionato minimizzando l'**AIC** (Akaike Information Criterion),
che penalizza la complessità del modello per evitare l'overfitting.

- {p_interp}
- {q_interp}
- **d = {d}**: i rendimenti logaritmici sono già stazionari, non è necessaria differenziazione.

**Diagnostica residui:**
I p-value Ljung-Box verificano se resta autocorrelazione lineare nei residui. ARCH-LM
verifica se resta eteroschedasticità condizionale, segnale che un modello GARCH sulla
varianza è necessario. Jarque-Bera testa la normalità: sui rendimenti finanziari è comune
rifiutarla per via di code spesse.

**Forecast:**
Il modello produce previsioni puntuali dei rendimenti per i prossimi {fc_steps} giorni
con **intervalli di confidenza al 95%**. Data la bassa persistenza dell'autocorrelazione
nei rendimenti finanziari, le previsioni tendono rapidamente verso la media storica
(mean-reversion), con bande di incertezza che si allargano progressivamente.

---
"""


def _build_sarima(ctx: dict) -> str:
    sr = ctx.get("sarima", {})
    order = sr.get("order", (1, 0, 1))
    sorder = sr.get("seasonal_order", (1, 0, 1, 5))
    label = sr.get("label", f"SARIMA{order}×{sorder}")
    aic = sr.get("aic")
    bic = sr.get("bic")
    diag = sr.get("diagnostics", {})
    arch = diag.get("arch_lm", {})
    s = sorder[3] if len(sorder) > 3 else 5
    s_label = "settimanale (5 giorni di trading)" if s == 5 else f"s={s}"
    ar = ctx.get("arima", {})
    aic_diff = None
    if aic and ar.get("aic"):
        aic_diff = float(aic) - float(ar["aic"])

    diff_interp = ""
    if aic_diff is not None:
        if aic_diff < -2:
            diff_interp = f"Il SARIMA ha AIC inferiore di {abs(aic_diff):.2f} rispetto all'ARIMA: la componente stagionale **migliora significativamente** il fit."
        elif aic_diff < 2:
            diff_interp = f"La differenza di AIC tra SARIMA e ARIMA è trascurabile ({aic_diff:+.2f}): la stagionalità **non aggiunge informazione rilevante** in questo caso."
        else:
            diff_interp = f"Il SARIMA ha AIC superiore di {aic_diff:.2f} rispetto all'ARIMA: la componente stagionale **penalizza il fit** e potrebbe essere rimossa."

    return f"""{_section_header(4, "Modello SARIMA — Componente Stagionale")}
**Specifica:** `{label}`

| Metrica | Valore |
|---|---|
| Ordine non-stagionale | {order} |
| Ordine stagionale | {sorder} |
| Stagionalità | {s_label} |
| AIC | {_fmt(aic, 4)} |
| BIC | {_fmt(bic, 4) if bic else 'N/D'} |
| Ljung-Box residui | {_lb_summary(diag)} |
| ARCH-LM residui | p = {_fmt_pvalue(arch.get('p_value'))} |

**Interpretazione:**

Il SARIMA estende l'ARIMA aggiungendo termini AR e MA stagionali,
utili per catturare pattern che si ripetono con periodicità fissa
(ad esempio effetti "day-of-week" nei mercati finanziari, con s = 5).

{diff_interp}

In pratica, i rendimenti finanziari giornalieri mostrano raramente una stagionalità
forte e stabile. La componente stagionale è comunque inclusa per verifica empirica
e il confronto via backtesting fornisce la valutazione definitiva.

---
"""


def _build_garch(ctx: dict) -> str:
    garch = ctx.get("garch", {})
    vol_comp = ctx.get("vol_comparison")
    fc_vol = garch.get("forecast_vol")
    fc_vol_mean = float(fc_vol.mean() * 100) if fc_vol is not None else None
    fc_vol_last = float(fc_vol[-1] * 100) if fc_vol is not None else None
    cond_vol = garch.get("conditional_vol_annual")
    vol_mean = float(cond_vol.mean() * 100) if cond_vol is not None else None
    vol_max = float(cond_vol.max() * 100) if cond_vol is not None else None
    diag = garch.get("diagnostics", {})

    # Tabella comparativa modelli
    comp_table = ""
    if vol_comp is not None and not vol_comp.empty:
        best = _best_garch(vol_comp)
        rows = []
        for name, row in vol_comp.iterrows():
            marker = " ★" if name == best else ""
            rows.append(
                f"| {name}{marker} | {_fmt(row.get('log_lik'), 2)} | "
                f"{_fmt(row.get('aic'), 2)} | {_fmt(row.get('bic'), 2)} | "
                f"{_pct(row.get('vol_annualized_mean_%'), 2)} | "
                f"{_pct(row.get('forecast_vol_mean_%'), 2)} |"
            )
        comp_table = (
            "| Modello | Log-Likelihood | AIC | BIC | Vol. storica media | Vol. forecast media |\n"
            "|---|---|---|---|---|---|\n"
            + "\n".join(rows)
        )
    else:
        comp_table = "*Dati comparativi non disponibili.*"

    return f"""{_section_header(5, "Famiglia GARCH — Volatilità Condizionale")}
**Modello principale:** `{garch.get('vol_type', 'GARCH(1,1)')}` con distribuzione t di Student

### 5.1 Confronto GARCH / EGARCH / TARCH

{comp_table}

*(★ = modello con log-likelihood più alta = fit migliore)*

### 5.2 Interpretazione dei modelli

| Modello | Caratteristica |
|---|---|
| **GARCH(1,1)** | Volatilità simmetrica: shocks positivi e negativi hanno lo stesso effetto sulla varianza |
| **EGARCH(1,1)** | Cattura l'effetto leva: le cattive notizie (rendimenti negativi) aumentano la volatilità più delle buone notizie |
| **TARCH/GJR-GARCH** | Asimmetria via termine additivo: gli shock negativi hanno un coefficiente extra rispetto a quelli positivi |

### 5.3 Statistiche di volatilità

| Metrica | Valore |
|---|---|
| Volatilità condizionale media (annualizzata) | {_pct(vol_mean, 2) if vol_mean else 'N/D'} |
| Picco di volatilità storica (annualizzata) | {_pct(vol_max, 2) if vol_max else 'N/D'} |
| Forecast volatilità media ({ctx.get('forecast_steps', 20)} gg) | {_pct(fc_vol_mean, 2) if fc_vol_mean else 'N/D'} |
| Forecast volatilità (ultimo giorno) | {_pct(fc_vol_last, 2) if fc_vol_last else 'N/D'} |
| Persistenza volatilità | {_fmt(diag.get('persistence'), 4)} |
| Varianza stazionaria | {'Sì' if diag.get('stationary_variance') else 'No/N.D.'} |
| Ljung-Box residui standardizzati | {_lb_summary(diag, 'ljung_box_std_resid')} |
| Ljung-Box residui standardizzati² | {_lb_summary(diag, 'ljung_box_squared_std_resid')} |

**Interpretazione:**

Il parametro **beta** di GARCH(1,1) misura la **persistenza della volatilità**:
valori vicini a 1 indicano che i periodi di alta volatilità tendono a durare a lungo
("volatility clustering"), fenomeno tipico dei mercati finanziari.
La distribuzione t di Student è preferita alla normale perché cattura
le **code spesse** (fat tails) dei rendimenti reali.

La volatilità GARCH forecast converge verso la **volatilità di lungo periodo**
(unconditional volatility) man mano che l'orizzonte si allunga.
Se la volatilità corrente è superiore a quella storica media,
ci si attende un ritorno graduale verso valori più bassi (**mean-reversion della volatilità**).

---
"""


def _build_backtesting(ctx: dict) -> str:
    bt_a = ctx.get("backtest_arima", {})
    bt_s = ctx.get("backtest_sarima", {})
    baselines = ctx.get("backtest_baselines", {})
    direction_tests = ctx.get("direction_tests", {})
    dm = ctx.get("dm_test", {})
    dm_vs_baseline = ctx.get("dm_vs_baseline", {})

    mae_a = bt_a.get("MAE", None)
    mae_s = bt_s.get("MAE", None)
    if mae_a is not None and mae_s is not None:
        winner = "ARIMA" if mae_a <= mae_s else "SARIMA"
        winner_mae = min(mae_a, mae_s)
    else:
        winner = "N/D"
        winner_mae = None

    da_a = bt_a.get("Direction_Accuracy_%")
    da_s = bt_s.get("Direction_Accuracy_%")
    da_a_interp = _interpret_dir_acc(da_a) if da_a else "N/D"
    da_s_interp = _interpret_dir_acc(da_s) if da_s else "N/D"

    dm_text = ""
    if dm:
        dm_stat = dm.get("dm_stat")
        dm_pval = dm.get("p_value")
        dm_concl = dm.get("conclusion", "")
        if dm_pval is not None:
            if dm_pval < 0.05:
                dm_text = (
                    f"Il **test di Diebold-Mariano** (DM = {_fmt(dm_stat, 4)}, p = {_fmt(dm_pval, 4)}) "
                    f"**rifiuta H₀** al 5%: {dm_concl} produce previsioni statisticamente più accurate."
                )
            else:
                dm_text = (
                    f"Il **test di Diebold-Mariano** (DM = {_fmt(dm_stat, 4)}, p = {_fmt(dm_pval, 4)}) "
                    "**non rifiuta H₀**: non vi è differenza statistica significativa nell'accuratezza "
                    "delle previsioni tra ARIMA e SARIMA."
                )

    baseline_rows = []
    for name, values in baselines.items():
        baseline_rows.append(
            f"| {name} | {_fmt(values.get('MAE'), 6)} | {_fmt(values.get('RMSE'), 6)} | "
            f"{_pct(values.get('Direction_Accuracy_%'), 2)} |"
        )
    baseline_table = "\n".join(baseline_rows) if baseline_rows else "| N/D | N/D | N/D | N/D |"

    direction_rows = []
    for name, values in direction_tests.items():
        sig = "Sì" if values.get("significant") else "No"
        direction_rows.append(
            f"| {name} | {values.get('successes', 'N/D')}/{values.get('n', 'N/D')} | "
            f"{_pct(values.get('accuracy_pct'), 2)} | {_fmt_pvalue(values.get('p_value'))} | {sig} |"
        )
    direction_table = "\n".join(direction_rows) if direction_rows else "| N/D | N/D | N/D | N/D | N/D |"

    dm_baseline_rows = []
    for name, values in dm_vs_baseline.items():
        sig = "Sì" if values.get("significant") else "No"
        dm_baseline_rows.append(
            f"| ARIMA vs {name} | {_fmt(values.get('dm_stat'), 4)} | "
            f"{_fmt_pvalue(values.get('p_value'))} | {values.get('hac_lag', 'N/D')} | {sig} |"
        )
    dm_baseline_table = "\n".join(dm_baseline_rows) if dm_baseline_rows else "| N/D | N/D | N/D | N/D | N/D |"

    return f"""{_section_header(6, "Backtesting Walk-Forward")}
Il backtesting walk-forward valuta i modelli su dati **out-of-sample**: ad ogni passo
il modello viene riaddestrando sul passato e testato sui successivi {ctx.get('forecast_steps', 20)} giorni,
simulando un utilizzo reale in tempo reale.

| Metrica | ARIMA | SARIMA | Migliore |
|---|---|---|---|
| MAE | {_fmt(bt_a.get('MAE'), 6)} | {_fmt(bt_s.get('MAE'), 6)} | {'ARIMA ★' if winner == 'ARIMA' else 'SARIMA ★'} |
| RMSE | {_fmt(bt_a.get('RMSE'), 6)} | {_fmt(bt_s.get('RMSE'), 6)} | {'ARIMA ★' if (bt_a.get('RMSE') or 1) <= (bt_s.get('RMSE') or 1) else 'SARIMA ★'} |
| MAPE (%) | {_fmt(bt_a.get('MAPE_%'), 4)} | {_fmt(bt_s.get('MAPE_%'), 4)} | — |
| Direction Accuracy | {_pct(da_a, 2)} | {_pct(da_s, 2)} | {'ARIMA ★' if (da_a or 0) >= (da_s or 0) else 'SARIMA ★'} |
| N. previsioni | {bt_a.get('N_forecasts', 'N/D')} | {bt_s.get('N_forecasts', 'N/D')} | |

### 6.1 Baseline naive

| Baseline | MAE | RMSE | Direction Accuracy |
|---|---|---|---|
{baseline_table}

### 6.2 Significatività direzionale

| Modello | Hit direzionali | Accuracy | p-value binomiale | Significativo 5% |
|---|---|---|---|---|
{direction_table}

### 6.3 Diebold-Mariano HAC vs baseline

| Confronto | DM stat | p-value | HAC lag | Differenza significativa |
|---|---|---|---|---|
{dm_baseline_table}

**Interpretazione delle metriche:**

- **MAE** (Mean Absolute Error): errore medio assoluto in unità di log-return.
  Valori bassi indicano previsioni più precise. Per i rendimenti giornalieri,
  valori nell'ordine di 0.01–0.03 sono tipici.
- **RMSE** (Root Mean Squared Error): penalizza maggiormente gli errori grandi.
  Utile per rilevare se il modello produce occasionalmente errori molto ampi.
- **MAPE**: l'errore percentuale medio è spesso instabile per i rendimenti
  (che possono essere vicini a zero), va interpretato con cautela.
- **Direction Accuracy**: la metrica più operativa per un trader. Indica la
  percentuale di volte in cui il modello predice correttamente il segno del rendimento.

  - ARIMA: {da_a_interp}
  - SARIMA: {da_s_interp}

{dm_text}

Il test DM usa una varianza HAC/Newey-West per ridurre il rischio di p-value troppo
ottimistici quando le perdite di forecast sono autocorrelate o generate da previsioni
multi-step.

**Conclusione:** il modello migliore per MAE è **{winner}** (MAE = {_fmt(winner_mae, 6)}).
Si raccomanda comunque di affiancare le metriche di backtest con una valutazione
economica (P&L simulato) prima di usare le previsioni per decisioni operative.

---
"""


def _build_montecarlo(ctx: dict) -> str:
    mc = ctx.get("mc_gbm", {})
    mc_g = ctx.get("mc_garch", {})
    confidence = ctx.get("mc_confidence", 0.95)
    horizon = ctx.get("mc_horizon", 252)
    n_sims = ctx.get("mc_sims", 1000)

    var_gbm = mc.get("VaR", 0)
    cvar_gbm = mc.get("CVaR", 0)
    mean_ret = mc.get("mean_terminal_return", 0)
    std_ret = mc.get("std_terminal_return", 0)

    var_garch = mc_g.get("VaR") if mc_g else None
    cvar_garch = mc_g.get("CVaR") if mc_g else None
    var_bt = ctx.get("var_backtest", {})

    garch_row = ""
    if var_garch is not None:
        garch_row = f"| MC-GARCH (vol. dinamica) | {_pct(abs(var_garch)*100, 2)} | {_pct(abs(cvar_garch)*100, 2)} |"
    else:
        garch_row = "| MC-GARCH (vol. dinamica) | N/D | N/D |"

    var_interp = _interpret_var(var_gbm, cvar_gbm, horizon, confidence)
    conf_label = f"{confidence*100:.0f}%"

    return f"""{_section_header(7, "Simulazioni Monte Carlo — VaR e CVaR")}
Sono state eseguite **{n_sims} simulazioni** su un orizzonte di **{horizon} giorni** ({horizon//21} mesi ca.).

### 7.1 Geometric Brownian Motion (GBM)

Il GBM assume che i rendimenti siano normalmente distribuiti con drift e volatilità **costanti**:

$$dS = S(\\mu \\, dt + \\sigma \\, dW_t)$$

con $\\mu = $ {_pct(ctx.get('mu_annual',0)*100, 2)} (drift annuo) e $\\sigma = $ {_pct(ctx.get('sigma_annual',0)*100, 2)} (vol. annua).

| Metrica | GBM | MC-GARCH |
|---|---|---|
| VaR {conf_label} ({horizon}g) | {_pct(abs(var_gbm)*100, 2)} | {_pct(abs(var_garch)*100, 2) if var_garch else 'N/D'} |
| CVaR {conf_label} ({horizon}g) | {_pct(abs(cvar_gbm)*100, 2)} | {_pct(abs(cvar_garch)*100, 2) if cvar_garch else 'N/D'} |
| Rendimento medio simulato | {_pct(mean_ret*100, 2)} | — |
| Std. dev. rendimento simulato | {_pct(std_ret*100, 2)} | — |
{garch_row}

### 7.2 Interpretazione

{var_interp}

**GBM vs MC-GARCH:**

Il **GBM classico** (volatilità costante) sottostima il rischio nei periodi di stress:
non cattura il **volatility clustering** né le code spesse della distribuzione dei rendimenti.

Il **Monte Carlo GARCH** usa la volatilità dinamica stimata da GARCH(1,1):
la varianza cambia ogni giorno in funzione degli shock passati, producendo
distribuzioni dei prezzi con code più spesse e stime di VaR tipicamente
**più conservative** (VaR più alto in valore assoluto), più vicine alla realtà empirica.

**Nota metodologica:**
- Il **VaR** è una misura del rischio al percentile: non dice quanto si può perdere *oltre* quella soglia.
- Il **CVaR** (Expected Shortfall) completa l'immagine misurando la perdita media
  nei {100-int(confidence*100)}% dei casi peggiori — è la misura preferita da Basilea III/IV.

### 7.3 Backtest copertura VaR storico

| Metrica | Valore |
|---|---|
| Soglia VaR storica giornaliera | {_pct((var_bt.get('var_level') or 0) * 100, 3)} |
| Violazioni osservate | {var_bt.get('breaches', 'N/D')} |
| Violazioni attese | {_fmt(var_bt.get('expected_breaches'), 2)} |
| Tasso violazioni osservato | {_pct(var_bt.get('breach_rate_pct'), 2)} |
| Kupiec p-value | {_fmt_pvalue(var_bt.get('kupiec_p_value'))} |
| Copertura coerente al 5% | {'Sì' if var_bt.get('valid_coverage') else 'No/N.D.'} |

---
"""


def _build_risk_metrics(ctx: dict) -> str:
    rm = ctx.get("risk_metrics")
    if rm is None:
        return f"""{_section_header(8, "Metriche di Rischio (dbt — fct_risk_metrics)")}
*Dati non disponibili (la tabella fct_risk_metrics non contiene dati per {ctx.get('ticker', 'N/D')}).*

---
"""
    ticker = ctx.get("ticker", "N/D")

    def _get(key):
        try:
            v = rm.get(key)
            return _fmt(v, 4) if v is not None else "N/D"
        except Exception:
            return "N/D"

    return f"""{_section_header(8, "Metriche di Rischio (dbt — fct_risk_metrics)")}
Dati storici aggregati calcolati via dbt (SQL su DuckDB):

| Metrica | Valore |
|---|---|
| Asset class | {_get('asset_class')} |
| Prima data osservata | {_get('first_date')} |
| Ultima data osservata | {_get('last_date')} |
| N. osservazioni | {_get('n_obs')} |
| Rendimento atteso annuale | {_get('expected_annual_return_pct')}% |
| Volatilità annualizzata | {_get('vol_annual_pct')}% |
| Sharpe Ratio | {_get('sharpe_ratio')} |
| VaR storico 95% (1 giorno) | {_get('var_95_daily_pct')}% |
| CVaR storico 95% (1 giorno) | {_get('cvar_95_daily_pct')}% |

**Interpretazione:**

- **Sharpe Ratio:** misura il rendimento aggiustato per il rischio rispetto a un tasso privo di rischio.
  Valori > 1 indicano un buon profilo rischio/rendimento; < 0 indicano rendimento inferiore al risk-free.
- **VaR storico 95%:** calcolato come percentile 5° dei rendimenti giornalieri storici.
  Misura la perdita massima giornaliera non superata nel 95% delle sedute passate.
  È un approccio "non parametrico" (non assume una distribuzione specifica).
- **CVaR storico 95%:** media dei rendimenti sotto il VaR 95%.
  Risponde alla domanda: *"quanto perdo in media nelle giornate peggiori?"*

---
"""


def _build_conclusions(ctx: dict) -> str:
    ticker = ctx.get("ticker", "N/D")
    adf_r = ctx.get("adf_returns", {})
    kpss_r = ctx.get("kpss_returns", {})
    arima = ctx.get("arima", {})
    sarima = ctx.get("sarima", {})
    bt_a = ctx.get("backtest_arima", {})
    bt_s = ctx.get("backtest_sarima", {})
    mc = ctx.get("mc_gbm", {})
    confidence = ctx.get("mc_confidence", 0.95)
    horizon = ctx.get("mc_horizon", 252)

    winner = "ARIMA" if bt_a.get("MAE", 1) <= bt_s.get("MAE", 1) else "SARIMA"
    var_val = abs(mc.get("VaR", 0)) * 100
    cvar_val = abs(mc.get("CVaR", 0)) * 100
    stationary = adf_r.get("is_stationary", False) and kpss_r.get("is_stationary", False)

    staz_bullet = (
        "I rendimenti logaritmici sono **stazionari** — prerequisito soddisfatto per la modellazione ARIMA/GARCH."
        if stationary
        else "I rendimenti logaritmici mostrano potenziali anomalie di stazionarietà — interpretare i modelli con cautela."
    )

    return f"""{_section_header(9, "Conclusioni")}
### Riepilogo per {ticker}

1. **Stazionarietà:** {staz_bullet}

2. **Modello di media condizionale:** `ARIMA{arima.get('order', '')}` (AIC={_fmt(arima.get('aic'), 2)})
   e `{sarima.get('label', '')}` (AIC={_fmt(sarima.get('aic'), 2)}) sono stati stimati e confrontati.
   Il modello **{winner}** mostra la minore perdita media out-of-sample (MAE).

3. **Modello di varianza condizionale:** la famiglia GARCH cattura il **volatility clustering**
   tipico dei mercati finanziari. La distribuzione t di Student è appropriata per le code spesse
   dei rendimenti.

4. **Forecast:** le previsioni di rendimento convergeranno rapidamente verso la media storica
   (random walk behaviour). Il valore informativo principale è negli **intervalli di confidenza**
   e nella stima della volatilità futura piuttosto che nelle previsioni puntuali.

5. **Rischio:** il VaR {confidence*100:.0f}% Monte Carlo su {horizon} giorni è stimato al
   **{_pct(var_val, 2)}** del capitale investito; il CVaR (perdita attesa nei scenari peggiori)
   è **{_pct(cvar_val, 2)}**.

### Limitazioni e sviluppi futuri

| Limitazione | Possibile soluzione |
|---|---|
| GBM assume volatilità costante | Già mitigato da MC-GARCH |
| ARIMA cattura solo dipendenza lineare | Modelli LSTM / Transformer |
| Analisi monovariata | VAR multi-asset, cointegrazione |
| Nessun cambio di regime | Markov-Switching GARCH |
| Risk-free rate = 0 nel Sharpe | Integrare tassi FRED |

---

*Report generato automaticamente da `report.py` — Financial Time Series Platform.*
"""


# ---------------------------------------------------------------------------
# Entry point pubblico
# ---------------------------------------------------------------------------

def generate_report(ctx: dict, output_dir: str = "reports") -> str:
    """
    Genera il report in Markdown e lo salva su disco.

    Parameters
    ----------
    ctx : dict
        Dizionario con tutti i risultati della pipeline (vedi main.py).
    output_dir : str
        Cartella di destinazione (verrà creata se non esiste).

    Returns
    -------
    str
        Percorso del file salvato.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    ticker_safe = ctx.get("ticker", "UNKNOWN").replace("-", "_").replace("^", "")
    filename = f"REPORT_{ticker_safe}_{date_str}.md"
    filepath = os.path.join(output_dir, filename)

    sections = [
        _build_metadata(ctx),
        _build_executive_summary(ctx),
        _build_descriptive(ctx),
        _build_stationarity(ctx),
        _build_arima(ctx),
        _build_sarima(ctx),
        _build_garch(ctx),
        _build_backtesting(ctx),
        _build_montecarlo(ctx),
        _build_risk_metrics(ctx),
        _build_conclusions(ctx),
    ]

    content = "\n".join(sections)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n{'='*60}")
    print(f"  REPORT salvato in: {filepath}")
    print(f"{'='*60}\n")
    return filepath
