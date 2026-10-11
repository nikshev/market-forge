"""Each venue's poll and its settled-funding history (REQ-WP-093 FR-001..FR-005)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.context.pollers import PollFailed, poller_for
from channelflow.context.rest import RateLimited, RestFailure
from tests.unit.context.doubles import FakeClient, load

MS = 1_000_000
NOW = 1_791_706_800_000 * MS


@pytest.mark.trace("REQ-WP-093")
def test_binance_poll_is_a_state_for_mark_and_funding_and_the_recent_open_interest_buckets(
    client: FakeClient,
) -> None:
    states = poller_for("binance", client, now_ns=lambda: NOW).poll("BTCUSDT")

    sources = [s.meta.source for s in states]
    assert sources.count("binance-rest") == 1
    assert sources.count("binance-rest-oi") == len(load("binance_openInterestHist"))
    assert all(s.meta.ingest_time_ns == NOW for s in states)
    assert all(s.meta.symbol == "BTCUSDT" and s.meta.market_type == "perp" for s in states)
    oi = [s for s in states if s.meta.source == "binance-rest-oi"]
    assert all(s.open_interest_usd is not None for s in oi)


@pytest.mark.trace("REQ-WP-093")
def test_bybit_poll_is_one_state_at_the_venues_time(client: FakeClient) -> None:
    (state,) = poller_for("bybit", client, now_ns=lambda: NOW).poll("BTCUSDT")
    assert state.meta.event_time_ns == int(load("bybit_tickers")["time"]) * MS
    assert state.meta.ingest_time_ns == NOW
    assert state.open_interest_usd is not None and state.mark_price is not None


@pytest.mark.trace("REQ-WP-093")
def test_okx_poll_assembles_four_answers_with_the_contract_value_it_fetched(
    client: FakeClient,
) -> None:
    (state,) = poller_for("okx", client, now_ns=lambda: NOW).poll("BTC-USDT-SWAP")

    assert state.meta.symbol == "BTC-USDT-SWAP"
    assert state.open_interest_usd == float(load("okx_open_interest")["data"][0]["oiUsd"])
    assert state.index_price == Decimal(load("okx_index_tickers")["data"][0]["idxPx"])
    # The index ticker is asked for by the underlying (`BTC-USDT`), not the swap's own name.
    index_calls = [c for c in client.calls if "index-tickers" in c[0]]
    assert index_calls and index_calls[0][1]["instId"] == "BTC-USDT"


@pytest.mark.trace("REQ-WP-093")
def test_okx_asks_for_the_contract_value_once_per_symbol(client: FakeClient) -> None:
    poller = poller_for("okx", client, now_ns=lambda: NOW)
    poller.poll("BTC-USDT-SWAP")
    poller.poll("BTC-USDT-SWAP")
    assert len([c for c in client.calls if "instruments" in c[0]]) == 1


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize(
    ("venue", "symbol", "route"),
    [
        ("binance", "BTCUSDT", "/fapi/v1/premiumIndex"),
        ("binance", "BTCUSDT", "/futures/data/openInterestHist"),
        ("bybit", "BTCUSDT", "/v5/market/tickers"),
        ("okx", "BTC-USDT-SWAP", "/api/v5/public/open-interest"),
        ("okx", "BTC-USDT-SWAP", "/api/v5/public/mark-price"),
    ],
)
def test_a_poll_with_one_failing_request_returns_nothing_at_all(
    venue: str, symbol: str, route: str
) -> None:
    client = FakeClient(fail={route: RestFailure(route, "HTTP 500")})
    with pytest.raises(PollFailed) as caught:
        poller_for(venue, client, now_ns=lambda: NOW).poll(symbol)
    assert route in str(caught.value)


@pytest.mark.trace("REQ-WP-093")
def test_a_rate_limit_is_passed_on_with_its_wait_so_the_loop_can_back_off() -> None:
    client = FakeClient(fail={"/v5/market/tickers": RateLimited("/v5/market/tickers", 90.0)})
    with pytest.raises(RateLimited) as caught:
        poller_for("bybit", client, now_ns=lambda: NOW).poll("BTCUSDT")
    assert caught.value.retry_after_s == 90.0


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize(
    ("venue", "symbol"), [("binance", "BTCUSDT"), ("bybit", "BTCUSDT"), ("okx", "BTC-USDT-SWAP")]
)
def test_history_is_one_settled_row_per_settlement(
    client: FakeClient, venue: str, symbol: str
) -> None:
    states = poller_for(venue, client, now_ns=lambda: NOW).history(symbol)

    assert len(states) >= 24  # funding_z's window, from the first start
    assert {s.meta.source for s in states} == {f"{venue}-funding-history"}
    assert len({s.meta.event_time_ns for s in states}) == len(states)


@pytest.mark.trace("REQ-WP-093")
def test_a_failing_history_request_is_a_failure_and_stores_nothing() -> None:
    client = FakeClient(fail={"/v5/market/funding/history": RestFailure("h", "HTTP 500")})
    with pytest.raises(PollFailed):
        poller_for("bybit", client, now_ns=lambda: NOW).history("BTCUSDT")


@pytest.mark.trace("REQ-WP-093")
def test_an_unknown_venue_is_refused_not_defaulted() -> None:
    with pytest.raises(ValueError, match="kraken"):
        poller_for("kraken", FakeClient(), now_ns=lambda: NOW)


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize(
    ("venue", "symbol", "route", "missing"),
    [
        ("binance", "BTCUSDT", "/fapi/v1/premiumIndex", "markPrice"),
        ("bybit", "BTCUSDT", "/v5/market/tickers", "result"),
        ("okx", "BTC-USDT-SWAP", "/api/v5/public/mark-price", "data"),
    ],
)
def test_an_answer_missing_what_the_normalizer_needs_is_a_failed_poll_not_a_crash(
    venue: str, symbol: str, route: str, missing: str
) -> None:
    class Broken(FakeClient):
        def get(self, url: str, params: object = None) -> object:  # type: ignore[override]
            answer = super().get(url, params)  # type: ignore[arg-type]
            if route in url:
                if isinstance(answer, list):
                    answer = [dict(answer[0])]
                    answer[0].pop(missing)
                else:
                    answer = dict(answer)
                    answer.pop(missing)
            return answer

    with pytest.raises(PollFailed):
        poller_for(venue, Broken(), now_ns=lambda: NOW).poll(symbol)


@pytest.mark.trace("REQ-WP-093")
def test_binance_asks_for_several_open_interest_buckets_so_a_missed_poll_leaves_no_hole(
    client: FakeClient,
) -> None:
    poller_for("binance", client, now_ns=lambda: NOW).poll("BTCUSDT")
    (call,) = [c for c in client.calls if "openInterestHist" in c[0]]
    assert int(call[1]["limit"]) >= 3 and call[1]["period"] == "5m"


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize(
    ("venue", "symbol", "route"),
    [
        ("binance", "BTCUSDT", "fundingRate"),
        ("bybit", "BTCUSDT", "funding/history"),
        ("okx", "BTC-USDT-SWAP", "funding-rate-history"),
    ],
)
def test_history_asks_for_enough_settlements_to_fill_the_window(
    client: FakeClient, venue: str, symbol: str, route: str
) -> None:
    from channelflow.context.sources import FUNDING_WINDOW

    poller_for(venue, client, now_ns=lambda: NOW).history(symbol)
    (call,) = [c for c in client.calls if route in c[0]]
    assert int(call[1]["limit"]) >= FUNDING_WINDOW
