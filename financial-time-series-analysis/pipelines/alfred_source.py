"""Vintage macro point-in-time tramite ALFRED/FRED all releases."""

from datetime import datetime, timezone

import pandas as pd
from fredapi import Fred


def fetch_alfred_vintages(fred: Fred, series_id: str, start_date: str) -> list[dict]:
    releases = fred.get_series_all_releases(series_id)
    releases = releases[releases["date"] >= pd.Timestamp(start_date)]
    ingested_at = datetime.now(timezone.utc)
    records = []
    for row in releases.itertuples(index=False):
        vintage = pd.Timestamp(row.realtime_start)
        vintage = vintage.tz_localize("UTC") if vintage.tzinfo is None else vintage.tz_convert("UTC")
        records.append({"series_id": series_id, "observation_date": pd.Timestamp(row.date).date(),
                        "value": float(row.value), "release_date": vintage, "vintage_date": vintage,
                        "available_time": vintage, "ingested_at": ingested_at})
    return records
