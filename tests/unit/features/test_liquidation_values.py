"""The liquidation features at a bar's close (REQ-WP-094, spec 146).

Pure: events and heartbeats in, values out. The point of every test is one of two rules. Principle I
-- a value at the close uses only events the stream had delivered by then. And "quiet is a reading
only where the collector was listening": zero liquidated in a window is true if the stream was up
for the whole of it, and a lie otherwise.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import EventMeta, LiquidationEvent
from channelflow.features import liquidation_values as lv

MINUTE = 60_000_000_000
T0 = 1_791_700_000_000_000_000
FEATURES = (
    "liquidation_long_usd_5m",
    "liquidation_short_usd_5m",
    "liquidation_imbalance_5m",
)


def ev(
    at: int,
    side: str,
    usd: str,
    *,
    ingest: int | None = None,
    symbol: str = "BTCUSDT",
) -> LiquidationEvent:
    return LiquidationEvent(
        meta=EventMeta(
            source="binance-ws-liquidation",
            venue="binance",
            market_type="perp",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=at if ingest is None else ingest,
            sequence=None,
            source_event_id=None,
        ),
        side=side,  # type: ignore[arg-type]
        price=Decimal(1),
        qty=Decimal(usd),
        notional_usd=Decimal(usd),
    )


def beats(start_minute: int, end_minute: int) -> list[int]:
    """A heartbeat at the end of every minute from `start_minute` to `end_minute` inclusive."""
    return [T0 + m * MINUTE for m in range(start_minute, end_minute + 1)]


CLOSE = T0 + 30 * MINUTE


@pytest.mark.trace("REQ-WP-094")
def test_the_sums_and_the_imbalance_are_the_librarys_over_the_trailing_five_minutes() -> None:
    events = [
        ev(CLOSE - 4 * MINUTE, "long_liquidated", "300"),
        ev(CLOSE - 2 * MINUTE, "long_liquidated", "100"),
        ev(CLOSE - 1 * MINUTE, "short_liquidated", "100"),
        ev(CLOSE - 6 * MINUTE, "long_liquidated", "9999"),  # outside the window
    ]

    values = lv.liquidation_values(events, beats(0, 30), close_ns=CLOSE)

    assert values["liquidation_long_usd_5m"] == 400.0
    assert values["liquidation_short_usd_5m"] == 100.0
    assert values["liquidation_imbalance_5m"] == pytest.approx((400 - 100) / 500)
    assert set(values) == set(FEATURES)


@pytest.mark.trace("REQ-WP-094")
def test_the_window_is_open_at_the_start_and_closed_at_the_close() -> None:
    at_floor = ev(CLOSE - 5 * MINUTE, "long_liquidated", "1000")
    at_close = ev(CLOSE, "short_liquidated", "10")

    values = lv.liquidation_values([at_floor, at_close], beats(0, 30), close_ns=CLOSE)

    assert values["liquidation_long_usd_5m"] == 0.0
    assert values["liquidation_short_usd_5m"] == 10.0


@pytest.mark.trace("REQ-WP-094")
def test_a_covered_quiet_window_has_zero_sums_and_no_imbalance() -> None:
    values = lv.liquidation_values([], beats(0, 30), close_ns=CLOSE)

    assert values["liquidation_long_usd_5m"] == 0.0
    assert values["liquidation_short_usd_5m"] == 0.0
    assert "liquidation_imbalance_5m" not in values  # zero would read "both sides equally"


@pytest.mark.trace("REQ-WP-094")
def test_a_window_the_stream_did_not_cover_writes_nothing_even_with_events_inside_it() -> None:
    events = [ev(CLOSE - 1 * MINUTE, "long_liquidated", "50")]
    gap = [b for b in beats(0, 30) if not (T0 + 27 * MINUTE <= b <= T0 + 28 * MINUTE)]

    assert lv.liquidation_values(events, gap, close_ns=CLOSE) == {}
    assert lv.liquidation_values(events, [], close_ns=CLOSE) == {}


@pytest.mark.trace("REQ-WP-094")
def test_every_minute_of_the_window_needs_its_heartbeat() -> None:
    five = beats(26, 30)
    assert lv.covered(five, close_ns=CLOSE)
    assert not lv.covered(five[1:], close_ns=CLOSE)  # the first minute has none
    assert not lv.covered(five[:-1], close_ns=CLOSE)  # nor the last
    assert not lv.covered([], close_ns=CLOSE)


@pytest.mark.trace("REQ-WP-094")
def test_two_heartbeats_in_one_minute_do_not_stand_in_for_two_minutes() -> None:
    doubled = beats(26, 29) + [CLOSE - 10, CLOSE]  # the last minute has two heartbeats
    assert lv.covered(doubled, close_ns=CLOSE)
    short = sorted([CLOSE - 10, CLOSE] + beats(26, 27))
    assert not lv.covered(short, close_ns=CLOSE)


@pytest.mark.trace("REQ-WP-094")
def test_events_delivered_after_the_close_are_not_used() -> None:
    known = ev(CLOSE - 2 * MINUTE, "long_liquidated", "100")
    late = ev(CLOSE - 1 * MINUTE, "short_liquidated", "900", ingest=CLOSE + 3 * MINUTE)

    values = lv.liquidation_values([known, late], beats(0, 30), close_ns=CLOSE)

    assert values["liquidation_short_usd_5m"] == 0.0
    assert values["liquidation_long_usd_5m"] == 100.0


@pytest.mark.trace("REQ-WP-094")
def test_appending_later_events_and_heartbeats_changes_nothing() -> None:
    base = [ev(CLOSE - 2 * MINUTE, "long_liquidated", "100")]
    before = lv.liquidation_values(base, beats(0, 30), close_ns=CLOSE)

    later = [
        ev(CLOSE + 1 * MINUTE, "short_liquidated", "7777"),
        ev(CLOSE + 5, "long_liquidated", "1"),
    ]

    assert lv.liquidation_values(base + later, beats(0, 60), close_ns=CLOSE) == before


@pytest.mark.trace("REQ-WP-094")
def test_an_event_dated_after_the_close_by_a_fast_venue_clock_is_not_used() -> None:
    ahead = ev(CLOSE + 1 * MINUTE, "short_liquidated", "500", ingest=CLOSE - 1)
    values = lv.liquidation_values([ahead], beats(0, 30), close_ns=CLOSE)
    assert values["liquidation_short_usd_5m"] == 0.0


@pytest.mark.trace("REQ-WP-094")
def test_unknown_side_events_are_in_neither_sum() -> None:
    values = lv.liquidation_values(
        [ev(CLOSE - MINUTE, "unknown", "500"), ev(CLOSE - MINUTE, "long_liquidated", "50")],
        beats(0, 30),
        close_ns=CLOSE,
    )
    assert values["liquidation_long_usd_5m"] == 50.0 and values["liquidation_short_usd_5m"] == 0.0
