"""Ingestion Binance USD-M: funding, open interest e basis-ready prices."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import dlt
import requests

from pipelines.http import get_json, retry_session

BINANCE_FUTURES_URL = "https://fapi.binance.com"


def _utc_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def fetch_funding_rates(symbol: str, start_time: datetime | None = None,
                        session: requests.Session | None = None) -> Iterator[dict]:
    client = session or retry_session(); cursor = int(start_time.timestamp() * 1000) if start_time else None
    while True:
        params = {"symbol": symbol, "limit": 1000}
        if cursor is not None: params["startTime"] = cursor
        rows = get_json(client, f"{BINANCE_FUTURES_URL}/fapi/v1/fundingRate", params=params)
        ingested_at = datetime.now(timezone.utc)
        if not rows: break
        for row in rows:
            available = _utc_ms(int(row["fundingTime"]))
            yield {"exchange": "binance", "symbol": symbol, "funding_time": available,
                   "funding_rate": float(row["fundingRate"]), "mark_price": float(row.get("markPrice", "nan")),
                   "available_time": available, "ingested_at": ingested_at}
        next_cursor = int(rows[-1]["fundingTime"]) + 1
        if len(rows) < 1000: break
        cursor = next_cursor


def fetch_open_interest(symbol: str, period: str = "1h", start_time: datetime | None = None,
                        session: requests.Session | None = None) -> Iterator[dict]:
    client = session or retry_session()
    cursor = int(start_time.timestamp() * 1000) if start_time else None
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    while True:
        params = {"symbol": symbol, "period": period, "limit": 500, "endTime": end_ms}
        if cursor is not None:
            params["startTime"] = cursor
        rows = get_json(client, f"{BINANCE_FUTURES_URL}/futures/data/openInterestHist", params=params)
        if not rows:
            break
        ingested_at = datetime.now(timezone.utc)
        for row in rows:
            timestamp = _utc_ms(int(row["timestamp"]))
            yield {"exchange": "binance", "symbol": symbol, "timestamp": timestamp,
                   "open_interest": float(row["sumOpenInterest"]), "open_interest_value": float(row["sumOpenInterestValue"]),
                   "available_time": timestamp, "ingested_at": ingested_at}
        next_cursor = int(rows[-1]["timestamp"]) + 1
        if len(rows) < 500 or next_cursor > end_ms:
            break
        cursor = next_cursor


def _fetch_ratio_series(endpoint: str, symbol: str, period: str, start_time: datetime | None,
                        session: requests.Session | None = None) -> Iterator[tuple[dict, datetime]]:
    client = session or retry_session()
    cursor = int(start_time.timestamp() * 1000) if start_time else None
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    while True:
        params = {"symbol": symbol, "period": period, "limit": 500, "endTime": end_ms}
        if cursor is not None:
            params["startTime"] = cursor
        rows = get_json(client, f"{BINANCE_FUTURES_URL}{endpoint}", params=params)
        if not rows:
            break
        ingested_at = datetime.now(timezone.utc)
        for row in rows:
            yield row, ingested_at
        next_cursor = int(rows[-1]["timestamp"]) + 1
        if len(rows) < 500 or next_cursor > end_ms:
            break
        cursor = next_cursor


def fetch_long_short_ratios(symbol: str, period: str = "1h", start_time: datetime | None = None,
                            session: requests.Session | None = None) -> Iterator[dict]:
    for row, ingested_at in _fetch_ratio_series(
        "/futures/data/globalLongShortAccountRatio", symbol, period, start_time, session
    ):
        timestamp = _utc_ms(int(row["timestamp"]))
        yield {
            "exchange": "binance", "symbol": symbol, "period": period, "timestamp": timestamp,
            "long_short_ratio": float(row["longShortRatio"]),
            "long_account_share": float(row["longAccount"]),
            "short_account_share": float(row["shortAccount"]),
            "available_time": timestamp, "ingested_at": ingested_at,
        }


def fetch_taker_volume_ratios(symbol: str, period: str = "1h", start_time: datetime | None = None,
                              session: requests.Session | None = None) -> Iterator[dict]:
    for row, ingested_at in _fetch_ratio_series(
        "/futures/data/takerlongshortRatio", symbol, period, start_time, session
    ):
        timestamp = _utc_ms(int(row["timestamp"]))
        yield {
            "exchange": "binance", "symbol": symbol, "period": period, "timestamp": timestamp,
            "buy_sell_ratio": float(row["buySellRatio"]),
            "buy_volume": float(row["buyVol"]), "sell_volume": float(row["sellVol"]),
            "available_time": timestamp, "ingested_at": ingested_at,
        }


def fetch_basis_metrics(symbol: str, period: str = "1h", start_time: datetime | None = None,
                        session: requests.Session | None = None) -> Iterator[dict]:
    client = session or retry_session()
    cursor = int(start_time.timestamp() * 1000) if start_time else None
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    while True:
        params = {
            "pair": symbol, "contractType": "PERPETUAL", "period": period,
            "limit": 500, "endTime": end_ms,
        }
        if cursor is not None:
            params["startTime"] = cursor
        rows = get_json(client, f"{BINANCE_FUTURES_URL}/futures/data/basis", params=params)
        if not rows:
            break
        ingested_at = datetime.now(timezone.utc)
        for row in rows:
            timestamp = _utc_ms(int(row["timestamp"]))
            yield {
                "exchange": "binance", "symbol": symbol, "period": period, "timestamp": timestamp,
                "index_price": float(row["indexPrice"]), "futures_price": float(row["futuresPrice"]),
                "basis": float(row["basis"]), "basis_rate": float(row["basisRate"]),
                "available_time": timestamp, "ingested_at": ingested_at,
            }
        next_cursor = int(rows[-1]["timestamp"]) + 1
        if len(rows) < 500 or next_cursor > end_ms:
            break
        cursor = next_cursor


@dlt.resource(name="funding_rates", write_disposition="merge",
              primary_key=["exchange", "symbol", "funding_time"])
def binance_funding_rates(symbol: str, start_time: datetime | None = None):
    yield from fetch_funding_rates(symbol, start_time)


@dlt.resource(name="open_interest", write_disposition="merge",
              primary_key=["exchange", "symbol", "timestamp"])
def binance_open_interest(symbol: str, period: str = "1h", start_time: datetime | None = None):
    yield from fetch_open_interest(symbol, period, start_time)


@dlt.resource(name="long_short_ratios", write_disposition="merge",
              primary_key=["exchange", "symbol", "period", "timestamp"])
def binance_long_short_ratios(symbol: str, period: str = "1h", start_time: datetime | None = None):
    yield from fetch_long_short_ratios(symbol, period, start_time)


@dlt.resource(name="taker_volume_ratios", write_disposition="merge",
              primary_key=["exchange", "symbol", "period", "timestamp"])
def binance_taker_volume_ratios(symbol: str, period: str = "1h", start_time: datetime | None = None):
    yield from fetch_taker_volume_ratios(symbol, period, start_time)


@dlt.resource(name="basis_metrics", write_disposition="merge",
              primary_key=["exchange", "symbol", "period", "timestamp"])
def binance_basis_metrics(symbol: str, period: str = "1h", start_time: datetime | None = None):
    yield from fetch_basis_metrics(symbol, period, start_time)
