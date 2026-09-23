"""The offered-set read (REQ-WP-074).

The frontend's control renders what this route reports and nothing else, so
these tests are about the set being exactly the deployment's: the source always,
the configured targets, ascending, once each.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from channelflow.api.app import create_app
from channelflow.api.repositories import InMemoryRepository
from channelflow.timeframes import TIMEFRAMES, parse_list


def _client(*tokens: str) -> TestClient:
    configured = parse_list(",".join(tokens)) if tokens else ()
    return TestClient(create_app(repository=InMemoryRepository(), timeframes=configured))


@pytest.mark.trace("REQ-WP-074")
def test_the_source_is_offered_when_nothing_is_configured() -> None:
    response = _client().get("/api/v1/timeframes")

    assert response.status_code == 200
    assert response.json() == {"timeframes": [{"token": "1m", "timeframe_ns": 60_000_000_000}]}


@pytest.mark.trace("REQ-WP-074")
def test_the_response_is_the_source_plus_the_configured_targets() -> None:
    response = _client("1h", "5m").get("/api/v1/timeframes")

    assert response.json() == {
        "timeframes": [
            {"token": "1m", "timeframe_ns": 60_000_000_000},
            {"token": "5m", "timeframe_ns": 300_000_000_000},
            {"token": "1h", "timeframe_ns": 3_600_000_000_000},
        ]
    }


@pytest.mark.trace("REQ-WP-074")
def test_a_configured_source_appears_once() -> None:
    response = _client("1m", "5m").get("/api/v1/timeframes")
    tokens = [entry["token"] for entry in response.json()["timeframes"]]

    assert tokens == ["1m", "5m"]


@pytest.mark.trace("REQ-WP-074")
def test_the_durations_are_the_producers_durations() -> None:
    """A client that requests a reported duration gets the built series."""
    entries = _client("15m", "4h", "1w").get("/api/v1/timeframes").json()["timeframes"]

    for entry in entries:
        known = TIMEFRAMES[entry["token"]]
        assert entry["timeframe_ns"] == known.ns
        assert isinstance(entry["timeframe_ns"], int)


@pytest.mark.trace("REQ-WP-074")
def test_ascending_by_duration_is_not_the_configuration_order() -> None:
    """Nothing about the response depends on how the variable was spelled."""
    forward = _client("1w", "5m", "1d", "1h").get("/api/v1/timeframes").json()
    shuffled = _client("1h", "1d", "5m", "1w").get("/api/v1/timeframes").json()

    assert forward == shuffled
    durations = [entry["timeframe_ns"] for entry in forward["timeframes"]]
    assert durations == sorted(durations)
