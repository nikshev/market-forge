"""One HTTP GET, and what each way it can go wrong becomes (REQ-WP-093 FR-004)."""

from __future__ import annotations

import httpx
import pytest

from channelflow.context.rest import HttpxJsonClient, RateLimited, RestFailure


def client_for(handler: httpx.MockTransport) -> HttpxJsonClient:
    return HttpxJsonClient(transport=handler, timeout=1.0)


@pytest.mark.trace("REQ-WP-093")
def test_a_successful_answer_is_its_decoded_json() -> None:
    http = client_for(httpx.MockTransport(lambda request: httpx.Response(200, json={"a": [1]})))
    assert http.get("https://x.test/p", {"q": "1"}) == {"a": [1]}


@pytest.mark.trace("REQ-WP-093")
def test_the_query_parameters_are_sent() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={})

    client_for(httpx.MockTransport(handler)).get("https://x.test/p", {"symbol": "BTCUSDT"})
    assert seen == ["https://x.test/p?symbol=BTCUSDT"]


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize("status", [429, 418])
def test_a_rate_limit_carries_how_long_the_venue_asked_us_to_wait(status: int) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, headers={"Retry-After": "37"})
    )
    with pytest.raises(RateLimited) as caught:
        client_for(transport).get("https://x.test/p")
    assert caught.value.retry_after_s == 37.0


@pytest.mark.trace("REQ-WP-093")
def test_a_rate_limit_without_a_retry_after_waits_a_stated_minimum() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(429))
    with pytest.raises(RateLimited) as caught:
        client_for(transport).get("https://x.test/p")
    assert caught.value.retry_after_s >= 60.0


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize("status", [400, 403, 500, 503])
def test_any_other_failure_status_is_a_failure_naming_the_status(status: int) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, text="no"))
    with pytest.raises(RestFailure, match=str(status)):
        client_for(transport).get("https://x.test/p")


@pytest.mark.trace("REQ-WP-093")
def test_an_answer_that_is_not_json_is_a_failure_not_an_exception_of_another_kind() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text="<html>"))
    with pytest.raises(RestFailure, match="JSON"):
        client_for(transport).get("https://x.test/p")


@pytest.mark.trace("REQ-WP-093")
def test_a_timeout_or_a_dropped_connection_is_a_failure_and_never_hangs() -> None:
    def hangs(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    for handler in (hangs, refused):
        with pytest.raises(RestFailure):
            client_for(httpx.MockTransport(handler)).get("https://x.test/p")
