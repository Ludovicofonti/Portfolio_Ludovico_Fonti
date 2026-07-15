"""Renderer Markdown deterministico delle sezioni metodologiche obbligatorie."""

from __future__ import annotations

import json
import math

from .disclaimers import DISCLAIMER


SECTIONS = (
    "Data lineage", "Qualità e freshness dei dati", "Descrizione del target",
    "Feature disponibili al forecast origin", "Baseline", "Configurazione walk-forward",
    "Risultati per fold", "Significatività del confronto", "Performance per regime",
    "Performance dopo i costi", "VaR backtesting", "Expected Shortfall",
    "Sensitivity analysis", "Grafici e artefatti", "Limiti", "Condizioni di rifiuto del modello",
)


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _render(value) -> str:
    if value is None:
        return "Non disponibile per questa run."
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list, tuple)):
        return "~~~json\n" + json.dumps(
            _json_safe(value), indent=2, sort_keys=True, default=str, ensure_ascii=False
        ) + "\n~~~"
    return str(value)


def render_technical_report(context: dict) -> str:
    blocks = ["# Report tecnico riproducibile"]
    for section in SECTIONS:
        blocks.extend([f"## {section}", _render(context.get(section))])
    blocks.append(f"> {DISCLAIMER}")
    return "\n\n".join(blocks) + "\n"
