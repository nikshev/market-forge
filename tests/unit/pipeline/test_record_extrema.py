"""A replay records the extrema it detected (REQ-WP-029)."""

from __future__ import annotations

import math
from itertools import groupby

import pytest

from channelflow.bus import EventBus
from channelflow.events import ExtremumConfirmed, ExtremumObserved
from channelflow.lakehouse import InMemoryObjectStore
from channelflow.pipeline import record_replay
from channelflow.tables import extrema as extrema_table

from .test_replay import MINUTE_NS, bar, rising_with_rejections


def turning(n: int = 200) -> list:
    """A series with real turns, so there is something to confirm.

    A monotone series confirms nothing, and a test asserting on extrema over one
    would be asserting about its fixture.
    """
    return [bar(i, 100.0 + 6.0 * math.sin(i / 9.0)) for i in range(n)]


def replay(bars: list, *, store: InMemoryObjectStore, bus: EventBus | None = None):
    return record_replay(
        bars,
        store=store,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        bus=bus,
    )


@pytest.fixture
def store() -> InMemoryObjectStore:
    return InMemoryObjectStore()


@pytest.mark.trace("REQ-WP-029")
def test_a_replay_fills_the_extremum_tables(store: InMemoryObjectStore) -> None:
    """The tables have been reachable and empty since REQ-WP-028."""
    recording, _ = replay(turning(), store=store)

    confirmed = extrema_table.read_confirmed(extrema_table.confirmed_table_for(store))
    candidates = extrema_table.read_candidates(extrema_table.candidates_table_for(store))

    assert recording.confirmed_extrema > 0
    assert len(confirmed) == recording.confirmed_extrema
    assert len(candidates) == recording.extremum_candidates
    assert candidates


@pytest.mark.trace("REQ-WP-029")
def test_what_was_written_is_what_the_detector_produced(store: InMemoryObjectStore) -> None:
    """Field for field, through the plane and back."""
    from channelflow.extrema import DirectionalChangeDetector

    bars = turning()
    replay(bars, store=store)

    expected = DirectionalChangeDetector(instrument_id="binance:BTCUSDT", venue_scope="binance")
    expected.run(bars)

    stored = extrema_table.read_confirmed(extrema_table.confirmed_table_for(store))
    assert stored == sorted(expected.confirmed, key=lambda e: e.extremum_time_ns)


@pytest.mark.trace("REQ-WP-029")
def test_a_caller_sees_every_extremum_event(store: InMemoryObjectStore) -> None:
    """The bus's second producer. Its own note called the first benefit "one
    caller, one capability, proven by tests rather than by use"."""
    seen_confirmed: list[ExtremumConfirmed] = []
    seen_candidates: list[ExtremumObserved] = []
    bus = EventBus()
    bus.subscribe(ExtremumConfirmed, seen_confirmed.append)
    bus.subscribe(ExtremumObserved, seen_candidates.append)

    recording, _ = replay(turning(), store=store, bus=bus)

    assert len(seen_confirmed) == recording.confirmed_extrema
    assert len(seen_candidates) == recording.extremum_candidates


@pytest.mark.trace("REQ-WP-029")
def test_an_observer_does_not_change_what_is_recorded(store: InMemoryObjectStore) -> None:
    bars = turning()
    plain, _ = replay(bars, store=InMemoryObjectStore())

    bus = EventBus()
    bus.subscribe(ExtremumConfirmed, lambda _: None)
    observed, _ = replay(bars, store=store, bus=bus)

    assert observed.confirmed_extrema == plain.confirmed_extrema
    assert observed.dataset == plain.dataset


@pytest.mark.trace("REQ-WP-029")
def test_a_confirmation_arrives_in_its_own_bar_s_turn(store: InMemoryObjectStore) -> None:
    """Not flushed at the end.

    A batch produces the same rows and a different event stream, and the
    difference stays invisible until a live process attaches the same
    subscribers and sees a burst. Interleaving is what proves it: a candidate
    observed after a confirmation must arrive after it.
    """
    order: list[str] = []
    bus = EventBus()
    bus.subscribe(ExtremumConfirmed, lambda _: order.append("confirmed"))
    bus.subscribe(ExtremumObserved, lambda _: order.append("candidate"))

    replay(turning(), store=store, bus=bus)

    assert "confirmed" in order
    assert "candidate" in order
    # Counted in runs, not by "is it sorted". A flush at the end produces
    # exactly two runs -- every confirmation, then every candidate -- and that
    # sequence is *also* unsorted, so the obvious assertion passes for it. The
    # mutation sweep found that; this counts the alternations instead.
    runs = [kind for kind, _ in groupby(order)]
    assert len(runs) > 2


@pytest.mark.trace("REQ-WP-029")
def test_a_second_replay_writes_no_extrema(store: InMemoryObjectStore) -> None:
    """ADR-056 on two more tables."""
    bars = turning()
    first, _ = replay(bars, store=store)
    second, _ = replay(bars, store=store)

    assert first.confirmed_extrema > 0
    assert second.confirmed_extrema == 0
    assert second.extremum_candidates == 0
    # Exactly, and every term. `skipped` is the whole run's tally, so with `>=`
    # the channel snapshots alone satisfied it and dropping the confirmations
    # from the count went unnoticed -- which the mutation sweep found.
    assert second.skipped == (
        first.channel_snapshots
        + first.signals
        + first.confirmed_extrema
        + first.extremum_candidates
    )
    assert (
        len(extrema_table.read_confirmed(extrema_table.confirmed_table_for(store)))
        == first.confirmed_extrema
    )


@pytest.mark.trace("REQ-WP-029")
def test_a_longer_replay_adds_only_what_is_new(store: InMemoryObjectStore) -> None:
    """Idempotence rather than inertia: writing nothing on a re-run is easy if
    you also write nothing on an extension."""
    bars = turning(240)
    replay(bars[:150], store=store)
    second, _ = replay(bars, store=store)

    whole = InMemoryObjectStore()
    replay(bars, store=whole)

    assert second.confirmed_extrema > 0
    assert extrema_table.read_confirmed(
        extrema_table.confirmed_table_for(store)
    ) == extrema_table.read_confirmed(extrema_table.confirmed_table_for(whole))


@pytest.mark.trace("REQ-WP-029")
def test_a_series_with_no_turn_records_nothing_and_refuses_nothing(
    store: InMemoryObjectStore,
) -> None:
    """An absence of turns is a fact about the series."""
    flat = [bar(i, 100.0) for i in range(60)]

    recording, _ = replay(flat, store=store)

    assert recording.confirmed_extrema == 0


@pytest.mark.trace("REQ-WP-029")
def test_what_the_replay_already_recorded_is_unchanged(store: InMemoryObjectStore) -> None:
    """SC-006: the criterion that catches this feature damaging its neighbours."""
    bars = rising_with_rejections()

    recording, report = replay(bars, store=store)

    assert recording.channel_snapshots > 0
    assert recording.signals == report.candidates_opened
    assert recording.has_dataset
