"""The order-flow features as of a bar's close (REQ-WP-095, spec 147)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.features import book_values as bv
from channelflow.tables.book_minutes import BookMinute

MINUTE = 60_000_000_000
T0 = 1_791_700_000_000_000_000


def minute(
    close: int,
    *,
    frames: int = 100,
    observations: int = 58,
    ofi: str | None = "3",
    di: float | None = 0.25,
    ingest_lag: int = 3_000_000_000,
) -> BookMinute:
    return BookMinute(
        minute_close_ns=close,
        ingest_time_ns=close + ingest_lag,
        frames=frames,
        observations=observations,
        ofi=None if ofi is None else Decimal(ofi),
        depth_imbalance_10=di,
        mid=Decimal(100),
    )


@pytest.mark.trace("REQ-WP-095")
def test_the_value_at_a_close_is_the_latest_minute_that_ended_at_or_before_it() -> None:
    minutes = [
        minute(T0 + 1 * MINUTE, ofi="1"),
        minute(T0 + 2 * MINUTE, ofi="2"),
        minute(T0 + 3 * MINUTE, ofi="3"),
    ]

    values = bv.book_values(minutes, close_ns=T0 + 2 * MINUTE)

    assert values == {"ofi_1m": 2.0, "depth_imbalance_10": 0.25}


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_that_ends_after_the_close_is_not_used() -> None:
    minutes = [minute(T0 + 1 * MINUTE, ofi="1"), minute(T0 + 5 * MINUTE, ofi="999")]
    assert bv.book_values(minutes, close_ns=T0 + 3 * MINUTE)["ofi_1m"] == 1.0
    assert bv.book_values(minutes[1:], close_ns=T0 + 3 * MINUTE) == {}


@pytest.mark.trace("REQ-WP-095")
def test_appending_later_minutes_changes_nothing_at_an_earlier_close() -> None:
    base = [minute(T0 + 1 * MINUTE), minute(T0 + 2 * MINUTE)]
    before = bv.book_values(base, close_ns=T0 + 2 * MINUTE)

    later = [minute(T0 + 3 * MINUTE, ofi="777", di=0.9), minute(T0 + 4 * MINUTE, ofi="888")]

    assert bv.book_values(base + later, close_ns=T0 + 2 * MINUTE) == before


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_with_no_frame_writes_nothing() -> None:
    empty = minute(T0 + MINUTE, frames=0, observations=0, ofi=None, di=None)
    assert bv.book_values([empty], close_ns=T0 + MINUTE) == {}


@pytest.mark.trace("REQ-WP-095")
def test_too_few_observations_means_no_ofi_but_the_depth_imbalance_can_still_stand() -> None:
    thin = minute(T0 + MINUTE, observations=0, ofi=None, di=0.1)
    assert bv.book_values([thin], close_ns=T0 + MINUTE) == {"depth_imbalance_10": 0.1}


@pytest.mark.trace("REQ-WP-095")
def test_a_book_without_ten_levels_has_no_depth_imbalance_but_keeps_its_ofi() -> None:
    shallow = minute(T0 + MINUTE, di=None, ofi="4")
    assert bv.book_values([shallow], close_ns=T0 + MINUTE) == {"ofi_1m": 4.0}


@pytest.mark.trace("REQ-WP-095")
def test_an_ofi_of_exactly_zero_is_a_reading_when_there_were_observations() -> None:
    quiet = minute(T0 + MINUTE, observations=58, ofi="0")
    assert bv.book_values([quiet], close_ns=T0 + MINUTE)["ofi_1m"] == 0.0


@pytest.mark.trace("REQ-WP-095")
def test_a_minute_older_than_two_minutes_at_the_close_is_stale() -> None:
    last = T0 + MINUTE
    inside = last + 2 * MINUTE  # the bound is two minutes
    assert bv.book_values([minute(last)], close_ns=inside) != {}
    assert bv.book_values([minute(last)], close_ns=inside + 1) == {}


@pytest.mark.trace("REQ-WP-095")
def test_no_minutes_is_no_values() -> None:
    assert bv.book_values([], close_ns=T0) == {}


@pytest.mark.trace("REQ-WP-095")
def test_the_precomputed_times_give_the_same_answer() -> None:
    minutes = [minute(T0 + m * MINUTE, ofi=str(m)) for m in range(1, 8)]
    times = [m.minute_close_ns for m in minutes]
    for close in (T0 + 3 * MINUTE, T0 + 7 * MINUTE, T0 + 8 * MINUTE):
        assert bv.book_values(minutes, close_ns=close) == bv.book_values(
            minutes, close_ns=close, times=times
        )
