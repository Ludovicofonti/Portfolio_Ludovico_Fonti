"""Business report leggibile da analisti finanziari e risk manager."""

from __future__ import annotations

import math
from typing import Iterable

from .disclaimers import DISCLAIMER


def promotion_decision(*, model_metric: float, baseline_metric: float, higher_is_better: bool,
                       net_return: float, stability_score: float, calibration_score: float,
                       minimum_stability: float = 0.60, minimum_calibration: float = 0.70,
                       residuals_valid: bool = True,
                       require_positive_after_costs: bool = True) -> dict:
    beats_baseline = model_metric > baseline_metric if higher_is_better else model_metric < baseline_metric
    checks = {
              "beats_baseline": beats_baseline,
              "positive_after_costs": (net_return > 0) if require_positive_after_costs else True,
              "stable_across_folds": stability_score >= minimum_stability,
              "acceptable_calibration": calibration_score >= minimum_calibration,
              "valid_residuals": residuals_valid}
    return {"promoted": all(checks.values()), "checks": checks,
            "rejection_reasons": [name for name, passed in checks.items() if not passed]}


def _as_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _fmt_number(value, digits: int = 3) -> str:
    number = _as_float(value)
    if number is None:
        return "N/D"
    return f"{number:,.{digits}f}"


def _fmt_percent(value, digits: int = 2) -> str:
    number = _as_float(value)
    if number is None:
        return "N/D"
    return f"{number * 100:,.{digits}f}%"


def _fmt_metric(value) -> str:
    number = _as_float(value)
    if number is None:
        return "N/D"
    if abs(number) < 0.01:
        return f"{number:.6f}"
    return f"{number:.4f}"


def _fmt_bool(value) -> str:
    return "Pass" if bool(value) else "Fail"


def _clean_cell(value) -> str:
    text = str(value).replace("\n", " ").replace("|", "/")
    return text if text else "N/D"


def _table(headers: Iterable[str], rows: Iterable[Iterable[object]]) -> str:
    headers = [_clean_cell(item) for item in headers]
    body = [[_clean_cell(item) for item in row] for row in rows]
    if not body:
        body = [["N/D" for _ in headers]]
    separator = ["---" for _ in headers]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def _task_label(task: str | None) -> str:
    return {
        "return": "Previsione rendimento",
        "direction": "Probabilita' direzionale",
        "volatility": "Stima volatilita'",
        "tail": "Rischio di coda",
    }.get(str(task), str(task or "N/D"))


def _business_action(promoted: bool, task: str | None) -> str:
    if promoted and task in {"return", "direction"}:
        return "Candidato a paper trading controllato e revisione del sizing."
    if promoted:
        return "Candidato a monitoraggio operativo come indicatore di rischio."
    if task in {"volatility", "tail"}:
        return "Usare solo come indicatore di rischio sperimentale, non come trigger operativo."
    return "Non usare per allocazione o segnali trading; mantenere in osservazione."


def _status_text(promoted: bool) -> str:
    return "PROMOSSO PER USO OPERATIVO" if promoted else "NON PROMOSSO - SOLO ANALISI INFORMATIVA"


def _gate_label(name: str) -> str:
    return {
        "beats_baseline": "Batte la baseline",
        "positive_after_costs": "Resta positivo dopo i costi",
        "stable_across_folds": "Stabile sui fold temporali",
        "acceptable_calibration": "Calibrazione accettabile",
        "valid_residuals": "Residui sotto controllo",
    }.get(name, name)


def _gate_business_meaning(name: str) -> str:
    return {
        "beats_baseline": "Il modello aggiunge valore rispetto a una regola semplice.",
        "positive_after_costs": "Il segnale sopravvive a fee, spread e slippage.",
        "stable_across_folds": "Il risultato non dipende da una singola finestra favorevole.",
        "acceptable_calibration": "Le probabilita'/stime sono coerenti con gli esiti osservati.",
        "valid_residuals": "Gli errori non mostrano bias eccessivo.",
    }.get(name, "Controllo qualitativo del modello.")


