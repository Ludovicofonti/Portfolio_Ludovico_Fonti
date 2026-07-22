import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from scripts.bigquery_config import BigQueryConfig
from scripts.load_bigquery_raw import (
    DAY_MS,
    RAW_RETENTION_DAYS,
    ensure_datasets,
    load_chart_rows,
    load_track_rows,
    replace_partitioned_table,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]


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


def write_raw_snapshot(raw_dir):
    chart_path = raw_dir / "italy_daily_chart_2026-07-17.csv"
    fields = [
        "chart_date",
        "country",
        "country_name",
        "chart_source",
        "rank",
        "rank_change",
        "track_id",
        "track_name",
        "artist_ids",
        "artist_names",
        "artist_names_text",
        "days_on_chart",
        "peak_rank",
        "peak_count_text",
        "streams",
        "streams_change",
        "streams_7day",
        "streams_7day_change",
        "streams_total",
        "kworb_track_url",
    ]
    with chart_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "chart_date": "2026-07-17",
                "country": "IT",
                "rank": "1",
                "track_id": "track-1",
                "track_name": "Test Track",
                "artist_names_text": "Test Artist",
                "streams": "1000",
            }
        )
    details = {
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
    (raw_dir / "italy_daily_track_details_2026-07-17.json").write_text(
        json.dumps(details), encoding="utf-8"
    )


def test_raw_rows_include_partition_and_lineage_fields(tmp_path):
    write_raw_snapshot(tmp_path)
    chart_rows, lookup = load_chart_rows(tmp_path)
    details, artists, images = load_track_rows(lookup, tmp_path)
    assert chart_rows[0]["chart_date"] == "2026-07-17"
    assert chart_rows[0]["_dlt_id"]
    assert chart_rows[0]["_loaded_at"].endswith("+00:00")
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
        self.loads = []
        self.updated = []

    def get_dataset(self, dataset_ref):
        raise NotFound(f"Missing {dataset_ref}")

    def create_dataset(self, dataset, exists_ok=False):
        self.created_datasets.append((dataset, exists_ok))

    def load_table_from_json(self, rows, table_id, job_config):
        self.loads.append((rows, table_id, job_config))
        return FakeLoadJob()

    def get_table(self, table_id):
        return SimpleNamespace(table_id=table_id)

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


def test_bootstrap_and_raw_table_controls():
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
        [{"chart_date": "2026-07-17", "track_id": "track-1", "_loaded_at": "2026-07-17T00:00:00Z"}],
        ["track_id"],
    )
    job_config = client.loads[0][2]
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert job_config.time_partitioning.field == "chart_date"
    assert job_config.time_partitioning.expiration_ms == RAW_RETENTION_DAYS * DAY_MS
    assert job_config.clustering_fields == ["track_id"]
    assert client.updated[0][0].require_partition_filter is True


def test_bigquery_models_do_not_use_current_as_an_alias():
    sql = (
        PROJECT_DIR / "dbt" / "models" / "marts" / "mart_chart_entries_exits.sql"
    ).read_text(encoding="utf-8")
    assert " as current\n" not in sql.lower()
