"""The API says what the channel's slope is (REQ-WP-082).

The stored snapshot has `slope_log_per_bar`; `ChannelOut` kept only `slope_normalized`, the slope in
units of the fit's own noise, from which the per-bar slope cannot be recovered. So the page could
not draw a sloped band, and drew three flat lines instead. The value is additive: nothing the
response carried changes."""

from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from channelflow.api import InMemoryRepository, create_app

from .conftest import BASE_NS, MINUTE_NS, bar, snapshot

AT_NS = BASE_NS + 60 * MINUTE_NS
SLOPE = 0.000425

#: What `GET /api/v1/channels` carried before this requirement.
BEFORE = {
    "as_of_ns",
    "model_name",
    "model_version",
    "lookback",
    "center_now",
    "upper_now",
    "lower_now",
    "slope_normalized",
    "width_pct",
    "quality_score",
    "source_max_event_time_ns",
    "mode",
}


@pytest.fixture
def client() -> TestClient:
    repo = InMemoryRepository()
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="spot")
    for i in range(120):
        repo.add_bar(bar(i, 112000.0 + i * 40.0))  # rising: a refit sees a positive slope
    stored = snapshot(as_of_ns=AT_NS, center=112000.0, slope=-0.01).model_copy(
        update={"slope_log_per_bar": -SLOPE}
    )
    repo.add_channel_snapshot(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, snapshot=stored
    )
    return TestClient(create_app(repository=repo))


def _channel(client: TestClient, **params: object) -> dict[str, object]:
    response = client.get(
        "/api/v1/channels",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": AT_NS,
            **params,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.trace("REQ-WP-082")
def test_the_stored_slope_is_served_in_the_as_seen_then_view(client: TestClient) -> None:
    served = _channel(client, as_seen_then=True)

    assert served["slope_log_per_bar"] == -SLOPE


@pytest.mark.trace("REQ-WP-082")
def test_the_refit_view_serves_its_own_slope_not_the_stored_one(client: TestClient) -> None:
    """The refit sees the rise that followed, so its slope is positive and is not the stored -SLOPE:
    the field is the fit's, in whichever view."""
    refit = _channel(client, as_seen_then=False)

    slope = refit["slope_log_per_bar"]
    assert isinstance(slope, float) and math.isfinite(slope)
    assert slope > 0.0 and slope != -SLOPE


@pytest.mark.trace("REQ-WP-082")
def test_every_field_the_response_carried_before_is_still_there_and_unchanged(
    client: TestClient,
) -> None:
    served = _channel(client, as_seen_then=True)

    assert set(served) == BEFORE | {"slope_log_per_bar"}
    assert served["center_now"] == 112000.0
    assert served["upper_now"] == 112500.0 and served["lower_now"] == 111500.0
    assert served["slope_normalized"] == -0.01
    assert served["lookback"] == 60


@pytest.mark.trace("REQ-WP-082")
def test_a_snapshot_stored_before_the_slope_existed_serves_zero_not_an_error(
    client: TestClient,
) -> None:
    """Rows written before the column read back as 0.0 (the model default): a flat band, which is
    what a snapshot with no recorded slope can honestly be drawn as -- and not a 500."""
    repo = InMemoryRepository()
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="spot")
    for i in range(120):
        repo.add_bar(bar(i, 112000.0))
    repo.add_channel_snapshot(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        snapshot=snapshot(as_of_ns=AT_NS, center=112000.0),
    )

    served = _channel(TestClient(create_app(repository=repo)), as_seen_then=True)

    assert served["slope_log_per_bar"] == 0.0
