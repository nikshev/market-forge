"""The collector's health and metrics (REQ-WP-093 FR-013)."""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from channelflow.context.status import Status, serve

SECOND = 1_000_000_000


def status_at(clock: list[int]) -> Status:
    return Status(venue="bybit", poll_interval_s=60, now_ns=lambda: clock[0])


@pytest.mark.trace("REQ-WP-093")
def test_a_collector_that_has_just_started_is_given_its_first_intervals() -> None:
    clock = [0]
    status = status_at(clock)
    assert status.healthy()
    clock[0] = 179 * SECOND
    assert status.healthy()
    clock[0] = 181 * SECOND
    assert not status.healthy()


@pytest.mark.trace("REQ-WP-093")
def test_healthy_means_a_success_within_three_intervals() -> None:
    clock = [0]
    status = status_at(clock)
    status.record_success()
    clock[0] = 179 * SECOND
    assert status.healthy()
    clock[0] = 181 * SECOND
    assert not status.healthy()
    status.record_success()
    assert status.healthy()


@pytest.mark.trace("REQ-WP-093")
def test_failures_are_counted_and_a_success_resets_the_run() -> None:
    clock = [0]
    status = status_at(clock)
    status.record_failure("tickers")
    status.record_failure("tickers")
    assert status.consecutive_failures == 2
    status.record_success()
    assert status.consecutive_failures == 0
    assert status.failures_total == {"tickers": 2}


@pytest.mark.trace("REQ-WP-093")
def test_the_metrics_name_the_age_of_the_last_state_and_the_failures() -> None:
    clock = [0]
    status = status_at(clock)
    status.record_success()
    status.record_failure("tickers")
    clock[0] = 42 * SECOND

    text = status.render_metrics()

    assert 'context_last_state_age_seconds{venue="bybit"} 42' in text
    assert 'context_poll_failures_total{venue="bybit",endpoint="tickers"} 1' in text
    assert 'context_healthy{venue="bybit"} 1' in text


@pytest.mark.trace("REQ-WP-093")
def test_before_any_success_the_age_is_reported_as_unknown_not_zero() -> None:
    clock = [5 * SECOND]
    text = status_at(clock).render_metrics()
    assert 'context_last_state_age_seconds{venue="bybit"} -1' in text


@pytest.mark.trace("REQ-WP-093")
def test_the_endpoints_answer_200_when_healthy_and_503_when_not() -> None:
    clock = [0]
    status = status_at(clock)
    status.record_success()
    server, _ = serve(status, port=0, host="127.0.0.1")
    port = server.server_address[1]
    try:
        assert urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3).status == 200
        assert (
            b"context_healthy"
            in urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=3).read()
        )
        clock[0] = 10_000 * SECOND
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3)
        assert caught.value.code == 503
    finally:
        server.shutdown()
        server.server_close()
