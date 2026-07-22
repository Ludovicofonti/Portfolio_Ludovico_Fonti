import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from spotify_api import (
    SpotifyRequestStats,
    fetch_italy_daily_chart,
    get_access_token,
    get_track_details,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
CACHE_PATH = PROJECT_DIR / "data" / "cache" / "spotify_tracks.json"
QUALITY_DIR = PROJECT_DIR / "data" / "quality"
MIN_CHART_ROWS = 190
MIN_METADATA_MATCH_RATE = 0.95


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect and validate the Spotify Italy chart for BigQuery."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only enrich the first N chart rows. Intended for smoke tests.",
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


def _atomic_json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    temporary_path.replace(path)


def load_metadata_cache():
    if not CACHE_PATH.exists():
        return {}
    with CACHE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_pipeline_quality(metrics, failures):
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    history_path = QUALITY_DIR / "pipeline_runs.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(metrics, ensure_ascii=False) + "\n")
    _atomic_json_write(QUALITY_DIR / "latest_run.json", metrics)
    _atomic_json_write(QUALITY_DIR / "unmatched_tracks.json", failures)


def load_raw_track_details(chart_date):
    raw_details_path = RAW_DIR / f"italy_daily_track_details_{chart_date}.json"
    if not raw_details_path.exists():
        return None

    with raw_details_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_cached_track_details():
    cached_details = {}
    for raw_details_path in sorted(RAW_DIR.glob("italy_daily_track_details_*.json")):
        with raw_details_path.open("r", encoding="utf-8") as handle:
            cached_details.update(json.load(handle))
    return cached_details or None


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Cannot write empty dataset: {path.name}")

    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(path)


def write_raw_snapshot(chart_rows, track_details):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    chart_date = chart_rows[0]["chart_date"]
    raw_chart_path = RAW_DIR / f"italy_daily_chart_{chart_date}.csv"
    raw_details_path = RAW_DIR / f"italy_daily_track_details_{chart_date}.json"

    raw_chart_rows = []
    for row in chart_rows:
        serialized = row.copy()
        serialized["artist_ids"] = json.dumps(row["artist_ids"], ensure_ascii=False)
        serialized["artist_names"] = json.dumps(row["artist_names"], ensure_ascii=False)
        raw_chart_rows.append(serialized)

    write_csv(raw_chart_path, raw_chart_rows)
    _atomic_json_write(raw_details_path, track_details)


def main():
    args = parse_args()
    started_at = datetime.now().astimezone()
    load_dotenv(PROJECT_DIR / ".env")

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required.")

    chart_rows = fetch_italy_daily_chart()
    if args.limit:
        chart_rows = chart_rows[: args.limit]
    validate_chart_rows(chart_rows, min_rows=1 if args.limit else args.min_chart_rows)

    chart_date = chart_rows[0]["chart_date"]
    track_details = load_metadata_cache()
    track_details.update(load_cached_track_details() or {})
    track_details.update(load_raw_track_details(chart_date) or {})

    expected_track_ids = {row["track_id"] for row in chart_rows}
    missing_track_ids = expected_track_ids.difference(track_details)
    failures = []
    stats = SpotifyRequestStats()
    if missing_track_ids:
        token = get_access_token(client_id, client_secret)
        missing_rows = [row for row in chart_rows if row["track_id"] in missing_track_ids]
        track_details.update(enrich_chart(missing_rows, token, stats=stats, failures=failures))

    _atomic_json_write(CACHE_PATH, track_details)
    current_track_details = {
        track_id: track_details[track_id]
        for track_id in expected_track_ids
        if track_id in track_details
    }
    match_rate = len(current_track_details) / len(chart_rows)
    if match_rate < args.min_match_rate:
        raise ValueError(
            f"Metadata health gate failed: {match_rate:.1%} matched, "
            f"expected at least {args.min_match_rate:.1%}"
        )

    if not args.limit:
        write_raw_snapshot(chart_rows, current_track_details)

    finished_at = datetime.now().astimezone()
    metrics = {
        "run_id": started_at.strftime("%Y%m%dT%H%M%S%z"),
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
    if not args.limit:
        write_pipeline_quality(metrics, failures)

    print(
        json.dumps(
            {
                "chart_date": chart_date,
                "dry_run": bool(args.limit),
                "chart_rows": len(chart_rows),
                "matched_tracks": len(current_track_details),
                "metadata_match_rate": match_rate,
                "spotify_requests": stats.requests,
                "spotify_retries": stats.retries,
                "spotify_429_responses": stats.rate_limited,
                "generated_at": finished_at.isoformat(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
