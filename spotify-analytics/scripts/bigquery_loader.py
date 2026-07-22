import hashlib
import json
from datetime import UTC, datetime

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

RAW_RETENTION_DAYS = 365
DAY_MS = 86_400_000
RESOURCE_LABELS = {"application": "spotify-analytics", "managed_by": "github-actions"}
METADATA_CACHE_TABLE = "spotify_track_metadata_cache"
PIPELINE_RUNS_TABLE = "pipeline_runs"

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
PIPELINE_RUN_FIELDS = [
    bigquery.SchemaField("run_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("run_started_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("chart_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("chart_rows", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("matched_tracks", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("match_rate", "FLOAT", mode="REQUIRED"),
    bigquery.SchemaField("duplicate_tracks", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("missing_streams", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("spotify_requests", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("spotify_retries", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("spotify_429_responses", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("pipeline_duration_seconds", "FLOAT", mode="REQUIRED"),
    bigquery.SchemaField("pipeline_status", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("generated_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("failures_json", "STRING", mode="REQUIRED"),
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


def utc_timestamp(value=None):
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat()


def normalize_chart_rows(chart_rows, loaded_at=None):
    loaded_at = utc_timestamp(loaded_at)
    rows = []
    lookup = {}
    for source in chart_rows:
        row = {field: scalar_text(source.get(field)) for field in CHART_FIELDS}
        for field in ("artist_ids", "artist_names"):
            value = source.get(field)
            row[field] = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, list)
                else scalar_text(value)
            )
        row["_dlt_id"] = stable_id(
            source["chart_date"], source["country"], source["track_id"]
        )
        row["_loaded_at"] = loaded_at
        rows.append(row)
        lookup[(source["chart_date"], source["track_id"])] = row
    return rows, lookup


def normalize_track_rows(chart_lookup, track_details, loaded_at=None):
    loaded_at = utc_timestamp(loaded_at)
    details_rows, artist_rows, image_rows = [], [], []
    for (chart_date, track_id), chart in chart_lookup.items():
        track = track_details.get(track_id)
        if not track:
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
                "_loaded_at": loaded_at,
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
                    "_loaded_at": loaded_at,
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
                    "_loaded_at": loaded_at,
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
        "raw": "Validated Kworb and Spotify data loaded directly by GitHub Actions.",
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


def ensure_partitioned_table(
    client,
    table_id,
    schema,
    partition_field,
    cluster_fields,
    description,
    require_partition_filter=True,
):
    try:
        table = client.get_table(table_id)
    except NotFound:
        table = bigquery.Table(table_id, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field=partition_field,
            expiration_ms=RAW_RETENTION_DAYS * DAY_MS,
        )
        table.clustering_fields = cluster_fields
        table.require_partition_filter = require_partition_filter
        table.labels = RESOURCE_LABELS
        table.description = description
        return client.create_table(table, exists_ok=True)

    table.require_partition_filter = require_partition_filter
    table.labels = RESOURCE_LABELS
    table.description = description
    client.update_table(table, ["require_partition_filter", "labels", "description"])
    return table


def replace_partitioned_table(client, config, table_name, fields, rows, cluster_fields):
    if not rows:
        raise ValueError(f"Refusing to replace {table_name} with an empty dataset")
    chart_dates = {row["chart_date"] for row in rows}
    if len(chart_dates) != 1:
        raise ValueError(
            f"Expected one chart_date for {table_name}, found {sorted(chart_dates)}"
        )

    table_id = f"{config.project}.{config.raw_dataset}.{table_name}"
    schema = table_schema(fields)
    ensure_partitioned_table(
        client,
        table_id,
        schema,
        "chart_date",
        cluster_fields,
        "Managed directly by the Spotify Analytics GitHub Actions pipeline.",
    )
    partition_suffix = next(iter(chart_dates)).replace("-", "")
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    client.load_table_from_json(
        rows,
        f"{table_id}${partition_suffix}",
        job_config=job_config,
    ).result()


def ensure_metadata_cache_table(client, config):
    table_id = f"{config.project}.{config.raw_dataset}.{METADATA_CACHE_TABLE}"
    schema = [
        bigquery.SchemaField("track_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("market", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("payload_json", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("cached_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("cache_date", "DATE", mode="REQUIRED"),
    ]
    return ensure_partitioned_table(
        client,
        table_id,
        schema,
        "cache_date",
        ["track_id", "market"],
        "Append-only cache of Spotify track metadata used by the online pipeline.",
        require_partition_filter=False,
    )


def load_metadata_cache(client, config, track_ids, market="IT"):
    if not track_ids:
        return {}
    table_id = f"{config.project}.{config.raw_dataset}.{METADATA_CACHE_TABLE}"
    query = f"""
        select track_id, payload_json
        from `{table_id}`
        where market = @market and track_id in unnest(@track_ids)
        qualify row_number() over (partition by track_id order by cached_at desc) = 1
    """
    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=config.maximum_bytes_billed,
        query_parameters=[
            bigquery.ScalarQueryParameter("market", "STRING", market),
            bigquery.ArrayQueryParameter("track_ids", "STRING", sorted(track_ids)),
        ],
    )
    cached = {}
    for row in client.query(query, job_config=job_config).result():
        try:
            cached[row["track_id"]] = json.loads(row["payload_json"])
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
    return cached


def append_metadata_cache(client, config, track_details, market="IT", cached_at=None):
    if not track_details:
        return
    cached_at = cached_at or datetime.now(UTC)
    rows = [
        {
            "track_id": track_id,
            "market": market,
            "payload_json": json.dumps(payload, ensure_ascii=False),
            "cached_at": cached_at.isoformat(),
            "cache_date": cached_at.date().isoformat(),
        }
        for track_id, payload in track_details.items()
    ]
    table_id = f"{config.project}.{config.raw_dataset}.{METADATA_CACHE_TABLE}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    client.load_table_from_json(rows, table_id, job_config=job_config).result()


def record_pipeline_run(client, config, metrics, failures):
    table_id = f"{config.project}.{config.raw_dataset}.{PIPELINE_RUNS_TABLE}"
    ensure_partitioned_table(
        client,
        table_id,
        PIPELINE_RUN_FIELDS,
        "chart_date",
        ["pipeline_status"],
        "Operational metrics for Spotify Analytics pipeline executions.",
    )
    row = {**metrics, "failures_json": json.dumps(failures, ensure_ascii=False)}
    job_config = bigquery.LoadJobConfig(
        schema=PIPELINE_RUN_FIELDS,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    client.load_table_from_json([row], table_id, job_config=job_config).result()


def load_snapshot_to_bigquery(
    client,
    config,
    chart_rows,
    track_details,
    new_track_details,
    metrics,
    failures,
):
    ensure_datasets(client, config)
    ensure_metadata_cache_table(client, config)
    loaded_at = datetime.now(UTC)
    normalized_chart, chart_lookup = normalize_chart_rows(chart_rows, loaded_at=loaded_at)
    detail_rows, artist_rows, image_rows = normalize_track_rows(
        chart_lookup,
        track_details,
        loaded_at=loaded_at,
    )
    tables = {
        "italy_daily_chart": (
            CHART_FIELDS,
            normalized_chart,
            ["country", "track_id"],
        ),
        "italy_daily_track_details": (
            DETAIL_FIELDS,
            detail_rows,
            ["chart_country", "chart_track_id"],
        ),
        "italy_daily_track_details__artists": (
            ARTIST_FIELDS,
            artist_rows,
            ["id", "chart_track_id"],
        ),
        "italy_daily_track_details__album__images": (
            IMAGE_FIELDS,
            image_rows,
            ["chart_track_id"],
        ),
    }
    for table_name, (fields, rows, clusters) in tables.items():
        replace_partitioned_table(client, config, table_name, fields, rows, clusters)
    append_metadata_cache(client, config, new_track_details, cached_at=loaded_at)
    record_pipeline_run(client, config, metrics, failures)
    return {
        "project": config.project,
        "datasets": config.datasets,
        "chart_rows": len(normalized_chart),
        "track_details": len(detail_rows),
        "artists": len(artist_rows),
        "album_images": len(image_rows),
        "new_cache_entries": len(new_track_details),
    }
