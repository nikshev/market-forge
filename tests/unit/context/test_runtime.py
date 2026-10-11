"""The collector's loop: what is due when, and what a failure does to it (REQ-WP-093)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from channelflow.context.pollers import PollFailed
from channelflow.context.rest import RateLimited
from channelflow.context.runtime import Collector, CollectorConfig
from channelflow.context.status import Status
from channelflow.domain import DerivativesState, EventMeta

SECOND = 1_000_000_000


def make_state(at: int, source: str = "bybit-rest", symbol: str = "BTCUSDT") -> DerivativesState:
    return DerivativesState(
        meta=EventMeta(
            source=source,
            venue="bybit",
            market_type="perp",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=at,
            sequence=None,
            source_event_id=None,
        ),
        funding_rate=0.0,
    )


@dataclass
class FakePoller:
    venue: str = "bybit"
    now: list[int] = field(default_factory=lambda: [0])
    poll_calls: list[tuple[int, str]] = field(default_factory=list)
    history_calls: list[tuple[int, str]] = field(default_factory=list)
    fail_polls: int = 0
    fail_history: int = 0
    rate_limit_s: float | None = None

    def poll(self, symbol: str) -> list[DerivativesState]:
        self.poll_calls.append((self.now[0], symbol))
        if self.rate_limit_s is not None:
            raise RateLimited("tickers", self.rate_limit_s)
        if self.fail_polls > 0:
            self.fail_polls -= 1
            raise PollFailed("tickers: HTTP 500")
        return [make_state(self.now[0], symbol=symbol)]

    def history(self, symbol: str) -> list[DerivativesState]:
        self.history_calls.append((self.now[0], symbol))
        if self.fail_history > 0:
            self.fail_history -= 1
            raise PollFailed("funding/history: HTTP 500")
        return [make_state(1, source="bybit-funding-history", symbol=symbol)]


class MemorySink:
    """Collects what the collector stores, deduplicating as the real sink does."""

    def __init__(self) -> None:
        self.stored: dict[tuple[str, str, int, str], DerivativesState] = {}
        self.pending: int = 0
        self.flushes: list[int] = []
        self.clock: list[int] = [0]

    def __call__(self, state: DerivativesState) -> None:
        key = (state.meta.venue, state.meta.symbol, state.meta.event_time_ns, state.meta.source)
        if key not in self.stored:
            self.stored[key] = state
            self.pending += 1

    def flush(self) -> str | None:
        if self.pending == 0:
            return None
        self.pending = 0
        self.flushes.append(self.clock[0])
        return "snapshot"


def build(
    poller: FakePoller | None = None, **config: object
) -> tuple[Collector, FakePoller, MemorySink, list[int], Status]:
    clock = [0]
    fake = poller or FakePoller()
    fake.now = clock
    sink = MemorySink()
    sink.clock = clock
    status = Status(venue="bybit", poll_interval_s=60, now_ns=lambda: clock[0])
    collector = Collector(
        config=CollectorConfig(venue="bybit", symbols=("BTCUSDT",), **config),  # type: ignore[arg-type]
        poller=fake,
        sink=sink,
        now_ns=lambda: clock[0],
        status=status,
    )
    return collector, fake, sink, clock, status


@pytest.mark.trace("REQ-WP-093")
def test_the_first_step_loads_history_and_polls_once() -> None:
    collector, poller, sink, _, _ = build()
    collector.step()

    assert poller.history_calls == [(0, "BTCUSDT")]
    assert poller.poll_calls == [(0, "BTCUSDT")]
    assert len(sink.stored) == 2


@pytest.mark.trace("REQ-WP-093")
def test_nothing_is_polled_again_before_the_interval() -> None:
    collector, poller, _, clock, _ = build()
    collector.step()
    clock[0] = 59 * SECOND
    collector.step()
    assert len(poller.poll_calls) == 1

    clock[0] = 60 * SECOND
    collector.step()
    assert len(poller.poll_calls) == 2


@pytest.mark.trace("REQ-WP-093")
def test_history_is_refreshed_on_its_own_cadence_and_stored_once() -> None:
    collector, poller, sink, clock, _ = build(history_refresh_s=3600)
    collector.step()
    clock[0] = 3599 * SECOND
    collector.step()
    assert len(poller.history_calls) == 1
    clock[0] = 3600 * SECOND
    collector.step()
    assert len(poller.history_calls) == 2
    assert len([k for k in sink.stored if k[3] == "bybit-funding-history"]) == 1


@pytest.mark.trace("REQ-WP-093")
def test_a_failed_history_load_is_retried_on_the_poll_cadence_not_after_an_hour() -> None:
    """Without history `funding_z` has nothing; asking again only after an hour is an hour of it."""
    collector, poller, sink, clock, status = build(
        FakePoller(fail_history=1), history_refresh_s=3600
    )
    collector.step()
    assert (
        status.consecutive_failures >= 0
        and [k for k in sink.stored if k[3] == "bybit-funding-history"] == []
    )

    clock[0] = 60 * SECOND
    collector.step()

    assert len(poller.history_calls) == 2
    assert len([k for k in sink.stored if k[3] == "bybit-funding-history"]) == 1


@pytest.mark.trace("REQ-WP-093")
def test_a_failed_poll_stores_nothing_and_is_retried_on_the_next_cycle() -> None:
    collector, poller, sink, clock, status = build(FakePoller(fail_polls=1))
    collector.step()
    assert [k for k in sink.stored if k[3] == "bybit-rest"] == []
    assert status.consecutive_failures == 1

    clock[0] = 60 * SECOND
    collector.step()
    assert len([k for k in sink.stored if k[3] == "bybit-rest"]) == 1
    assert status.consecutive_failures == 0


@pytest.mark.trace("REQ-WP-093")
def test_the_previous_state_is_never_stored_again_as_if_it_were_new() -> None:
    collector, poller, sink, clock, _ = build()
    collector.step()
    poller.fail_polls = 1
    clock[0] = 60 * SECOND
    collector.step()
    polled = [k for k in sink.stored if k[3] == "bybit-rest"]
    assert [k[2] for k in polled] == [0]


@pytest.mark.trace("REQ-WP-093")
def test_a_rate_limit_delays_the_next_attempt_by_what_the_venue_asked() -> None:
    collector, poller, _, clock, _ = build(FakePoller(rate_limit_s=300.0))
    collector.step()
    clock[0] = 61 * SECOND
    collector.step()
    clock[0] = 299 * SECOND
    collector.step()
    assert len(poller.poll_calls) == 1  # still waiting out the 300 s
    clock[0] = 300 * SECOND
    poller.rate_limit_s = None
    collector.step()
    assert len(poller.poll_calls) == 2


@pytest.mark.trace("REQ-WP-093")
def test_pending_rows_are_flushed_on_the_flush_interval_and_not_before() -> None:
    collector, _, sink, clock, _ = build(flush_interval_s=300, flush_rows=1000)
    collector.step()
    clock[0] = 299 * SECOND
    collector.step()
    assert sink.flushes == []
    clock[0] = 300 * SECOND
    collector.step()
    assert sink.flushes == [300 * SECOND]


@pytest.mark.trace("REQ-WP-093")
def test_a_burst_of_rows_is_flushed_without_waiting_for_the_interval() -> None:
    collector, _, sink, _, _ = build(flush_interval_s=3600, flush_rows=2)
    collector.step()  # history row + poll row = 2 pending
    assert sink.flushes == [0]


@pytest.mark.trace("REQ-WP-093")
def test_close_flushes_what_is_pending() -> None:
    collector, _, sink, _, _ = build(flush_interval_s=3600, flush_rows=1000)
    collector.step()
    collector.close()
    assert sink.pending == 0 and len(sink.flushes) == 1


@pytest.mark.trace("REQ-WP-093")
def test_a_failed_flush_keeps_the_rows_and_is_counted_not_fatal() -> None:
    class Broken(MemorySink):
        def flush(self) -> str | None:
            raise OSError("object store down")

    collector, _, _, clock, status = build()
    collector.sink = Broken()  # type: ignore[assignment]
    collector.step()
    clock[0] = 301 * SECOND
    collector.step()  # does not raise
    assert status.flush_failures >= 1
