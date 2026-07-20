import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "dlt"))

from spotify_api import (  # noqa: E402
    SpotifyRequestStats,
    fetch_italy_daily_chart,
    get_access_token,
    get_track_details,
)

RAW_DIR = PROJECT_DIR / "data" / "raw"
CACHE_PATH = PROJECT_DIR / "data" / "cache" / "spotify_tracks.json"
QUALITY_DIR = PROJECT_DIR / "data" / "quality"
PUBLIC_SOURCE_DIR = PROJECT_DIR / "evidence" / "sources" / "spotify_public"
MIN_CHART_ROWS = 190
MIN_METADATA_MATCH_RATE = 0.95


def parse_args():
    parser = argparse.ArgumentParser(description="Build public CSV snapshots for Evidence.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only enrich the first N chart rows. Intended for smoke tests.",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Write validated raw inputs only; dbt will build the public marts.",
    )
    parser.add_argument("--min-chart-rows", type=int, default=MIN_CHART_ROWS)
    parser.add_argument("--min-match-rate", type=float, default=MIN_METADATA_MATCH_RATE)
    return parser.parse_args()


def parse_rank_change(value):
    if not value or value in {"=", "-", "NEW", "RE"}:
        return 0
    try:
        return int(value.replace("+", ""))
    except ValueError:
        return 0


def parse_release_date(value):
    if not value:
        return None
    if len(value) == 4:
        value = f"{value}-01-01"
    elif len(value) == 7:
        value = f"{value}-01"
    return date.fromisoformat(value)


def largest_album_image(track):
    images = track.get("album", {}).get("images", [])
    if not images:
        return None
    return max(images, key=lambda image: image.get("width") or 0).get("url")


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


def build_top_songs(chart_rows, track_details):
    top_200_streams = sum(row["streams"] or 0 for row in chart_rows)
    songs = []

    for row in chart_rows:
        track = track_details.get(row["track_id"], {})
        album = track.get("album", {})
        artists = track.get("artists", [])
        release_date = parse_release_date(album.get("release_date"))
        chart_date = date.fromisoformat(row["chart_date"])
        rank = row["rank"]

        if rank <= 10:
            rank_bucket = "Top 10"
        elif rank <= 50:
            rank_bucket = "Top 50"
        elif rank <= 100:
            rank_bucket = "Top 100"
        else:
            rank_bucket = "Top 200"

        songs.append(
            {
                "chart_date": row["chart_date"],
                "country": row["country"],
                "chart_rank": rank,
                "rank_change": parse_rank_change(row["rank_change"]),
                "chart_track_id": row["track_id"],
                "track_name": row["track_name"],
                "artist_names_text": row["artist_names_text"],
                "streams": row["streams"],
                "streams_share": (row["streams"] or 0) / top_200_streams if top_200_streams else 0,
                "streams_change": row["streams_change"],
                "streams_7day": row["streams_7day"],
                "streams_total": row["streams_total"],
                "days_on_chart": row["days_on_chart"],
                "peak_rank": row["peak_rank"],
                "rank_bucket": rank_bucket,
                "spotify_track_id": track.get("id"),
                "spotify_track_url": track.get("external_urls", {}).get("spotify"),
                "spotify_album_id": album.get("id"),
                "album_name": album.get("name"),
                "album_type": album.get("album_type"),
                "album_release_date": release_date.isoformat() if release_date else None,
                "release_year": release_date.year if release_date else None,
                "days_since_release": (chart_date - release_date).days if release_date else None,
                "duration_minutes": (track.get("duration_ms") or 0) / 60000 if track else None,
                "is_explicit": track.get("explicit"),
                "artist_count": len(artists),
                "is_collaboration": len(artists) > 1,
                "album_image_url": largest_album_image(track),
                "kworb_track_url": row["kworb_track_url"],
            }
        )

    return songs