def _rejection_label(name: str) -> str:
    return {
        "beats_baseline": "non batte la baseline",
        "positive_after_costs": "non resta positivo dopo i costi",
        "stable_across_folds": "non e' stabile sui fold temporali",
        "acceptable_calibration": "calibrazione non accettabile",
        "valid_residuals": "residui non sotto controllo",
    }.get(name, name)


def _scope_table(context: dict) -> str:
    rows = [
        ("Run", context.get("run_id", "N/D")),
        ("Asset", context.get("asset", context.get("symbol", "N/D"))),
        ("Task", _task_label(context.get("task"))),
        ("Modello", context.get("model", "N/D")),
        ("Orizzonte", f"{context.get('horizon', 'N/D')} periodi"),
        ("Campione dati", f"{context.get('data_start', 'N/D')} -> {context.get('data_as_of', 'N/D')}"),
        ("Osservazioni forecast", context.get("forecast_observations", "N/D")),
    ]
    return _table(("Voce", "Dettaglio"), rows)


def _baseline_table(context: dict) -> str:
    comparison = context.get("baseline_comparison", {})
    model = comparison.get("model", {})
    baseline = comparison.get("best_baseline", {})
    primary = context.get("primary_metric", "N/D")
    model_value = _as_float(model.get(primary))
    baseline_value = _as_float(baseline.get(primary))
    improvement = None
    if model_value is not None and baseline_value not in (None, 0.0):
        improvement = (baseline_value - model_value) / abs(baseline_value)
    dm = comparison.get("diebold_mariano", {})
    rows = [
        ("Metrica primaria", primary, "Errore/qualita' usata per decidere il confronto"),
        ("Modello", _fmt_metric(model_value), str(context.get("model", "N/D"))),
        ("Migliore baseline", _fmt_metric(baseline_value), str(comparison.get("best_baseline_name", "N/D"))),
        ("Vantaggio vs baseline", _fmt_percent(improvement), "Positivo = modello migliore della baseline"),
        ("Significativita'", _fmt_number(dm.get("p_value"), 4), str(dm.get("conclusion", "N/D"))),
        ("Information coefficient", _fmt_number(model.get("information_coefficient"), 4), "Segno e forza della relazione forecast/rendimento"),
    ]
    return _table(("Indicatore", "Valore", "Lettura business"), rows)


def _performance_table(context: dict) -> str:
    base = context.get("net_performance", {})
    rows = [
        ("Rendimento cumulato netto", _fmt_percent(base.get("cumulative_net_return")), "Risultato dopo costi stimati"),
        ("Rendimento cumulato lordo", _fmt_percent(base.get("cumulative_gross_return")), "Risultato prima dei costi"),
        ("Sharpe ratio", _fmt_number(base.get("sharpe_ratio"), 2), "Rendimento corretto per volatilita'"),
        ("Max drawdown", _fmt_percent(base.get("maximum_drawdown")), "Perdita massima dal picco"),
        ("Hit rate", _fmt_percent(base.get("hit_rate")), "Quota di periodi profittevoli"),
        ("Exposure media", _fmt_percent(base.get("exposure")), "Tempo/capitale esposto al segnale"),
        ("Turnover", _fmt_number(base.get("turnover"), 1), "Intensita' operativa e consumo di costi"),
        ("Cost drag", _fmt_percent(base.get("cost_drag")), "Erosione totale stimata dai costi"),
    ]
    return _table(("KPI", "Valore", "Interpretazione"), rows)


def _cost_table(context: dict) -> str:
    scenarios = context.get("cost_impact", {})
    rows = []
    for name in ("optimistic", "base", "stress"):
        values = scenarios.get(name, {})
        rows.append((
            name,
            _fmt_percent(values.get("cumulative_net_return")),
            _fmt_number(values.get("sharpe_ratio"), 2),
            _fmt_percent(values.get("maximum_drawdown")),
            _fmt_percent(values.get("cost_drag")),
        ))
    return _table(("Scenario costi", "Return netto", "Sharpe", "Max drawdown", "Cost drag"), rows)


