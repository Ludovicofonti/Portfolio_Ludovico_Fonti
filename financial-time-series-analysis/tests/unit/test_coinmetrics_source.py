from datetime import datetime, timezone

from pipelines.coinmetrics_source import CoinMetricsCommunitySource


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        return FakeResponse(self.pages.pop(0))


def test_coinmetrics_pagination_and_point_in_time_mapping(monkeypatch):
    monkeypatch.delenv("COINMETRICS_API_KEY", raising=False)
    session = FakeSession([
        {
            "data": [{"asset": "btc", "time": "2026-01-01T00:00:00Z", "TxCnt": "12"}],
            "next_page_url": "https://community-api.coinmetrics.io/v4/page-2",
        },
        {
            "data": [{"asset": "btc", "time": "2026-01-02T00:00:00Z", "TxCnt": "13"}],
        },
    ])
    config = {
        "base_url": "https://community-api.coinmetrics.io/v4",
        "page_size": 10000,
        "api_key_env": "COINMETRICS_API_KEY",
    }
    source = CoinMetricsCommunitySource(config=config, session=session)
    records = source.fetch(
        "btc",
        "TxCnt",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 3, tzinfo=timezone.utc),
        "1d",
    )

    assert [row["value"] for row in records] == [12.0, 13.0]
    assert records[0]["available_time"] == datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert session.calls[0][1]["assets"] == "btc"
    assert "api_key" not in session.calls[0][1]
    assert session.calls[1][1] == {}
