"""Coin Metrics Community API v4 on-chain source."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Iterable

import dlt
import pandas as pd

from config import load_yaml_config
from pipelines.http import get_json, retry_session
from pipelines.onchain_source import OnChainSource


def _utc(value: datetime | str) -> datetime:
    stamp = pd.Timestamp(value)
    stamp = stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
    return stamp.to_pydatetime()


def _availability_time(observation_time: datetime, frequency: str) -> datetime:
    amount = int(frequency[:-1] or 1)
    if frequency.endswith("d"):
        return observation_time + timedelta(days=amount)
    if frequency.endswith("h"):
        return observation_time + timedelta(hours=amount)
    return observation_time


class CoinMetricsCommunitySource(OnChainSource):
    """Paginated client for the public asset metrics endpoint."""

    def __init__(self, config: dict | None = None, session=None):
        self.config = config or load_yaml_config("data_sources.yml")["sources"]["onchain"]
        self.base_url = self.config["base_url"].rstrip("/")
        self.session = session or retry_session(
            attempts=int(self.config.get("retry_attempts", 5)),
            backoff_seconds=float(self.config.get("retry_backoff_seconds", 1.0)),
        )
        self.api_key = os.getenv(str(self.config.get("api_key_env", "COINMETRICS_API_KEY")))

    def fetch(
        self,
        network: str,
        metric: str,
        start_time: datetime,
        end_time: datetime,
        frequency: str,
    ) -> list[dict]:
        params = {
            "assets": network.lower(),
            "metrics": metric,
            "frequency": frequency,
            "start_time": _utc(start_time).isoformat().replace("+00:00", "Z"),
            "end_time": _utc(end_time).isoformat().replace("+00:00", "Z"),
            "page_size": int(self.config.get("page_size", 10000)),
        }
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{self.base_url}/timeseries/asset-metrics"
        ingested_at = datetime.now(timezone.utc)
        records: list[dict] = []
        while url:
            payload = get_json(self.session, url, params=params)
            for row in payload.get("data", []):
                value = row.get(metric)
                if value is None:
                    continue
                observation_time = _utc(row["time"])
                records.append({
                    "provider": "coinmetrics_community",
                    "asset": str(row.get("asset", network)).lower(),
                    "metric": metric,
                    "frequency": frequency,
                    "observation_time": observation_time,
                    "value": float(value),
                    "available_time": _availability_time(observation_time, frequency),
                    "ingested_at": ingested_at,
                    "quality_flag": "valid",
                })
            url = payload.get("next_page_url")
            params = {}
        return records


@dlt.resource(
    name="onchain_metrics",
    write_disposition="merge",
    primary_key=("provider", "asset", "metric", "frequency", "observation_time"),
)
def coinmetrics_asset_metrics(
    assets: Iterable[str],
    metrics: Iterable[str],
    start_time: datetime,
    end_time: datetime | None = None,
    frequency: str = "1d",
):
    client = CoinMetricsCommunitySource()
    end_time = end_time or datetime.now(timezone.utc)
    for asset in assets:
        for metric in metrics:
            yield from client.fetch(asset, metric, start_time, end_time, frequency)
