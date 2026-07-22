import csv

import pytest

from scripts.refresh_public_data import validate_chart_rows, write_csv


def chart_row(rank=1, track_id="track-1"):
    return {
        "chart_date": "2026-06-01",
        "country": "IT",
        "rank": rank,
        "track_id": track_id,
        "streams": 100,
    }


def test_validate_chart_rows_rejects_incomplete_or_duplicate_snapshots():
    with pytest.raises(ValueError, match="expected at least"):
        validate_chart_rows([chart_row()], min_rows=2)
    with pytest.raises(ValueError, match="duplicate chart_date/country/track_id"):
        validate_chart_rows([chart_row(1), chart_row(2)], min_rows=2)
    with pytest.raises(ValueError, match="missing required"):
        validate_chart_rows([chart_row(track_id=None)], min_rows=1)


def test_write_csv_is_atomic_and_rejects_empty_datasets(tmp_path):
    output = tmp_path / "mart.csv"
    write_csv(output, [{"track_id": "track-1", "streams": 100}])
    with output.open(newline="", encoding="utf-8") as handle:
        assert list(csv.DictReader(handle))[0]["track_id"] == "track-1"
    assert not output.with_suffix(".csv.tmp").exists()
    with pytest.raises(ValueError, match="empty dataset"):
        write_csv(output, [])
