"""Ingestion gratuita Binance spot: OHLCV e snapshot order book aggregato."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import dlt
import requests

from pipelines.http import get_json, retry_session

BINANCE_SPOT_URL = "https://api.binance.com"


def _utc_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def fetch_ohlcv(symbol: str, interval: str, start_time: datetime | None = None,
                end_time: datetime | None = None, limit: int = 1000,
                session: requests.Session | None = None) -> Iterator[dict]:
    """Pagina le klines senza tick data e conserva timestamp di disponibilità."""
    client = session or retry_session()
    cursor = int(start_time.timestamp() * 1000) if start_time else None
    end_ms = int(end_time.timestamp() * 1000) if end_time else None
    while True:
        params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
        if cursor is not None:
            params["startTime"] = cursor
        if end_ms is not None:
            params["endTime"] = end_ms
        rows = get_json(client, f"{BINANCE_SPOT_URL}/api/v3/klines", params=params)
        if not rows:
            break
        ingested_at = datetime.now(timezone.utc)
        for row in rows:
            close_time = _utc_ms(row[6])
            if close_time > ingested_at:
                continue
            yield {"exchange": "binance", "symbol": symbol, "interval": interval,
                   "open_time": _utc_ms(row[0]), "close_time": close_time,
                   "open": float(row[1]), "high": float(row[2]), "low": float(row[3]), "close": float(row[4]),
                   "base_volume": float(row[5]), "quote_volume": float(row[7]),
                   "number_of_trades": int(row[8]), "taker_buy_base_volume": float(row[9]),
                   "taker_buy_quote_volume": float(row[10]), "available_time": _utc_ms(row[6]),
                   "source": "binance_api", "ingested_at": ingested_at, "quality_flag": "valid"}
        next_cursor = int(rows[-1][6]) + 1
        if len(rows) < params["limit"] or (end_ms is not None and next_cursor > end_ms):
            break
        cursor = next_cursor


def fetch_orderbook_snapshot(symbol: str, depth_limit: int = 100,
                             session: requests.Session | None = None) -> dict:
    client = session or retry_session()
    book = get_json(client, f"{BINANCE_SPOT_URL}/api/v3/depth",
                    params={"symbol": symbol, "limit": depth_limit})
    bids = [(float(p), float(q)) for p, q in book["bids"]]; asks = [(float(p), float(q)) for p, q in book["asks"]]
    best_bid, best_ask = bids[0][0], asks[0][0]; mid = (best_bid + best_ask) / 2
    bid_depth = sum(p * q for p, q in bids if p >= mid * 0.99)
    ask_depth = sum(p * q for p, q in asks if p <= mid * 1.01)
    total_depth = bid_depth + ask_depth
    now = datetime.now(timezone.utc)
    return {"exchange": "binance", "symbol": symbol, "best_bid": best_bid, "best_ask": best_ask,
            "mid_price": mid, "spread": best_ask - best_bid, "spread_bps": (best_ask - best_bid) / mid * 10_000,
            "bid_depth_1pct": bid_depth, "ask_depth_1pct": ask_depth,
            "order_book_imbalance": (bid_depth - ask_depth) / total_depth if total_depth else 0.0,
            "snapshot_time": now, "available_time": now, "ingested_at": now, "source": "binance_api"}


@dlt.resource(name="exchange_ohlcv", write_disposition="merge",
              primary_key=["exchange", "symbol", "interval", "open_time"])
def binance_spot_ohlcv(symbol: str, interval: str = "1h", start_time: datetime | None = None):
    yield from fetch_ohlcv(symbol, interval, start_time=start_time)


@dlt.resource(name="exchange_orderbook", write_disposition="merge",
              primary_key=["exchange", "symbol", "snapshot_time"])
def binance_orderbook_snapshot(symbol: str, depth_limit: int = 100):
    yield fetch_orderbook_snapshot(symbol, depth_limit)
