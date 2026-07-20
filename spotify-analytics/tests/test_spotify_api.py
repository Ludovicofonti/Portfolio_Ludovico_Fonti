from pathlib import Path

import pytest
import requests
from spotify_api import (
    SpotifyRequestStats,
    get_spotify_with_retry,
    get_track_details,
    parse_kworb_daily_chart,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = "fake response"
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def test_parse_kworb_daily_chart_extracts_date_track_id_and_values():
    rows = parse_kworb_daily_chart((FIXTURE_DIR / "kworb_daily.html").read_text())
    assert len(rows) == 2
    assert rows[0]["chart_date"] == "2026-06-01"
    assert rows[0]["track_id"] == "track-1"
    assert rows[0]["rank_change"] == "NEW"
    assert rows[0]["streams"] == 351405
    assert rows[1]["rank_change"] == "RE"
    assert rows[1]["streams_7day_change"] is None


@pytest.mark.parametrize("status_code", [429, 500, 502, 503])
def test_spotify_retry_handles_transient_statuses(status_code):
    responses = [FakeResponse(status_code, headers={"Retry-After": "0"}), FakeResponse(200)]
    stats = SpotifyRequestStats()
    sleeps = []
    response = get_spotify_with_retry(
        "https://api.spotify.test/tracks/track-1",
        "token",
        stats=stats,
        request_get=lambda *args, **kwargs: responses.pop(0),
        sleep_fn=sleeps.append,
        random_fn=lambda: 0,
    )
    assert response.status_code == 200
    assert stats.requests == 2
    assert stats.retries == 1
    assert stats.rate_limited == (1 if status_code == 429 else 0)
    assert len(sleeps) == 1


def test_spotify_retry_raises_after_budget_is_exhausted():
    response = FakeResponse(503)
    with pytest.raises(requests.HTTPError):
        get_spotify_with_retry(
            "https://api.spotify.test/tracks/track-1",
            "token",
            max_retries=1,
            request_get=lambda *args, **kwargs: response,
            sleep_fn=lambda seconds: None,
            random_fn=lambda: 0,
        )


def test_get_track_details_uses_requested_track_id():
    calls = []

    def request_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(200, {"id": "track-1"})

    track = get_track_details("token", "track-1", request_get=request_get)
    assert track["id"] == "track-1"
    assert calls[0][0].endswith("/tracks/track-1")
    assert calls[0][1]["params"] == {"market": "IT"}
