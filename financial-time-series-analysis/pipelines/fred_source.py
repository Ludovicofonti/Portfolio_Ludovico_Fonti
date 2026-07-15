"""
pipelines/fred_source.py — dlt source per dati macro FRED.

Legge la chiave API esclusivamente dalla variabile d'ambiente FRED_API_KEY.
Il valore non viene salvato nel repository né nei file di configurazione.

Ottieni la chiave gratuita su: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import os
from datetime import date
from typing import Iterator

import dlt
import pandas as pd
from fredapi import Fred

from config import FRED_SERIES, INGESTION_START_DATE


def _fetch_series(
    fred: Fred,
    series_id: str,
    description: str,
    last_date: date | None,
    start_date: str,
) -> Iterator[dict]:
    """Scarica una serie FRED e produce righe dict."""
    fetch_start = last_date.isoformat() if last_date else start_date
    try:
        s: pd.Series = fred.get_series(series_id, observation_start=fetch_start)
    except Exception as exc:
        print(f"  [WARN] Impossibile scaricare {series_id}: {exc}")
        return

    for obs_date, value in s.items():
        if pd.isna(value):
            continue
        yield {
            "series_id": series_id,
            "description": description,
            "date": obs_date.date() if hasattr(obs_date, "date") else obs_date,
            "value": float(value),
        }


@dlt.source(name="fred_source")
def fred_source(api_key: str | None = None, start_date: str = INGESTION_START_DATE):
    """Source dlt; reads FRED_API_KEY without persisting the secret."""
    resolved_key = api_key or os.getenv("FRED_API_KEY")
    if not resolved_key:
        raise RuntimeError("FRED_API_KEY non configurata; ingestion macro disabilitata")
    fred = Fred(api_key=resolved_key)

    def _make_resource(series_id: str, description: str):
        @dlt.resource(
            name=f"macro_{series_id.lower()}",
            write_disposition="merge",
            primary_key=["series_id", "date"],
        )
        def resource(
            date_cursor: dlt.sources.incremental[date] = dlt.sources.incremental(
                "date", initial_value=None
            ),
        ):
            last = date_cursor.last_value
            yield from _fetch_series(fred, series_id, description, last, start_date)

        return resource

    for sid, desc in FRED_SERIES.items():
        yield _make_resource(sid, desc)