def build_top_artists(songs, track_details):
    artists = defaultdict(
        lambda: {
            "track_ids": set(),
            "ranks": [],
            "streams": 0,
        }
    )

    for song in songs:
        track = track_details.get(song["chart_track_id"], {})
        for artist in track.get("artists", []):
            bucket = artists[(artist.get("id"), artist.get("name"))]
            bucket["spotify_artist_url"] = artist.get("external_urls", {}).get("spotify")
            bucket["track_ids"].add(track.get("id") or song["chart_track_id"])
            bucket["ranks"].append(song["chart_rank"])
            bucket["streams"] += song["streams"] or 0

    rows = []
    for (artist_id, artist_name), values in artists.items():
        rows.append(
            {
                "chart_date": songs[0]["chart_date"] if songs else None,
                "country": songs[0]["country"] if songs else "IT",
                "spotify_artist_id": artist_id,
                "artist_name": artist_name,
                "spotify_artist_url": values.get("spotify_artist_url"),
                "track_count": len(values["track_ids"]),
                "streams": values["streams"],
                "best_rank": min(values["ranks"]),
                "average_rank": round(sum(values["ranks"]) / len(values["ranks"]), 2),
            }
        )

    rows.sort(key=lambda row: (-row["streams"], row["artist_name"] or ""))
    for index, row in enumerate(rows, start=1):
        row["artist_stream_rank"] = index
    return rows


def build_album_release_analysis(songs):
    albums = defaultdict(
        lambda: {
            "chart_track_count": 0,
            "streams": 0,
            "ranks": [],
            "days_since_release": [],
            "has_explicit_track": False,
        }
    )

    for song in songs:
        if not song["spotify_album_id"]:
            continue
        bucket = albums[song["spotify_album_id"]]
        bucket.update(
            {
                "chart_date": song["chart_date"],
                "country": song["country"],
                "spotify_album_id": song["spotify_album_id"],
                "album_name": song["album_name"],
                "album_type": song["album_type"],
                "album_image_url": song["album_image_url"],
                "album_release_date": song["album_release_date"],
                "release_year": song["release_year"],
            }
        )
        bucket["chart_track_count"] += 1
        bucket["streams"] += song["streams"] or 0
        bucket["ranks"].append(song["chart_rank"])
        if song["days_since_release"] is not None:
            bucket["days_since_release"].append(song["days_since_release"])
        bucket["has_explicit_track"] = bucket["has_explicit_track"] or bool(song["is_explicit"])

    rows = []
    for bucket in albums.values():
        days = bucket.pop("days_since_release")
        ranks = bucket.pop("ranks")
        bucket["best_rank"] = min(ranks)
        bucket["average_days_since_release"] = round(sum(days) / len(days), 2) if days else None
        rows.append(bucket)

    rows.sort(key=lambda row: (-row["streams"], row["album_name"] or ""))
    return rows


def build_chart_momentum(songs):
    rows = []
    for song in songs:
        rank_change = song["rank_change"]
        streams_change = song["streams_change"]
        rows.append(
            {
                "chart_date": song["chart_date"],
                "chart_rank": song["chart_rank"],
                "track_name": song["track_name"],
                "artist_names_text": song["artist_names_text"],
                "album_name": song["album_name"],
                "streams": song["streams"],
                "streams_change": streams_change,
                "rank_change": rank_change,
                "days_on_chart": song["days_on_chart"],
                "peak_rank": song["peak_rank"],
                "rank_momentum": "Rising"
                if rank_change > 0
                else "Falling"
                if rank_change < 0
                else "Stable",
                "streams_momentum": (
                    "Streams up"
                    if streams_change and streams_change > 0
                    else "Streams down"
                    if streams_change and streams_change < 0
                    else "Streams stable"
                ),
                "album_image_url": song["album_image_url"],
                "spotify_track_url": song["spotify_track_url"],
            }
        )
    return rows


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

    songs = build_top_songs(chart_rows, current_track_details)
    artists = build_top_artists(songs, current_track_details)
    albums = build_album_release_analysis(songs)
    momentum = build_chart_momentum(songs)

    if not args.limit:
        write_raw_snapshot(chart_rows, current_track_details)
        if not args.extract_only:
            write_csv(PUBLIC_SOURCE_DIR / "mart_top_songs_italy.csv", songs)
            write_csv(PUBLIC_SOURCE_DIR / "mart_top_artists_italy.csv", artists)
            write_csv(PUBLIC_SOURCE_DIR / "mart_album_release_analysis.csv", albums)
            write_csv(PUBLIC_SOURCE_DIR / "mart_chart_momentum.csv", momentum)

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
                "chart_date": songs[0]["chart_date"],
                "dry_run": bool(args.limit),
                "songs": len(songs),
                "matched_tracks": len(current_track_details),
                "metadata_match_rate": match_rate,
                "spotify_requests": stats.requests,
                "spotify_retries": stats.retries,
                "spotify_429_responses": stats.rate_limited,
                "artists": len(artists),
                "albums": len(albums),
                "generated_at": datetime.now().astimezone().isoformat(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
