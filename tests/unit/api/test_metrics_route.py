"""The exposition, over HTTP (REQ-WP-055)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from channelflow.api.app import create_app
from channelflow.api.metrics_route import CONTENT_TYPE
from channelflow.api.repositories import InMemoryRepository
from channelflow.metrics import MetricKind, MetricRegistry
from channelflow.observability.dashboard import STALE_FEEDS


@pytest.mark.trace("REQ-WP-055")
def test_a_process_that_has_measured_nothing_serves_nothing() -> None:
    """`MetricRegistry` creates no series until something observes one, so a
    scrape before anything has happened returns an empty body.

    An error would make a quiet process look broken, and a zero would be the lie
    the registry exists to refuse.
    """
    client = TestClient(create_app(repository=InMemoryRepository()))
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.text == ""


@pytest.mark.trace("REQ-WP-055")
def test_what_has_been_observed_is_served() -> None:
    registry = MetricRegistry()
    registry.register(STALE_FEEDS, MetricKind.GAUGE, "feeds that have stopped updating")
    registry.observe(STALE_FEEDS, 2.0)

    client = TestClient(create_app(repository=InMemoryRepository(), metrics=registry))
    body = client.get("/metrics").text
    assert f"# TYPE {STALE_FEEDS} gauge" in body
    assert f"{STALE_FEEDS} 2" in body


@pytest.mark.trace("REQ-WP-055")
def test_the_content_type_is_the_one_a_scraper_expects() -> None:
    """Sent explicitly: `text/plain` without the version parameter is accepted by
    most scrapers and is not what the exposition format specifies."""
    client = TestClient(create_app(repository=InMemoryRepository()))
    assert client.get("/metrics").headers["content-type"] == CONTENT_TYPE
    assert "version=0.0.4" in CONTENT_TYPE


@pytest.mark.trace("REQ-WP-055")
def test_the_exposition_is_not_part_of_the_read_api() -> None:
    """Operational rather than PRD §28's: its shape is Prometheus's, and
    versioning it alongside the endpoints a browser calls would tie two things
    that change for different reasons."""
    client = TestClient(create_app(repository=InMemoryRepository()))
    assert client.get("/metrics").status_code == 200
    assert client.get("/api/v1/metrics").status_code == 404


@pytest.mark.trace("REQ-WP-055")
def test_a_registered_metric_nothing_observed_is_still_absent() -> None:
    """Registration records a name; it does not make a series. The distinction
    is [[REQ-WP-036]]'s and survives to the wire."""
    registry = MetricRegistry()
    registry.register(STALE_FEEDS, MetricKind.GAUGE, "feeds that have stopped updating")

    client = TestClient(create_app(repository=InMemoryRepository(), metrics=registry))
    assert client.get("/metrics").text == ""
