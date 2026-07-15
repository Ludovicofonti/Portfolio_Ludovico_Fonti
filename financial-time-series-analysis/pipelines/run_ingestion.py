"""
pipelines/run_ingestion.py — Orchestrazione dell'ingestion dlt.

Esegue:
  1. Yahoo Finance → DuckDB (raw_finance schema)
  2. FRED macro → DuckDB (raw_finance schema)  [richiede FRED_API_KEY nell'ambiente]

Uso:
    python pipelines/run_ingestion.py
    python pipelines/run_ingestion.py --yahoo-only   # senza FRED
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

# Garantisce che la root del progetto sia nel path per import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Workaround: la cartella di progetto si chiama 'time', coincide con il modulo
# built-in Python. dlt importa un modulo con il nome della CWD per scoprire
# plugin; in Python 3.13 il modulo time non ha __file__, causando AttributeError.
# Aggiungere __file__ = None è sicuro: dlt controlla `if m_.__file__ and ...`
# e None è falsy, quindi il modulo built-in viene ignorato correttamente.
import time as _builtin_time
if not hasattr(_builtin_time, "__file__"):
    _builtin_time.__file__ = None  # type: ignore[attr-defined]

import dlt

from config import DUCKDB_PATH, RAW_DATASET, load_yaml_config
from pipelines.yahoo_source import yahoo_source


def run_yahoo(pipeline: dlt.Pipeline) -> None:
    print("\n=== Ingestion Yahoo Finance ===")
    source = yahoo_source()
    info = pipeline.run(source)
    print(info)


def run_fred(pipeline: dlt.Pipeline) -> None:
    print("\n=== Ingestion FRED Macro ===")
    # Import ritardato: fallisce se la chiave non è configurata
    try:
        from pipelines.fred_source import fred_source
        source = fred_source()
        info = pipeline.run(source)
        print(info)
    except Exception as exc:
        print(f"  [SKIP] FRED ingestion non riuscita: {exc}")
        print("  Verifica che la variabile d'ambiente FRED_API_KEY sia configurata")


def _latest_timestamp(table: str, column: str, *, symbol: str, interval: str | None = None,
                      interval_column: str = "interval", complete_only: bool = False,
                      symbol_column: str = "symbol"):
    import duckdb
    try:
        with duckdb.connect(DUCKDB_PATH, read_only=True) as connection:
            filters, values = [f'"{symbol_column}" = ?'], [symbol]
            if interval is not None:
                filters.append(f'"{interval_column}" = ?')
                values.append(interval)
            if complete_only:
                filters.append("close_time <= ingested_at")
            return connection.execute(
                f'SELECT max("{column}") FROM "{RAW_DATASET}"."{table}" WHERE ' + " AND ".join(filters),
                values,
            ).fetchone()[0]
    except duckdb.Error:
        return None


def _next_timestamp(value):
    if value is None:
        return None
    stamp = value if getattr(value, "tzinfo", None) else value.replace(tzinfo=timezone.utc)
    return stamp + timedelta(milliseconds=1)


def run_crypto(pipeline: dlt.Pipeline, symbols: list[str], intervals: list[str], derivatives: bool = True,
               orderbook: bool = True, start_time: datetime | None = None) -> None:
    """Ingestion incrementale esplicita delle fonti exchange gratuite."""
    from pipelines.binance_spot_source import binance_orderbook_snapshot, binance_spot_ohlcv
    from pipelines.binance_futures_source import (
        binance_basis_metrics,
        binance_funding_rates,
        binance_long_short_ratios,
        binance_open_interest,
        binance_taker_volume_ratios,
    )
    print("\n=== Ingestion Binance Crypto ===")
    for symbol in symbols:
        for interval in intervals:
            latest = _next_timestamp(_latest_timestamp(
                "exchange_ohlcv", "close_time", symbol=symbol, interval=interval,
                complete_only=True,
            ))
            print(pipeline.run(binance_spot_ohlcv(symbol, interval, start_time=latest or start_time)))
        if derivatives:
            funding_start = _next_timestamp(_latest_timestamp(
                "funding_rates", "funding_time", symbol=symbol
            ))
            print(pipeline.run(binance_funding_rates(symbol, start_time=funding_start or start_time)))
            # OI viene normalizzato a 1h e riutilizzato via ASOF anche da 4h/1d.
            oi_period = "1h"
            oi_start = _next_timestamp(_latest_timestamp(
                "open_interest", "timestamp", symbol=symbol
            ))
            if oi_start is None:
                provider_limit = datetime.now(timezone.utc) - timedelta(days=29)
                oi_start = max(start_time or provider_limit, provider_limit)
            print(pipeline.run(binance_open_interest(symbol, period=oi_period, start_time=oi_start or start_time)))
            provider_limit = datetime.now(timezone.utc) - timedelta(days=29)
            for table, resource in (
                ("long_short_ratios", binance_long_short_ratios),
                ("taker_volume_ratios", binance_taker_volume_ratios),
                ("basis_metrics", binance_basis_metrics),
            ):
                metric_start = _next_timestamp(_latest_timestamp(
                    table, "timestamp", symbol=symbol, interval="1h", interval_column="period"
                ))
                metric_start = metric_start or max(start_time or provider_limit, provider_limit)
                print(pipeline.run(resource(symbol, period="1h", start_time=metric_start)))
        if orderbook:
            print(pipeline.run(binance_orderbook_snapshot(symbol)))


def run_onchain(pipeline: dlt.Pipeline, symbols: list[str], start_time: datetime) -> None:
    """Ingest Coin Metrics Community data using the configured symbol mapping."""
    from pipelines.coinmetrics_source import coinmetrics_asset_metrics

    cfg = load_yaml_config("data_sources.yml")["sources"]["onchain"]
    if not cfg.get("enabled", False):
        return
    print("\n=== Ingestion Coin Metrics On-chain ===")
    frequency = str(cfg.get("frequency", "1d"))
    metrics = list(cfg.get("metrics", []))
    mapped_assets = {
        cfg.get("assets", {}).get(symbol)
        for symbol in symbols
        if cfg.get("assets", {}).get(symbol)
    }
    for asset in sorted(mapped_assets):
        for metric in metrics:
            cursor = _next_timestamp(_latest_timestamp(
                "onchain_metrics", "observation_time", symbol=asset,
                interval=metric, interval_column="metric", symbol_column="asset",
            ))
            resource = coinmetrics_asset_metrics(
                [asset], [metric], cursor or start_time, frequency=frequency
            )
            try:
                print(pipeline.run(resource))
            except Exception as exc:
                print(f"  [WARN] Coin Metrics {asset}/{metric} non disponibile: {exc}")


def main(yahoo_only: bool = False, crypto_only: bool = False, crypto: bool = False,
         symbols: list[str] | None = None, intervals: list[str] | None = None,
         start_time: datetime | None = None, orderbook: bool = True,
         onchain: bool = True) -> None:
    import duckdb as _duckdb_mod
    pipeline = dlt.pipeline(
        pipeline_name="finance_ingestion",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name=RAW_DATASET,
    )

    if not crypto_only:
        run_yahoo(pipeline)

    if not yahoo_only and not crypto_only:
        run_fred(pipeline)
    if crypto or crypto_only:
        if start_time is None:
            days = int(load_yaml_config("data_sources.yml")["sources"]["binance_spot"].get("initial_backfill_days", 365))
            start_time = datetime.now(timezone.utc) - timedelta(days=days)
        selected_symbols = symbols or ["BTCUSDT", "ETHUSDT"]
        run_crypto(pipeline, selected_symbols, intervals or ["1h", "4h", "1d"],
                   start_time=start_time, orderbook=orderbook)
        if onchain:
            run_onchain(pipeline, selected_symbols, start_time)

    print("\n=== Verifica DuckDB ===")
    import duckdb
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    tables = con.execute(
        f"SELECT table_name FROM information_schema.tables WHERE table_schema='{RAW_DATASET}'"
    ).fetchall()
    print(f"Tabelle in '{RAW_DATASET}': {[t[0] for t in tables]}")

    # Conta righe per tabella
    for (tbl,) in tables:
        n = con.execute(f'SELECT COUNT(*) FROM "{RAW_DATASET}"."{tbl}"').fetchone()[0]
        print(f"  {tbl}: {n} righe")
    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yahoo-only", action="store_true",
                        help="Esegui solo Yahoo Finance (senza FRED)")
    parser.add_argument("--crypto", action="store_true", help="Aggiungi Binance spot e derivati")
    parser.add_argument("--crypto-only", action="store_true", help="Esegui soltanto Binance")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT", help="Simboli Binance separati da virgola")
    parser.add_argument("--intervals", default="1h,4h,1d", help="Intervalli Binance separati da virgola")
    parser.add_argument("--start", help="Backfill iniziale ISO-8601; ignorato se esiste già un cursore")
    parser.add_argument("--no-orderbook", action="store_true", help="Non acquisire lo snapshot order book")
    parser.add_argument("--no-onchain", action="store_true", help="Non acquisire le metriche Coin Metrics")
    args = parser.parse_args()
    main(yahoo_only=args.yahoo_only, crypto_only=args.crypto_only, crypto=args.crypto,
         symbols=args.symbols.split(","), intervals=args.intervals.split(","),
         start_time=datetime.fromisoformat(args.start).astimezone(timezone.utc) if args.start else None,
         orderbook=not args.no_orderbook, onchain=not args.no_onchain)
