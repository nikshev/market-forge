"""Normalization of recorded Binance messages (REQ-WP-003).

This is where Principle I stops being a policy and becomes code: the connector
assigns `event_time`, and every later guarantee about ordering inherits what it
decides here.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from channelflow.connectors.binance import normalize as n
from channelflow.domain import BookDelta, BookSnapshot, DerivativesState, TradeEvent

INGEST = 1788838909900000000


@pytest.mark.trace("REQ-WP-003")
def test_an_aggregate_trade_becomes_a_trade_event(agg_trades: list[dict[str, Any]]) -> None:
    """SC-001, against a real recorded message rather than a written sample."""
    raw = agg_trades[0]
    event = n.agg_trade(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)

    assert isinstance(event, TradeEvent)
    assert event.meta.symbol == raw["s"]
    assert event.trade_id == str(raw["a"])
    assert event.price == Decimal(raw["p"])
    assert event.qty_base == Decimal(raw["q"])
    # `m` is "buyer is market maker": if true the aggressor sold.
    assert event.aggressor_side == ("sell" if raw["m"] else "buy")


@pytest.mark.trace("REQ-WP-003")
def test_a_venue_millisecond_becomes_exact_nanoseconds(agg_trades: list[dict[str, Any]]) -> None:
    """SC-002. Milliseconds to nanoseconds is exact; doing it through a float
    would not be, and a nanosecond lost here is lost everywhere downstream."""
    raw = agg_trades[0]
    event = n.agg_trade(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)
    assert event.meta.event_time_ns == raw["T"] * 1_000_000


@pytest.mark.trace("REQ-WP-003")
def test_the_venue_clock_and_our_clock_stay_apart(agg_trades: list[dict[str, Any]]) -> None:
    """SC-003. PRD section 0.4 forbids conflating these, and section 9 forbids
    any feature using ingest_time as market information. Neither rule survives
    if the connector derives one from the other."""
    raw = agg_trades[0]
    event = n.agg_trade(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)

    assert event.meta.event_time_ns == raw["T"] * 1_000_000
    assert event.meta.ingest_time_ns == INGEST
    assert event.meta.event_time_ns != event.meta.ingest_time_ns


@pytest.mark.trace("REQ-WP-003")
def test_every_recorded_trade_normalizes(agg_trades: list[dict[str, Any]]) -> None:
    """All 15, not just the first -- one lucky message proves nothing."""
    events = [
        n.agg_trade(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)
        for raw in agg_trades
    ]
    assert len(events) == len(agg_trades)
    assert all(e.price > 0 and e.qty_base > 0 for e in events)


@pytest.mark.trace("REQ-WP-003")
def test_a_price_keeps_every_digit_the_venue_sent(agg_trades: list[dict[str, Any]]) -> None:
    """FR-006. The venue sends prices as strings precisely so they can be read
    exactly; parsing through a float would discard that on arrival."""
    raw = dict(agg_trades[0])
    raw["p"] = "78918.012345678901234567"
    event = n.agg_trade(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)
    assert event.price == Decimal("78918.012345678901234567")


@pytest.mark.trace("REQ-WP-003")
def test_a_depth_update_becomes_a_book_delta(depth_updates: list[dict[str, Any]]) -> None:
    raw = depth_updates[0]
    delta = n.depth_update(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)

    assert isinstance(delta, BookDelta)
    assert delta.first_update_id == raw["U"]
    assert delta.final_update_id == raw["u"]
    assert len(delta.bids) == len(raw["b"])
    assert len(delta.asks) == len(raw["a"])


@pytest.mark.trace("REQ-WP-003")
def test_a_rest_snapshot_becomes_a_book_snapshot(depth_snapshot: dict[str, Any]) -> None:
    snap = n.depth_snapshot(
        depth_snapshot,
        venue="binance",
        market_type="spot",
        symbol="BTCUSDT",
        ingest_time_ns=INGEST,
    )
    assert isinstance(snap, BookSnapshot)
    assert snap.update_id == depth_snapshot["lastUpdateId"]
    assert len(snap.bids) == len(depth_snapshot["bids"])


@pytest.mark.trace("REQ-WP-003")
def test_derivatives_state_comes_from_premium_index_and_open_interest(
    premium_index: dict[str, Any], open_interest: dict[str, Any]
) -> None:
    """FR-003. Mark price, index price and funding come from REST here because
    the futures websocket that carries them is unreachable -- see the spec."""
    state = n.derivatives_state(
        premium_index, open_interest, venue="binance", ingest_time_ns=INGEST
    )
    assert isinstance(state, DerivativesState)
    assert state.mark_price == Decimal(premium_index["markPrice"])
    assert state.index_price == Decimal(premium_index["indexPrice"])
    assert state.open_interest_base == pytest.approx(float(open_interest["openInterest"]))


@pytest.mark.trace("REQ-WP-003")
def test_a_missing_field_raises_and_names_it(agg_trades: list[dict[str, Any]]) -> None:
    """FR-007. A venue that changes shape must break the connector on purpose.
    Silently ignoring a field is how a connector passes its tests and reports
    wrong prices."""
    raw = dict(agg_trades[0])
    del raw["p"]
    with pytest.raises(n.NormalizationError, match="p"):
        n.agg_trade(raw, venue="binance", market_type="spot", ingest_time_ns=INGEST)
