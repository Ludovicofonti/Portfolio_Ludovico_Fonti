import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

try:
    from scripts.bigquery_config import BigQueryConfig
except ModuleNotFoundError:  # Direct execution: python scripts/load_bigquery_raw.py
    from bigquery_config import BigQueryConfig

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
RAW_RETENTION_DAYS = 365
DAY_MS = 86_400_000
RESOURCE_LABELS = {"application": "spotify-analytics", "managed_by": "github-actions"}

CHART_FIELDS = [
    "chart_date", "country", "country_name", "chart_source", "rank", "rank_change",
    "track_id", "track_name", "artist_ids", "artist_names", "artist_names_text",
    "days_on_chart", "peak_rank", "peak_count_text", "streams", "streams_change",
    "streams_7day", "streams_7day_change", "streams_total", "kworb_track_url",
    "_dlt_id", "_loaded_at",
]
DETAIL_FIELDS = [
    "_dlt_id", "id", "name", "uri", "href", "external_urls__spotify",
    "external_ids__isrc", "duration_ms", "explicit", "disc_number", "track_number",
    "is_local", "is_playable", "album__id", "album__name", "album__album_type",
    "album__release_date", "album__release_date_precision", "album__total_tracks",
    "album__external_urls__spotify", "chart_track_id", "chart_date", "chart_country",
    "chart_rank", "chart_track_name", "chart_artist_names_text", "chart_streams",
    "chart_streams_total", "_loaded_at",
]
ARTIST_FIELDS = [
    "_dlt_id", "_dlt_parent_id", "_dlt_list_idx", "id", "name", "uri", "href",
    "external_urls__spotify", "chart_date", "chart_track_id", "_loaded_at",
]
IMAGE_FIELDS = [
    "_dlt_id", "_dlt_parent_id", "_dlt_list_idx", "url", "height", "width",
    "chart_date", "chart_track_id", "_loaded_at",
]


def stable_id(*parts):
    value = "|".join(str(part) for part in parts)
    return hashlib.sha1(value.encode(), usedforsecurity=False).hexdigest()


