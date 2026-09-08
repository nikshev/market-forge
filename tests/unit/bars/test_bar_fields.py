"""A bar carries what PRD section 12 says it carries (REQ-WP-005)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import BarBuilder
from tests.unit.bars.conftest import MINUTE_NS, make_trade


def _finalized_single_bar(trades: list, base_ns: int) -> object:
    """Feed trades, then push the watermark past the window and its grace."""
    finalized: list = []
    builder = BarBuilder(timeframe_ns=MINUTE_NS, grace_ns=5_000_000_000, on_final=finalized.append)
    for trade in trades:
        builder.add(trade)
    builder.add(make_trade(event_time_ns=base_ns + 3 * MINUTE_NS, price="1", qty="1"))
    assert finalized, "the bar should have finalized once the watermark passed"
    return finalized[0]


@pytest.mark.trace("REQ-WP-005")
def test_a_bar_carries_every_field_prd_section_12_lists(base_ns: int) -> None:
    """SC-001. Fourteen fields, checked one by one rather than in aggregate."""
    trades = [
        make_trade(event_time_ns=base_ns + 1_000_000_000, price="100", qty="2", side="buy"),
        make_trade(event_time_ns=base_ns + 2_000_000_000, price="110", qty="1", side="sell"),
        make_trade(event_time_ns=base_ns + 3_000_000_000, price="90", qty="3", side="sell"),
        make_trade(event_time_ns=base_ns + 4_000_000_000, price="105", qty="4", side="buy"),
    ]
    bar = _finalized_single_bar(trades, base_ns)

    assert bar.open == Decimal("100")
    assert bar.high == Decimal("110")
    assert bar.low == Decimal("90")
    assert bar.close == Decimal("105")
    assert bar.volume_base == Decimal("10")
    assert (
        bar.volume_quote
        == Decimal("100") * 2 + Decimal("110") + Decimal("90") * 3 + Decimal("105") * 4
    )
    assert bar.trade_count == 4
    assert bar.aggressive_buy_base == Decimal("6")
    assert bar.aggressive_sell_base == Decimal("4")
    assert bar.delta_base == Decimal("2")
    assert bar.high_time_ns == base_ns + 2_000_000_000
    assert bar.low_time_ns == base_ns + 3_000_000_000
    assert bar.first_trade_id == "t-" + str(base_ns + 1_000_000_000)
    assert bar.last_trade_id == "t-" + str(base_ns + 4_000_000_000)
    assert bar.is_final


@pytest.mark.trace("REQ-WP-005")
def test_vwap_is_exact_for_a_price_beyond_double_precision(base_ns: int) -> None:
    """SC-007. VWAP through a float would lose digits the venue sent exactly."""
    price = "50000.123456789012345678901234"
    bar = _finalized_single_bar(
        [make_trade(event_time_ns=base_ns + 1_000_000_000, price=price, qty="1")], base_ns
    )
    assert bar.vwap == Decimal(price)


@pytest.mark.trace("REQ-WP-005")
def test_open_and_close_follow_event_time_not_arrival(base_ns: int) -> None:
    """FR-003. Arrival order is not market information; event time is."""
    late_first = make_trade(event_time_ns=base_ns + 1_000_000_000, price="100", qty="1")
    early_last = make_trade(event_time_ns=base_ns + 9_000_000_000, price="200", qty="1")

    bar = _finalized_single_bar([early_last, late_first], base_ns)
    assert bar.open == Decimal("100"), "open is the earliest trade by event time"
    assert bar.close == Decimal("200"), "close is the latest trade by event time"
