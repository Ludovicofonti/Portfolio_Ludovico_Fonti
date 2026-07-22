import json
from datetime import UTC, datetime

import pytest
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from scripts.bigquery_config import BigQueryConfig
from scripts.bigquery_loader import (
    DAY_MS,
    RAW_RETENTION_DAYS,
    ensure_datasets,
    load_metadata_cache,
    load_snapshot_to_bigquery,
    normalize_chart_rows,
    normalize_track_rows,
    replace_partitioned_table,
)


def test_bigquery_config_requires_project(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(RuntimeError, match="GCP_PROJECT_ID"):
        BigQueryConfig.from_env()


def test_bigquery_config_defaults_and_overrides(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "portfolio-project")
    monkeypatch.setenv("BIGQUERY_LOCATION", "europe-west8")
    monkeypatch.setenv("SPOTIFY_BQ_MARTS_DATASET", "custom_marts")
    config = BigQueryConfig.from_env()
    assert config.project == "portfolio-project"
    assert config.location == "europe-west8"
    assert config.marts_dataset == "custom_marts"
    assert config.raw_dataset == "spotify_analytics_raw"
    assert set(config.datasets) == {"raw", "staging", "intermediate", "marts"}


def chart_row():
    return {
        "chart_date": "2026-07-17",
        "country": "IT",
        "country_name": "Italy",
        "chart_source": "kworb_spotify_daily",
        "rank": 1,
        "track_id": "track-1",
        "track_name": "Test Track",
        "artist_ids": ["artist-1"],
        "artist_names": ["Test Artist"],
        "artist_names_text": "Test Artist",
        "streams": 1000,
    }


def track_details():
    return {
        "track-1": {
            "id": "track-1",
            "name": "Test Track",
            "explicit": False,
            "artists": [{"id": "artist-1", "name": "Test Artist"}],
            "album": {
                "id": "album-1",
                "name": "Test Album",
                "release_date": "2026-07-01",
                "images": [{"url": "https://example.test/cover.jpg", "width": 640}],
            },
        }
    }


def test_in_memory_rows_include_partition_and_lineage_fields():
    loaded_at = datetime(2026, 7, 17, tzinfo=UTC)
    chart_rows, lookup = normalize_chart_rows([chart_row()], loaded_at=loaded_at)
    details, artists, images = normalize_track_rows(
        lookup,
        track_details(),
        loaded_at=loaded_at,
    )
    assert chart_rows[0]["chart_date"] == "2026-07-17"
    assert json.loads(chart_rows[0]["artist_ids"]) == ["artist-1"]
    assert chart_rows[0]["_dlt_id"]
    assert chart_rows[0]["_loaded_at"] == "2026-07-17T00:00:00+00:00"
    assert details[0]["explicit"] == "false"
    assert details[0]["chart_track_id"] == "track-1"
    assert artists[0]["chart_date"] == "2026-07-17"
    assert images[0]["chart_track_id"] == "track-1"


class FakeLoadJob:
    def result(self):
        return self


class FakeLoaderClient:
    def __init__(self):
        self.created_datasets = []
        self.tables = {}
        self.loads = []
        self.updated = []

    def get_dataset(self, dataset_ref):
        raise NotFound(f"Missing {dataset_ref}")

    def create_dataset(self, dataset, exists_ok=False):
        self.created_datasets.append((dataset, exists_ok))

    def get_table(self, table_id):
        if table_id not in self.tables:
            raise NotFound(f"Missing {table_id}")
        return self.tables[table_id]

    def create_table(self, table, exists_ok=False):
        table_id = f"{table.project}.{table.dataset_id}.{table.table_id}"
        self.tables[table_id] = table
        return table

    def load_table_from_json(self, rows, table_id, job_config):
        self.loads.append((rows, table_id, job_config))
        return FakeLoadJob()

    def update_table(self, table, fields):
        self.updated.append((table, fields))


def bigquery_config():
    return BigQueryConfig(
        project="portfolio-project",
        location="EU",
        raw_dataset="spotify_analytics_raw",
        staging_dataset="spotify_analytics_staging",
        intermediate_dataset="spotify_analytics_intermediate",
        marts_dataset="spotify_analytics_marts",
        maximum_bytes_billed=10_000_000_000,
    )


def test_bootstrap_and_partition_replacement_controls():
    client = FakeLoaderClient()
    config = bigquery_config()
    ensure_datasets(client, config)
    assert len(client.created_datasets) == 4
    assert all(
        dataset.labels["application"] == "spotify-analytics"
        for dataset, _ in client.created_datasets
    )

    replace_partitioned_table(
        client,
        config,
        "italy_daily_chart",
        ["chart_date", "track_id", "_loaded_at"],
        [
            {
                "chart_date": "2026-07-17",
                "track_id": "track-1",
                "_loaded_at": "2026-07-17T00:00:00Z",
            }
        ],
        ["track_id"],
    )
    table = client.tables["portfolio-project.spotify_analytics_raw.italy_daily_chart"]
    assert table.require_partition_filter is True
    assert table.time_partitioning.field == "chart_date"
    assert table.time_partitioning.expiration_ms == RAW_RETENTION_DAYS * DAY_MS
    assert table.clustering_fields == ["track_id"]
    assert client.loads[0][1].endswith("italy_daily_chart$20260717")
    assert client.loads[0][2].write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE


class FakeQueryClient:
    def __init__(self):
        self.job_config = None

    def query(self, query, job_config):
        self.job_config = job_config
        return FakeQueryResult()


class FakeQueryResult:
    def result(self):
        return [
            {"track_id": "track-1", "payload_json": '{"id": "track-1"}'},
            {"track_id": "broken", "payload_json": "not-json"},
        ]


def test_metadata_cache_is_read_from_bigquery_with_bound_parameters():
    client = FakeQueryClient()
    cached = load_metadata_cache(client, bigquery_config(), {"track-1", "track-2"})
    assert cached == {"track-1": {"id": "track-1"}}
    parameters = {parameter.name: parameter for parameter in client.job_config.query_parameters}
    assert parameters["market"].value == "IT"
    assert parameters["track_ids"].values == ["track-1", "track-2"]


def test_partition_replacement_rejects_mixed_dates():
    rows = [
        {"chart_date": "2026-07-17", "track_id": "one"},
        {"chart_date": "2026-07-18", "track_id": "two"},
    ]
    with pytest.raises(ValueError, match="one chart_date"):
        replace_partitioned_table(
            FakeLoaderClient(),
            bigquery_config(),
            "italy_daily_chart",
            ["chart_date", "track_id"],
            rows,
            ["track_id"],
        )


def test_snapshot_is_loaded_directly_without_filesystem_staging():
    client = FakeLoaderClient()
    metrics = {
        "run_id": "20260717T000000Z",
        "run_started_at": "2026-07-17T00:00:00+00:00",
        "chart_date": "2026-07-17",
        "chart_rows": 1,
        "matched_tracks": 1,
        "match_rate": 1.0,
        "duplicate_tracks": 0,
        "missing_streams": 0,
        "spotify_requests": 1,
        "spotify_retries": 0,
        "spotify_429_responses": 0,
        "pipeline_duration_seconds": 1.0,
        "pipeline_status": "fresh",
        "generated_at": "2026-07-17T00:00:01+00:00",
    }
    summary = load_snapshot_to_bigquery(
        client,
        bigquery_config(),
        [chart_row()],
        track_details(),
        track_details(),
        metrics,
        [],
    )

    destinations = [table_id for _, table_id, _ in client.loads]
    partition_loads = [table_id for table_id in destinations if "$20260717" in table_id]
    assert len(partition_loads) == 4
    assert any(table_id.endswith("spotify_track_metadata_cache") for table_id in destinations)
    assert any(table_id.endswith("pipeline_runs") for table_id in destinations)
    assert summary["chart_rows"] == 1
    assert summary["new_cache_entries"] == 1
