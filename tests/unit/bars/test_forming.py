"""The bar still being built, readable without being finished (REQ-WP-102).

A forming bar is for looking at -- the live chart draws it -- and it is never final, never
stored and never an input to a feature. Reading it must not change what the builder goes on to
publish: the final bar of a minute is the same bar whether or not anybody looked at it first.
"""

from __future__ import annotations

import pytest

from channelflow.bars import Bar, BarBuilder
from tests.unit.bars.conftest import MINUTE_NS, make_trade

pytestmark = pytest.mark.trace("REQ-WP-102")


def builder(finalized: list[Bar] | None = None) -> BarBuilder:
    return BarBuilder(
        timeframe_ns=MINUTE_NS,
        grace_ns=5_000_000_000,
        on_final=(finalized.append if finalized is not None else None),
    )


def test_nothing_is_forming_before_the_first_trade() -> None:
    assert builder().forming() == []


def test_the_open_window_is_forming_and_says_it_is_not_final(base_ns: int) -> None:
    b = builder()
    b.add(make_trade(event_time_ns=base_ns + 1_000_000_000, price="100", qty="2", side="buy"))
    b.add(make_trade(event_time_ns=base_ns + 2_000_000_000, price="103", qty="1", side="sell"))
    b.add(make_trade(event_time_ns=base_ns + 3_000_000_000, price="99", qty="1", side="buy"))

    (bar,) = b.forming()

    assert bar.is_final is False
    assert (bar.open_time_ns, bar.close_time_ns) == (base_ns, base_ns + MINUTE_NS)
    assert (str(bar.open), str(bar.high), str(bar.low), str(bar.close)) == (
        "100",
        "103",
        "99",
        "99",
    )
    assert str(bar.volume_base) == "4"
    assert (bar.venue, bar.symbol) == ("binance", "BTCUSDT")


def test_reading_it_changes_nothing_that_is_published_later(base_ns: int) -> None:
    trades = [
        make_trade(event_time_ns=base_ns + s * 1_000_000_000, price=str(100 + s), qty="1")
        for s in range(1, 8)
    ]
    later = make_trade(event_time_ns=base_ns + 2 * MINUTE_NS, price="500", qty="1")

    looked: list[Bar] = []
    plain: list[Bar] = []
    watched, unwatched = builder(looked), builder(plain)
    for trade in trades:
        watched.add(trade)
        watched.forming()
        unwatched.add(trade)
    watched.add(later)
    unwatched.add(later)

    assert looked == plain
    assert looked[0].is_final is True


def test_a_window_that_has_been_finalised_is_no_longer_forming(base_ns: int) -> None:
    b = builder([])
    b.add(make_trade(event_time_ns=base_ns + 1_000_000_000, price="100", qty="1"))
    b.add(make_trade(event_time_ns=base_ns + 2 * MINUTE_NS, price="101", qty="1"))

    assert [bar.open_time_ns for bar in b.forming()] == [base_ns + 2 * MINUTE_NS]


def test_several_open_windows_come_oldest_first(base_ns: int) -> None:
    b = builder([])
    # Within the grace, two windows are open at once.
    b.add(make_trade(event_time_ns=base_ns + MINUTE_NS + 1_000_000_000, price="101", qty="1"))
    b.add(make_trade(event_time_ns=base_ns + MINUTE_NS - 1_000_000_000, price="100", qty="1"))

    assert [bar.open_time_ns for bar in b.forming()] == [base_ns, base_ns + MINUTE_NS]
