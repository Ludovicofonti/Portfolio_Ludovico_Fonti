from datetime import datetime, timedelta, timezone

from pipelines.binance_futures_source import fetch_open_interest
from pipelines.binance_spot_source import fetch_ohlcv


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, dict(params), timeout))
        return FakeResponse(self.payloads.pop(0))


def _kline(open_ms, close_ms):
    return [
        open_ms, "100", "102", "99", "101", "10", close_ms, "1010", 12,
        "6", "606", "0",
    ]


def test_ohlcv_excludes_the_still_open_candle():
    now = datetime.now(timezone.utc)
    closed = _kline(
        int((now - timedelta(hours=2)).timestamp() * 1000),
        int((now - timedelta(hours=1)).timestamp() * 1000),
    )
    open_candle = _kline(
        int(now.timestamp() * 1000),
        int((now + timedelta(hours=1)).timestamp() * 1000),
    )
    rows = list(fetch_ohlcv("BTCUSDT", "1h", limit=1000, session=FakeSession([[closed, open_candle]])))
    assert len(rows) == 1
    assert rows[0]["close_time"] <= rows[0]["ingested_at"]


def test_open_interest_paginates_from_last_timestamp():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first_timestamp = int(start.timestamp() * 1000)
    page = [
        {
            "timestamp": first_timestamp + index * 3_600_000,
            "sumOpenInterest": "10",
            "sumOpenInterestValue": "1000",
        }
        for index in range(500)
    ]
    session = FakeSession([page, []])
    rows = list(fetch_open_interest("BTCUSDT", start_time=start, session=session))
    assert len(rows) == 500
    assert len(session.calls) == 2
    assert session.calls[1][1]["startTime"] == page[-1]["timestamp"] + 1
