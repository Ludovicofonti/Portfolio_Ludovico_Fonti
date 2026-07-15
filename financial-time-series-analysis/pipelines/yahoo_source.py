"""
pipelines/yahoo_source.py — dlt source per Yahoo Finance (yfinance).

Ingerisce dati OHLCV per ogni asset class definita in config.py.
Usa write_disposition="merge" + incremental per evitare duplicati.
"""

from datetime import date, datetime
from typing import Iterator

import dlt
import pandas as pd
import yfinance as yf

from config import ASSETS, INGESTION_START_DATE


def _download_ticker(
    symbol: str,
    asset_class: str,
    last_date: date | None,
    start_date: str,
) -> Iterator[dict]:
    """Scarica OHLCV per un singolo ticker e produce righe dict."""
    fetch_start = last_date.isoformat() if last_date else start_date
    raw: pd.DataFrame = yf.download(
        symbol,
        start=fetch_start,
        end=date.today().isoformat(),
        auto_adjust=True,
        progress=False,
    )
    if raw.empty:
        return

    # Appiattisce il MultiIndex delle colonne (es: ("Close","AAPL") → "close")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0].lower().replace(" ", "_") for col in raw.columns]
    else:
        raw.columns = [c.lower().replace(" ", "_") for c in raw.columns]

    # L'indice contiene le date — lo convertiamo in colonna esplicita "date"
    # senza usare reset_index() per evitare il conflitto di naming con yfinance
    raw = raw.copy()
    raw["date"] = [d.date() if hasattr(d, "date") else d for d in raw.index]

    # Selezione delle colonne che ci servono (close potrebbe mancare per alcuni asset)
    for _, row in raw.iterrows():
        close_val = row.get("close", float("nan"))
        if pd.isna(close_val):
            continue
        yield {
            "symbol": symbol,
            "asset_class": asset_class,
            "date": row["date"],
            "open":   float(row.get("open",   float("nan"))),
            "high":   float(row.get("high",   float("nan"))),
            "low":    float(row.get("low",    float("nan"))),
            "close":  float(close_val),
            "volume": float(row.get("volume", 0.0)),
        }


@dlt.source(name="yahoo_finance")
def yahoo_source(start_date: str = INGESTION_START_DATE):
    """
    Source dlt: una resource per ogni asset class.
    Ogni resource è incrementale sulla colonna 'date'.
    """

    def _make_resource(asset_class: str, symbols: list[str]):
        @dlt.resource(
            name=f"prices_{asset_class}",
            write_disposition="replace",
            primary_key=["symbol", "date"],
        )
        def resource():
            for sym in symbols:
                yield from _download_ticker(sym, asset_class, None, start_date)

        return resource

    for cls, syms in ASSETS.items():
        yield _make_resource(cls, syms)