def scalar_text(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def loaded_at(path):
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()


def load_chart_rows(raw_dir=RAW_DIR):
    rows = []
    by_snapshot = {}
    for path in sorted(raw_dir.glob("italy_daily_chart_*.csv")):
        snapshot_loaded_at = loaded_at(path)
        with path.open(newline="", encoding="utf-8") as handle:
            snapshot = list(csv.DictReader(handle))
        for source in snapshot:
            row = {field: source.get(field) for field in CHART_FIELDS}
            row["_dlt_id"] = stable_id(source["chart_date"], source["country"], source["track_id"])
            row["_loaded_at"] = snapshot_loaded_at
            rows.append(row)
            by_snapshot[(source["chart_date"], source["track_id"])] = row
    return rows, by_snapshot


def load_track_rows(chart_lookup, raw_dir=RAW_DIR):
    details_rows, artist_rows, image_rows = [], [], []
    for path in sorted(raw_dir.glob("italy_daily_track_details_*.json")):
        chart_date = path.stem.removeprefix("italy_daily_track_details_")
        snapshot_loaded_at = loaded_at(path)
        tracks = json.loads(path.read_text(encoding="utf-8"))
        for track_id, track in tracks.items():
            chart = chart_lookup.get((chart_date, track_id))
            if chart is None:
                continue
            detail_id = stable_id(chart_date, track_id, "detail")
            album = track.get("album") or {}
            details_rows.append(
                {
                    "_dlt_id": detail_id,
                    "id": scalar_text(track.get("id")),
                    "name": scalar_text(track.get("name")),
                    "uri": scalar_text(track.get("uri")),
                    "href": scalar_text(track.get("href")),
                    "external_urls__spotify": scalar_text(
                        (track.get("external_urls") or {}).get("spotify")
                    ),
                    "external_ids__isrc": scalar_text(
                        (track.get("external_ids") or {}).get("isrc")
                    ),
                    "duration_ms": scalar_text(track.get("duration_ms")),
                    "explicit": scalar_text(track.get("explicit")),
                    "disc_number": scalar_text(track.get("disc_number")),
                    "track_number": scalar_text(track.get("track_number")),
                    "is_local": scalar_text(track.get("is_local")),
                    "is_playable": scalar_text(track.get("is_playable")),
                    "album__id": scalar_text(album.get("id")),
                    "album__name": scalar_text(album.get("name")),
                    "album__album_type": scalar_text(album.get("album_type")),
                    "album__release_date": scalar_text(album.get("release_date")),
                    "album__release_date_precision": scalar_text(
                        album.get("release_date_precision")
                    ),
                    "album__total_tracks": scalar_text(album.get("total_tracks")),
                    "album__external_urls__spotify": scalar_text(
                        (album.get("external_urls") or {}).get("spotify")
                    ),
                    "chart_track_id": track_id,
                    "chart_date": chart_date,
                    "chart_country": chart.get("country"),
                    "chart_rank": chart.get("rank"),
                    "chart_track_name": chart.get("track_name"),
                    "chart_artist_names_text": chart.get("artist_names_text"),
                    "chart_streams": chart.get("streams"),
                    "chart_streams_total": chart.get("streams_total"),
                    "_loaded_at": snapshot_loaded_at,
                }
            )
            for index, artist in enumerate(track.get("artists") or []):
                artist_rows.append(
                    {
                        "_dlt_id": stable_id(detail_id, "artist", index),
                        "_dlt_parent_id": detail_id,
                        "_dlt_list_idx": str(index),
                        "id": scalar_text(artist.get("id")),
                        "name": scalar_text(artist.get("name")),
                        "uri": scalar_text(artist.get("uri")),
                        "href": scalar_text(artist.get("href")),
                        "external_urls__spotify": scalar_text(
                            (artist.get("external_urls") or {}).get("spotify")
                        ),
                        "chart_date": chart_date,
                        "chart_track_id": track_id,
                        "_loaded_at": snapshot_loaded_at,
                    }
                )
            for index, image in enumerate(album.get("images") or []):
                image_rows.append(
                    {
                        "_dlt_id": stable_id(detail_id, "image", index),
                        "_dlt_parent_id": detail_id,
                        "_dlt_list_idx": str(index),
                        "url": scalar_text(image.get("url")),
                        "height": scalar_text(image.get("height")),
                        "width": scalar_text(image.get("width")),
                        "chart_date": chart_date,
                        "chart_track_id": track_id,
                        "_loaded_at": snapshot_loaded_at,
                    }
                )
    return details_rows, artist_rows, image_rows


def table_schema(fields):
    schema = []
    for field in fields:
        field_type = "DATE" if field == "chart_date" else "STRING"
        if field == "_loaded_at":
            field_type = "TIMESTAMP"
        schema.append(bigquery.SchemaField(field, field_type))
    return schema


def ensure_datasets(client, config):
    descriptions = {
        "raw": "Validated Kworb and Spotify snapshots; partitions expire after 365 days.",
        "staging": "Typed dbt staging views for Spotify analytics.",
        "intermediate": "Reusable dbt transformations for Spotify analytics.",
        "marts": "Published dbt facts and business marts for Spotify analytics.",
    }
    for layer, dataset_id in config.datasets.items():
        dataset_ref = f"{config.project}.{dataset_id}"
        try:
            client.get_dataset(dataset_ref)
            continue
        except NotFound:
            pass
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = config.location
        dataset.labels = RESOURCE_LABELS
        dataset.description = descriptions[layer]
        client.create_dataset(dataset, exists_ok=True)


def replace_partitioned_table(client, config, table_name, fields, rows, cluster_fields):
    if not rows:
        raise ValueError(f"Refusing to replace {table_name} with an empty dataset")
    table_id = f"{config.project}.{config.raw_dataset}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        schema=table_schema(fields),
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="chart_date",
            expiration_ms=RAW_RETENTION_DAYS * DAY_MS,
        ),
        clustering_fields=cluster_fields,
    )
    client.load_table_from_json(rows, table_id, job_config=job_config).result()
    table = client.get_table(table_id)
    table.require_partition_filter = True
    table.labels = RESOURCE_LABELS
    table.description = "Managed by the Spotify Analytics GitHub Actions pipeline."
    client.update_table(table, ["require_partition_filter", "labels", "description"])


def main():
    config = BigQueryConfig.from_env()
    client = bigquery.Client(project=config.project, location=config.location)
    chart_rows, chart_lookup = load_chart_rows()
    if not chart_rows:
        raise RuntimeError(f"No chart snapshots found in {RAW_DIR}")
    detail_rows, artist_rows, image_rows = load_track_rows(chart_lookup)
    ensure_datasets(client, config)
    tables = {
        "italy_daily_chart": (CHART_FIELDS, chart_rows, ["country", "track_id"]),
        "italy_daily_track_details": (
            DETAIL_FIELDS, detail_rows, ["chart_country", "chart_track_id"]
        ),
        "italy_daily_track_details__artists": (
            ARTIST_FIELDS, artist_rows, ["id", "chart_track_id"]
        ),
        "italy_daily_track_details__album__images": (
            IMAGE_FIELDS, image_rows, ["chart_track_id"]
        ),
    }
    for table_name, (fields, rows, clusters) in tables.items():
        replace_partitioned_table(client, config, table_name, fields, rows, clusters)
    print(
        json.dumps(
            {
                "project": config.project,
                "datasets": config.datasets,
                "chart_rows": len(chart_rows),
                "track_details": len(detail_rows),
                "artists": len(artist_rows),
                "album_images": len(image_rows),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
