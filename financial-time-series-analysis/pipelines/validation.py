"""Data-quality checks condivisi dall'ingestion."""

from __future__ import annotations

import pandas as pd


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(); reasons = pd.Series("", index=result.index, dtype="object")
    invalid_price = (result[["open", "high", "low", "close"]] <= 0).any(axis=1)
    invalid_high = result["high"] < result[["open", "close", "low"]].max(axis=1)
    invalid_low = result["low"] > result[["open", "close", "high"]].min(axis=1)
    invalid_volume = result.get("base_volume", result.get("volume", 0)) < 0
    reasons[invalid_price] += "non_positive_price;"; reasons[invalid_high] += "invalid_high;"
    reasons[invalid_low] += "invalid_low;"; reasons[invalid_volume] += "negative_volume;"
    result["quality_flag"] = "valid"; result.loc[reasons.ne(""), "quality_flag"] = "outlier"
    result["quality_reason"] = reasons.str.rstrip(";")
    return result


def freshness_status(frame: pd.DataFrame, expected_delay_seconds: int, now=None) -> dict:
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    event = pd.to_datetime(frame["event_time"], utc=True).max()
    available = pd.to_datetime(frame["available_time"], utc=True).max()
    ingested = pd.to_datetime(frame["ingested_at"], utc=True).max()
    delay = (now - available).total_seconds()
    return {"max_event_time": event, "max_available_time": available, "max_ingested_at": ingested,
            "expected_delay": expected_delay_seconds, "actual_delay": delay,
            "status": "fresh" if delay <= expected_delay_seconds else "stale"}