def _regime_table(context: dict) -> str:
    regimes = context.get("regime", {})
    rows = []
    for name, values in sorted(regimes.items()):
        rows.append((
            name,
            values.get("count", "N/D"),
            _fmt_percent(values.get("sum")),
            _fmt_percent(values.get("mean")),
            _fmt_percent(values.get("std")),
        ))
    return _table(("Regime", "Osservazioni", "P&L netto", "Media periodo", "Volatilita'"), rows)


def _risk_table(context: dict) -> str:
    risk = context.get("risk_threshold", {})
    coverage = risk.get("conditional_coverage", {}).get("coverage", {})
    es = risk.get("expected_shortfall", {})
    evt = risk.get("evt_pot", {})
    rows = [
        (
            "VaR violations",
            f"{coverage.get('number_of_violations', 'N/D')} su {coverage.get('number_of_observations', 'N/D')}",
            f"atteso {_fmt_percent(coverage.get('expected_violation_rate'))}, osservato {_fmt_percent(coverage.get('observed_violation_rate'))}",
        ),
        (
            "Coverage test",
            str(coverage.get("result", "N/D")),
            f"p-value {_fmt_number(coverage.get('p_value'), 4)}",
        ),
        (
            "Expected Shortfall",
            _fmt_percent(es.get("mean_exceedance_loss")),
            f"ES previsto {_fmt_percent(es.get('mean_predicted_es'))}",
        ),
        (
            "EVT/POT 99%",
            _fmt_percent(evt.get("var")),
            f"ES {_fmt_percent(evt.get('expected_shortfall'))}; shape {_fmt_number(evt.get('shape'), 3)}",
        ),
    ]
    return _table(("Controllo rischio", "Valore", "Lettura"), rows)


def _gate_table(promotion: dict) -> str:
    rows = [
        (_gate_label(name), _fmt_bool(passed), _gate_business_meaning(name))
        for name, passed in promotion.get("checks", {}).items()
    ]
    return _table(("Gate", "Esito", "Perche' conta"), rows)


def _chart_section(context: dict) -> str:
    charts = context.get("charts", {})
    labels = {
        "cumulative_performance": (
            "Performance cumulata netta e lorda",
            "Mostra se il valore del segnale resta dopo i costi di esecuzione.",
        ),
        "forecast_vs_actual": (
            "Forecast vs risultato realizzato",
            "Aiuta a capire se il segnale segue il mercato o resta rumore.",
        ),
        "var_violations": (
            "VaR rolling e violazioni",
            "Evidenzia quando le perdite superano la soglia di rischio stimata.",
        ),
    }
    sections = []
    for key in ("cumulative_performance", "forecast_vs_actual", "var_violations"):
        path = charts.get(key)
        if not path:
            continue
        title, description = labels[key]
        sections.append(f"### {title}\n\n{description}\n\n![{title}]({str(path).replace(chr(92), '/')})")
    return "\n\n".join(sections) if sections else "Grafici non disponibili per questa run."


def render_business_summary(context: dict, promotion: dict) -> str:
    promoted = bool(promotion["promoted"])
    status = _status_text(promoted)
    reasons = ", ".join(_rejection_label(reason) for reason in promotion["rejection_reasons"]) or "nessuna"
    action = _business_action(promoted, context.get("task"))
    decision = (
        "La run supera i controlli configurati e puo' entrare nel perimetro operativo definito."
        if promoted
        else "La run non deve essere usata per decisioni operative o allocazione di capitale."
    )
    return f"""# Business report - Financial Time Series Platform

## Sintesi esecutiva

**Stato:** {status}

**Azione suggerita:** {action}

{decision}

**Motivi principali:** {reasons}

## Perimetro dell'analisi

{_scope_table(context)}

## Lettura investimento

{_baseline_table(context)}

## Performance economica

{_performance_table(context)}

## Sensibilita' ai costi

{_cost_table(context)}

## Performance per regime di mercato

{_regime_table(context)}

## Rischio di coda e controllo perdite

{_risk_table(context)}

## Grafici business

{_chart_section(context)}

## Gate decisionali

{_gate_table(promotion)}

## Nota per il comitato investimenti

Questo report traduce i risultati quantitativi in evidenze decisionali. Il report tecnico resta il riferimento per audit, configurazione, metriche complete e riproducibilita' della run.

> {DISCLAIMER}
"""
