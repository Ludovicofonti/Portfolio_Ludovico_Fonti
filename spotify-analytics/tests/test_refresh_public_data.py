import pytest

from scripts import refresh_public_data
from scripts.refresh_public_data import collect_snapshot, validate_chart_rows


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


def test_collect_snapshot_uses_bigquery_cache_and_fetches_only_missing(monkeypatch):
    rows = [chart_row(1, "track-1"), chart_row(2, "track-2")]
    cached_track = {"id": "track-1", "artists": [], "album": {"images": []}}
    fetched_track = {"id": "track-2", "artists": [], "album": {"images": []}}
    monkeypatch.setattr(refresh_public_data, "fetch_italy_daily_chart", lambda: rows)
    monkeypatch.setattr(
        refresh_public_data,
        "load_metadata_cache",
        lambda client, config, track_ids: {"track-1": cached_track},
    )
    monkeypatch.setattr(refresh_public_data, "get_access_token", lambda *_: "token")

    enriched_rows = []

    def fake_enrich(rows_to_enrich, token, stats, failures):
        enriched_rows.extend(rows_to_enrich)
        return {"track-2": fetched_track}

    monkeypatch.setattr(refresh_public_data, "enrich_chart", fake_enrich)
    snapshot = collect_snapshot(
        object(),
        object(),
        "client-id",
        "client-secret",
        min_chart_rows=2,
    )

    assert [row["track_id"] for row in enriched_rows] == ["track-2"]
    assert snapshot.track_details == {
        "track-1": cached_track,
        "track-2": fetched_track,
    }
    assert snapshot.new_track_details == {"track-2": fetched_track}
    assert snapshot.metrics["match_rate"] == 1
