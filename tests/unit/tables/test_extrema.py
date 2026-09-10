"""Extrema on the canonical plane (REQ-WP-028)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from channelflow.extrema.models import ConfirmedExtremum, ExtremumCandidate
from channelflow.lakehouse import InMemoryObjectStore
from channelflow.tables import extrema as extrema_table

SECOND = 1_000_000_000
BASE = 1_788_838_800_000_000_000


def confirmed(
    *,
    turn_at: int,
    known_at: int,
    kind: str = "HIGH",
    prominence: float | None = 12.5,
    source: uuid.UUID | None = None,
) -> ConfirmedExtremum:
    return ConfirmedExtremum(
        extremum_id=uuid.uuid5(uuid.NAMESPACE_OID, f"{turn_at}:{known_at}"),
        instrument_id="binance:BTCUSDT",
        timeframe_ns=60 * SECOND,
        extremum_type=kind,  # type: ignore[arg-type]
        extremum_time_ns=BASE + turn_at * SECOND,
        known_at_ns=BASE + known_at * SECOND,
        price=Decimal("112000.10"),
        confirmation_method="directional_change",
        confirmation_lag_bars=known_at - turn_at,
        reversal_bps=45.0,
        threshold_bps=30.0,
        prominence_bps=prominence,
        prominence_atr=None,
        channel_class="upper",
        source_candidate_id=source,
    )


def candidate(*, at: int, observed: int) -> ExtremumCandidate:
    return ExtremumCandidate(
        candidate_id=uuid.uuid5(uuid.NAMESPACE_OID, f"cand:{at}"),
        instrument_id="binance:BTCUSDT",
        venue_scope="binance",
        timeframe_ns=60 * SECOND,
        candidate_type="HIGH",
        candidate_time_ns=BASE + at * SECOND,
        observed_at_ns=BASE + observed * SECOND,
        price=Decimal("112000.10"),
        method="directional_change",
        structural_score=0.5,
        channel_position=None,
        data_quality="ok",
    )


@pytest.fixture
def store() -> InMemoryObjectStore:
    return InMemoryObjectStore()


@pytest.mark.trace("REQ-WP-028")
def test_a_confirmation_reads_back_field_for_field(store: InMemoryObjectStore) -> None:
    table = extrema_table.confirmed_table_for(store)
    original = confirmed(turn_at=10, known_at=14)

    extrema_table.write_confirmed(table, [original])

    assert extrema_table.read_confirmed(table) == [original]


@pytest.mark.trace("REQ-WP-028")
def test_a_candidate_reads_back_field_for_field(store: InMemoryObjectStore) -> None:
    table = extrema_table.candidates_table_for(store)
    original = candidate(at=10, observed=12)

    extrema_table.write_candidates(table, [original])

    assert extrema_table.read_candidates(table) == [original]


@pytest.mark.trace("REQ-WP-028")
def test_an_absent_prominence_is_absent_not_zero(store: InMemoryObjectStore) -> None:
    """A prominence of zero is a real reading. A sentinel would make an
    unmeasured turn and a flat one the same row, which is the distinction this
    repository has had to draw in four other places."""
    table = extrema_table.confirmed_table_for(store)
    extrema_table.write_confirmed(
        table,
        [
            confirmed(turn_at=1, known_at=2, prominence=None),
            confirmed(turn_at=3, known_at=4, prominence=0.0),
        ],
    )

    read = extrema_table.read_confirmed(table)

    assert read[0].prominence_bps is None
    assert read[1].prominence_bps == 0.0


@pytest.mark.trace("REQ-WP-028")
def test_a_turn_is_not_returned_before_it_was_confirmed(store: InMemoryObjectStore) -> None:
    """PRD section 45's Phase 1A acceptance, at the layer that can enforce it.

    The turn happened at second 10 and was confirmed at second 14. A read as of
    second 13 that returned it would be the chart claiming the system knew about
    a turn before it did -- the repaint section 13A.1 forbids.
    """
    table = extrema_table.confirmed_table_for(store)
    extrema_table.write_confirmed(table, [confirmed(turn_at=10, known_at=14)])

    assert extrema_table.read_confirmed(table, as_of_ns=BASE + 13 * SECOND) == []
    assert len(extrema_table.read_confirmed(table, as_of_ns=BASE + 14 * SECOND)) == 1


@pytest.mark.trace("REQ-WP-028")
def test_a_returned_turn_still_carries_the_instant_it_happened(
    store: InMemoryObjectStore,
) -> None:
    """The other half. A confirmation drawn at its `known_at` never appears too
    early and is also not where the turn was -- which satisfies the criterion
    and draws the wrong picture."""
    table = extrema_table.confirmed_table_for(store)
    extrema_table.write_confirmed(table, [confirmed(turn_at=10, known_at=14)])

    (found,) = extrema_table.read_confirmed(table, as_of_ns=BASE + 20 * SECOND)

    assert found.extremum_time_ns == BASE + 10 * SECOND
    assert found.known_at_ns == BASE + 14 * SECOND


@pytest.mark.trace("REQ-WP-028")
def test_a_candidate_is_not_returned_before_it_was_observed(
    store: InMemoryObjectStore,
) -> None:
    """The criterion names confirmations only. A candidate leaking in early is
    the same defect under a different name, and nothing in the PRD would have
    caught it."""
    table = extrema_table.candidates_table_for(store)
    extrema_table.write_candidates(table, [candidate(at=10, observed=12)])

    assert extrema_table.read_candidates(table, as_of_ns=BASE + 11 * SECOND) == []
    assert len(extrema_table.read_candidates(table, as_of_ns=BASE + 12 * SECOND)) == 1


@pytest.mark.trace("REQ-WP-028")
def test_later_data_does_not_change_what_an_earlier_instant_shows(
    store: InMemoryObjectStore,
) -> None:
    """Principle III. The plane is append-only and its snapshots are immutable,
    so this is a property to confirm rather than to build -- and confirming it
    is what makes the chart's claim about the past worth anything."""
    table = extrema_table.confirmed_table_for(store)
    extrema_table.write_confirmed(table, [confirmed(turn_at=10, known_at=14)])
    before = extrema_table.read_confirmed(table, as_of_ns=BASE + 20 * SECOND)

    extrema_table.write_confirmed(table, [confirmed(turn_at=30, known_at=34)])

    assert extrema_table.read_confirmed(table, as_of_ns=BASE + 20 * SECOND) == before


@pytest.mark.trace("REQ-WP-028")
def test_one_instrument_does_not_return_another_s(store: InMemoryObjectStore) -> None:
    table = extrema_table.confirmed_table_for(store)
    other = confirmed(turn_at=10, known_at=14).model_copy(
        update={"instrument_id": "binance:ETHUSDT"}
    )
    extrema_table.write_confirmed(table, [confirmed(turn_at=10, known_at=14), other])

    found = extrema_table.read_confirmed(table, instrument_id="binance:ETHUSDT")

    assert [e.instrument_id for e in found] == ["binance:ETHUSDT"]


@pytest.mark.trace("REQ-WP-028")
def test_turns_come_back_oldest_first(store: InMemoryObjectStore) -> None:
    table = extrema_table.confirmed_table_for(store)
    extrema_table.write_confirmed(
        table, [confirmed(turn_at=30, known_at=32), confirmed(turn_at=10, known_at=14)]
    )

    found = extrema_table.read_confirmed(table)

    assert [e.extremum_time_ns for e in found] == [BASE + 10 * SECOND, BASE + 30 * SECOND]
