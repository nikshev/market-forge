"""PRD section 28's read endpoints (REQ-API-001).

Every response is checked against data put into the repository by hand. The API
reads what the pipeline produced and computes nothing (FR-010) -- the one
exception, the explicit refit, has its own file.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from .conftest import BASE_NS, MINUTE_NS


@pytest.mark.trace("REQ-API-001")
def test_markets_are_served(client: TestClient) -> None:
    """FR-005."""
    response = client.get("/api/v1/markets")

    assert response.status_code == 200
    assert len(response.json()["markets"]) == 3


@pytest.mark.trace("REQ-API-001")
def test_markets_filter_by_venue(client: TestClient) -> None:
    """SC-003. A filter that returns everything is not a filter."""
    all_markets = client.get("/api/v1/markets").json()["markets"]
    filtered = client.get("/api/v1/markets", params={"venue": "bybit"}).json()["markets"]

    assert len(filtered) == 1
    assert filtered[0]["venue"] == "bybit"
    assert len(filtered) < len(all_markets)


@pytest.mark.trace("REQ-API-001")
def test_markets_filter_by_market_type(client: TestClient) -> None:
    """FR-005's other half."""
    perps = client.get("/api/v1/markets", params={"market_type": "perp"}).json()["markets"]

    assert [m["symbol"] for m in perps] == ["BTCUSDT"]
    assert perps[0]["market_type"] == "perp"


@pytest.mark.trace("REQ-API-001")
def test_bars_are_served_in_event_time_order(client: TestClient) -> None:
    """FR-004, SC-003."""
    response = client.get(
        "/api/v1/bars",
        params={"venue": "binance", "symbol": "BTCUSDT", "timeframe_ns": MINUTE_NS},
    )

    bars = response.json()["bars"]
    assert len(bars) == 10
    assert [b["close_time_ns"] for b in bars] == sorted(b["close_time_ns"] for b in bars)


@pytest.mark.trace("REQ-API-001")
def test_bars_honour_the_time_range(client: TestClient) -> None:
    """FR-004, SC-003.

    Both bounds are asserted, because an implementation that dropped the end
    bound would pass a test that only moved the start.

    Bar `i` closes at minute `i + 1`, so an inclusive [3m, 6m] holds four bars,
    not three. Both bounds are inclusive: a range whose ends mean different
    things is a range nobody can reason about from the outside.
    """
    response = client.get(
        "/api/v1/bars",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "start_ns": BASE_NS + 3 * MINUTE_NS,
            "end_ns": BASE_NS + 6 * MINUTE_NS,
        },
    )

    bars = response.json()["bars"]
    assert len(bars) == 4, "bars closing at minutes 3, 4, 5 and 6"
    assert all(
        BASE_NS + 3 * MINUTE_NS <= b["close_time_ns"] <= BASE_NS + 6 * MINUTE_NS for b in bars
    )


@pytest.mark.trace("REQ-API-001")
def test_a_limit_returns_the_most_recent_bars(client: TestClient) -> None:
    """FR-004. Most recent, not first: a chart opening on a symbol wants the
    end of the series, and returning the oldest three would look like a stalled
    feed."""
    limited = client.get(
        "/api/v1/bars",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "limit": 3,
        },
    ).json()["bars"]

    assert len(limited) == 3
    assert limited[-1]["close_time_ns"] == BASE_NS + 10 * MINUTE_NS
    assert limited[0]["close_time_ns"] == BASE_NS + 8 * MINUTE_NS


@pytest.mark.trace("REQ-API-001")
def test_an_unknown_symbol_returns_an_empty_result(client: TestClient) -> None:
    """FR-009, SC-004. Nothing known is a fact, not an error -- and a 404 here
    would be indistinguishable from a broken route."""
    response = client.get(
        "/api/v1/bars",
        params={"venue": "binance", "symbol": "NOPEUSDT", "timeframe_ns": MINUTE_NS},
    )

    assert response.status_code == 200
    assert response.json()["bars"] == []


@pytest.mark.trace("REQ-API-001")
def test_signals_are_served_and_filtered(client: TestClient) -> None:
    """FR-007, SC-003."""
    all_signals = client.get("/api/v1/signals").json()["signals"]
    assert len(all_signals) == 1

    matching = client.get("/api/v1/signals", params={"symbol": "BTCUSDT"}).json()["signals"]
    assert len(matching) == 1

    other = client.get("/api/v1/signals", params={"symbol": "ETHUSDT"}).json()["signals"]
    assert other == []


@pytest.mark.trace("REQ-API-001")
def test_signals_filter_by_time_range(client: TestClient) -> None:
    """FR-007."""
    before = client.get("/api/v1/signals", params={"end_ns": BASE_NS - MINUTE_NS}).json()["signals"]

    assert before == []


@pytest.mark.trace("REQ-API-001")
def test_a_signal_detail_separates_the_later_outcome(client: TestClient) -> None:
    """FR-008, PRD section 28.6 and section 27.4.

    The outcome is a separate field, never merged into the decision snapshot.
    Section 27.4 requires it "visually separated so it cannot be confused with
    information available at signal time" -- and a response that merged them
    would make that impossible for any UI, not just this one.
    """
    signal_id = client.get("/api/v1/signals").json()["signals"][0]["signal_id"]

    detail = client.get(f"/api/v1/signals/{signal_id}").json()

    assert detail["decision"]["state"] == "confirmed"
    assert "channel" in detail
    assert "features" in detail
    assert "outcome" in detail
    assert detail["outcome"] is None, "nothing has resolved it; see ADR-010"


@pytest.mark.trace("REQ-API-001")
def test_an_unknown_signal_is_a_not_found(client: TestClient) -> None:
    """The one place a 404 is right: the id names a specific thing that does
    not exist, rather than a query that matched nothing."""
    response = client.get("/api/v1/signals/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.trace("REQ-API-001")
def test_a_feature_snapshot_is_served(client: TestClient) -> None:
    """FR-006."""
    response = client.get(
        "/api/v1/features/snapshot",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": BASE_NS + 5 * MINUTE_NS,
        },
    )

    assert response.status_code == 200
    assert response.json()["values"] == {}, "nothing was stored; an empty snapshot is the fact"


@pytest.mark.trace("REQ-API-001")
def test_a_feature_time_series_is_served(client: TestClient, repository: object) -> None:
    """FR-006. Values stored at three instants, two of them inside the range."""
    repository.add_feature_snapshot(  # type: ignore[attr-defined]
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=BASE_NS + 2 * MINUTE_NS,
        values={"qi_l1": -0.5},
    )
    repository.add_feature_snapshot(  # type: ignore[attr-defined]
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=BASE_NS + 4 * MINUTE_NS,
        values={"qi_l1": 0.1},
    )
    repository.add_feature_snapshot(  # type: ignore[attr-defined]
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=BASE_NS + 9 * MINUTE_NS,
        values={"qi_l1": 0.9},
    )

    series = client.get(
        "/api/v1/features/timeseries",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "start_ns": BASE_NS,
            "end_ns": BASE_NS + 5 * MINUTE_NS,
        },
    ).json()["points"]

    assert [p["values"]["qi_l1"] for p in series] == [-0.5, 0.1]
