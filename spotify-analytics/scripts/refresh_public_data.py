import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime

import requests
from google.cloud import bigquery

try:
    from scripts.bigquery_config import BigQueryConfig
    from scripts.bigquery_loader import (
        ensure_datasets,
        ensure_metadata_cache_table,
        load_metadata_cache,
        load_snapshot_to_bigquery,
    )
    from scripts.spotify_api import (
        SpotifyRequestStats,
        fetch_italy_daily_chart,
        get_access_token,
        get_track_details,
    )
except ModuleNotFoundError:  # Direct execution: python scripts/refresh_public_data.py
    from bigquery_config import BigQueryConfig
    from bigquery_loader import (
        ensure_datasets,
        ensure_metadata_cache_table,
        load_metadata_cache,
        load_snapshot_to_bigquery,
    )
    from spotify_api import (
        SpotifyRequestStats,
        fetch_italy_daily_chart,
        get_access_token,
        get_track_details,
    )

MIN_CHART_ROWS = 190
MIN_METADATA_MATCH_RATE = 0.95


@dataclass(frozen=True)
class SpotifySnapshot:
    chart_rows: list[dict]
    track_details: dict[str, dict]
    new_track_details: dict[str, dict]
    metrics: dict
    failures: list[dict]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect, validate and load the Spotify Italy chart into BigQuery."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only enrich the first N chart rows without publishing. Intended for smoke tests.",
    )
    parser.add_argument("--min-chart-rows", type=int, default=MIN_CHART_ROWS)
    parser.add_argument("--min-match-rate", type=float, default=MIN_METADATA_MATCH_RATE)
    return parser.parse_args()


def enrich_chart(chart_rows, token, stats=None, failures=None):
    """Enrich chart rows deterministically via GET /tracks/{track_id}."""
    track_details = {}
    stats = stats or SpotifyRequestStats()
    failures = failures if failures is not None else []
    for row in chart_rows:
        try:
            track = get_track_details(
                token,
                row["track_id"],
                market=row["country"],
                stats=stats,
            )
        except requests.HTTPError as exc:
            response = exc.response
            failures.append(
                {
                    "chart_date": row["chart_date"],
                    "track_id": row["track_id"],
                    "chart_rank": row["rank"],
                    "reason": "spotify_http_{}".format(
                        response.status_code if response is not None else "unknown"
                    ),
                }
            )
            continue
        except (ValueError, requests.RequestException) as exc:
            failures.append(
                {
                    "chart_date": row["chart_date"],
                    "track_id": row["track_id"],
                    "chart_rank": row["rank"],
                    "reason": type(exc).__name__,
                }
            )
            continue
        if track:
            track_details[row["track_id"]] = track
    return track_details


def validate_chart_rows(chart_rows, min_rows=MIN_CHART_ROWS):
    if len(chart_rows) < min_rows:
        raise ValueError(
            f"Chart health gate failed: {len(chart_rows)} rows, expected at least {min_rows}"
        )

    required = ("chart_date", "country", "rank", "track_id")
    missing = [
        row.get("rank")
        for row in chart_rows
        if any(row.get(column) in (None, "") for column in required)
    ]
    if missing:
        raise ValueError(
            f"Chart health gate failed: {len(missing)} rows have missing required values"
        )

    grains = {(row["chart_date"], row["country"], row["track_id"]) for row in chart_rows}
    ranks = {(row["chart_date"], row["country"], row["rank"]) for row in chart_rows}
    if len(grains) != len(chart_rows):
        raise ValueError("Chart health gate failed: duplicate chart_date/country/track_id")
    if len(ranks) != len(chart_rows):
        raise ValueError("Chart health gate failed: duplicate chart_date/country/rank")
    if any(not 1 <= row["rank"] <= 200 for row in chart_rows):
        raise ValueError("Chart health gate failed: rank outside the 1-200 range")


def collect_snapshot(
    client,
    config,
    client_id,
    client_secret,
    limit=None,
    min_chart_rows=MIN_CHART_ROWS,
    min_match_rate=MIN_METADATA_MATCH_RATE,
):
    started_at = datetime.now(UTC)
    chart_rows = fetch_italy_daily_chart()
    if limit:
        chart_rows = chart_rows[:limit]
    validate_chart_rows(chart_rows, min_rows=1 if limit else min_chart_rows)

    chart_date = chart_rows[0]["chart_date"]
    expected_track_ids = {row["track_id"] for row in chart_rows}
    cached_track_details = load_metadata_cache(client, config, expected_track_ids)
    missing_track_ids = expected_track_ids.difference(cached_track_details)
    failures = []
    stats = SpotifyRequestStats()
    new_track_details = {}
    if missing_track_ids:
        token = get_access_token(client_id, client_secret)
        missing_rows = [row for row in chart_rows if row["track_id"] in missing_track_ids]
        new_track_details = enrich_chart(
            missing_rows,
            token,
            stats=stats,
            failures=failures,
        )

    all_track_details = {**cached_track_details, **new_track_details}
    current_track_details = {
        track_id: all_track_details[track_id]
        for track_id in expected_track_ids
        if track_id in all_track_details
    }
    match_rate = len(current_track_details) / len(chart_rows)
    if match_rate < min_match_rate:
        raise ValueError(
            f"Metadata health gate failed: {match_rate:.1%} matched, "
            f"expected at least {min_match_rate:.1%}"
        )

    finished_at = datetime.now(UTC)
    metrics = {
        "run_id": started_at.strftime("%Y%m%dT%H%M%SZ"),
        "run_started_at": started_at.isoformat(),
        "chart_date": chart_date,
        "chart_rows": len(chart_rows),
        "matched_tracks": len(current_track_details),
        "match_rate": match_rate,
        "duplicate_tracks": len(chart_rows) - len(expected_track_ids),
        "missing_streams": sum(row.get("streams") is None for row in chart_rows),
        "spotify_requests": stats.requests,
        "spotify_retries": stats.retries,
        "spotify_429_responses": stats.rate_limited,
        "pipeline_duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "pipeline_status": "fresh",
        "generated_at": finished_at.isoformat(),
    }
    return SpotifySnapshot(
        chart_rows=chart_rows,
        track_details=current_track_details,
        new_track_details=new_track_details,
        metrics=metrics,
        failures=failures,
    )


def main():
    args = parse_args()
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required.")

    config = BigQueryConfig.from_env()
    client = bigquery.Client(project=config.project, location=config.location)
    ensure_datasets(client, config)
    ensure_metadata_cache_table(client, config)
    snapshot = collect_snapshot(
        client,
        config,
        client_id,
        client_secret,
        limit=args.limit,
        min_chart_rows=args.min_chart_rows,
        min_match_rate=args.min_match_rate,
    )

    summary = {
        "chart_date": snapshot.metrics["chart_date"],
        "dry_run": bool(args.limit),
        "chart_rows": snapshot.metrics["chart_rows"],
        "matched_tracks": snapshot.metrics["matched_tracks"],
        "metadata_match_rate": snapshot.metrics["match_rate"],
        "spotify_requests": snapshot.metrics["spotify_requests"],
        "spotify_retries": snapshot.metrics["spotify_retries"],
        "spotify_429_responses": snapshot.metrics["spotify_429_responses"],
        "generated_at": snapshot.metrics["generated_at"],
    }
    if not args.limit:
        summary["bigquery"] = load_snapshot_to_bigquery(
            client,
            config,
            snapshot.chart_rows,
            snapshot.track_details,
            snapshot.new_track_details,
            snapshot.metrics,
            snapshot.failures,
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
