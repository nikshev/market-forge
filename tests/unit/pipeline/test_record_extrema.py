"""A replay records the extrema it detected (REQ-WP-029)."""

from __future__ import annotations

import math
from itertools import groupby
from pathlib import Path

import pytest

from channelflow.bus import EventBus
from channelflow.events import ExtremumConfirmed, ExtremumObserved
from channelflow.lakehouse import Catalog
from channelflow.pipeline import record_replay
from channelflow.tables import extrema as extrema_table

from .test_replay import MINUTE_NS, bar, rising_with_rejections


def turning(n: int = 200) -> list:
    """A series with real turns, so there is something to confirm.

    A monotone series confirms nothing, and a test asserting on extrema over one
    would be asserting about its fixture.
    """
    return [bar(i, 100.0 + 6.0 * math.sin(i / 9.0)) for i in range(n)]


def _fresh(home: Path) -> Catalog:
    """A plane of its own, for the tests that need two."""
    from channelflow.lakehouse import catalog as open_catalog

    home.mkdir(parents=True, exist_ok=True)
    return open_catalog(uri=f"sqlite:///{home}/catalog.db", warehouse=str(home))


def replay(bars: list, *, catalog: Catalog, bus: EventBus | None = None):
    return record_replay(
        bars,
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        bus=bus,
    )


@pytest.mark.trace("REQ-WP-029")
def test_a_replay_fills_the_extremum_tables(catalog: Catalog) -> None:
    """The tables have been reachable and empty since REQ-WP-028."""
    recording, _ = replay(turning(), catalog=catalog)

    confirmed = extrema_table.read_confirmed(extrema_table.confirmed_table_for(catalog))
    candidates = extrema_table.read_candidates(extrema_table.candidates_table_for(catalog))

    assert recording.confirmed_extrema > 0
    assert len(confirmed) == recording.confirmed_extrema
    assert len(candidates) == recording.extremum_candidates
    assert candidates


@pytest.mark.trace("REQ-WP-029")
def test_what_was_written_is_what_the_detector_produced(catalog: Catalog) -> None:
    """Field for field, through the plane and back."""
    from channelflow.extrema import DirectionalChangeDetector

    bars = turning()
    replay(bars, catalog=catalog)

    expected = DirectionalChangeDetector(instrument_id="binance:BTCUSDT", venue_scope="binance")
    expected.run(bars)

    stored = extrema_table.read_confirmed(extrema_table.confirmed_table_for(catalog))
    assert stored == sorted(expected.confirmed, key=lambda e: e.extremum_time_ns)


@pytest.mark.trace("REQ-WP-029")
def test_a_caller_sees_every_extremum_event(catalog: Catalog) -> None:
    """The bus's second producer. Its own note called the first benefit "one
    caller, one capability, proven by tests rather than by use"."""
    seen_confirmed: list[ExtremumConfirmed] = []
    seen_candidates: list[ExtremumObserved] = []
    bus = EventBus()
    bus.subscribe(ExtremumConfirmed, seen_confirmed.append)
    bus.subscribe(ExtremumObserved, seen_candidates.append)

    recording, _ = replay(turning(), catalog=catalog, bus=bus)

    assert len(seen_confirmed) == recording.confirmed_extrema
    assert len(seen_candidates) == recording.extremum_candidates


@pytest.mark.trace("REQ-WP-029")
def test_an_observer_does_not_change_what_is_recorded(tmp_path: Path) -> None:
    bars = turning()
    # Two planes, not one. A single catalog would have the second replay see the
    # first one's rows and skip them all, which is the watermark working and not
    # the property under test.
    plain, _ = replay(bars, catalog=_fresh(tmp_path / "plain"))

    bus = EventBus()
    bus.subscribe(ExtremumConfirmed, lambda _: None)
    observed, _ = replay(bars, catalog=_fresh(tmp_path / "observed"), bus=bus)

    assert observed.confirmed_extrema == plain.confirmed_extrema
    assert observed.dataset == plain.dataset


@pytest.mark.trace("REQ-WP-029")
def test_a_confirmation_arrives_in_its_own_bar_s_turn(catalog: Catalog) -> None:
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

    replay(turning(), catalog=catalog, bus=bus)

    assert "confirmed" in order
    assert "candidate" in order
    # Counted in runs, not by "is it sorted". A flush at the end produces
    # exactly two runs -- every confirmation, then every candidate -- and that
    # sequence is *also* unsorted, so the obvious assertion passes for it. The
    # mutation sweep found that; this counts the alternations instead.
    runs = [kind for kind, _ in groupby(order)]
    assert len(runs) > 2


@pytest.mark.trace("REQ-WP-029")
def test_a_second_replay_writes_no_extrema(catalog: Catalog) -> None:
    """ADR-056 on two more tables."""
    bars = turning()
    first, _ = replay(bars, catalog=catalog)
    second, _ = replay(bars, catalog=catalog)

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
        len(extrema_table.read_confirmed(extrema_table.confirmed_table_for(catalog)))
        == first.confirmed_extrema
    )


@pytest.mark.trace("REQ-WP-029")
def test_a_longer_replay_adds_only_what_is_new(catalog: Catalog) -> None:
    """Idempotence rather than inertia: writing nothing on a re-run is easy if
    you also write nothing on an extension."""
    bars = turning(240)
    replay(bars[:150], catalog=catalog)
    second, _ = replay(bars, catalog=catalog)

    whole = catalog
    replay(bars, catalog=whole)

    assert second.confirmed_extrema > 0
    assert extrema_table.read_confirmed(
        extrema_table.confirmed_table_for(catalog)
    ) == extrema_table.read_confirmed(extrema_table.confirmed_table_for(whole))


@pytest.mark.trace("REQ-WP-029")
def test_a_series_with_no_turn_records_nothing_and_refuses_nothing(
    catalog: Catalog,
) -> None:
    """An absence of turns is a fact about the series."""
    flat = [bar(i, 100.0) for i in range(60)]

    recording, _ = replay(flat, catalog=catalog)

    assert recording.confirmed_extrema == 0


@pytest.mark.trace("REQ-WP-029")
def test_what_the_replay_already_recorded_is_unchanged(catalog: Catalog) -> None:
    """SC-006: the criterion that catches this feature damaging its neighbours."""
    bars = rising_with_rejections()

    recording, report = replay(bars, catalog=catalog)

    assert recording.channel_snapshots > 0
    assert recording.signals == report.candidates_opened
    assert recording.has_dataset
