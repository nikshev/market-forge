"""Signed trade notional and its running total (REQ-WP-011).

PRD section 15.4: `delta_t = aggressive_buy_notional - aggressive_sell_notional`
and `CVD_t = CVD_{t-1} + delta_t`.

Notional, not base quantity: the PRD says so, and `TradeEvent` carries
`notional_quote` directly, so nothing here has to approximate it by multiplying
size by a price.

CVD-price divergence is absent on purpose -- ADR-013. Section 15.4 names it
without defining it, and four defensible readings give four different numbers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.features.flow import FlowTracker

from .conftest import BASE_NS, SECOND_NS, trade


@pytest.mark.trace("REQ-WP-011")
def test_delta_is_buy_notional_minus_sell_notional() -> None:
    """FR-010, SC-005. 100*2 bought, 100*3 sold: 200 - 300 = -100."""
    tracker = FlowTracker()
    tracker.observe(trade("a", "100", "2", "buy", at_ns=BASE_NS))
    tracker.observe(trade("b", "100", "3", "sell", at_ns=BASE_NS + 1))

    window = tracker.window(SECOND_NS, as_of_ns=BASE_NS + 1)
    assert window.delta == Decimal(-100)
    assert window.volume == Decimal(500)


@pytest.mark.trace("REQ-WP-011")
def test_an_unknown_aggressor_counts_as_volume_and_as_neither_side() -> None:
    """FR-010, SC-005.

    An unknown side is not a zero-sized trade -- it happened, and it moved
    volume. Dropping it would understate volume; guessing a side would invent
    flow. Both errors are invisible in the output.
    """
    tracker = FlowTracker()
    tracker.observe(trade("a", "100", "2", "buy", at_ns=BASE_NS))
    tracker.observe(trade("b", "100", "7", "unknown", at_ns=BASE_NS + 1))

    window = tracker.window(SECOND_NS, as_of_ns=BASE_NS + 1)
    assert window.delta == Decimal(200), "the unknown trade must not change delta"
    assert window.volume == Decimal(900), "but it must count toward volume"


@pytest.mark.trace("REQ-WP-011")
def test_cumulative_delta_is_the_running_sum() -> None:
    """FR-011, SC-005. +200, then -300, then +100: 200, -100, 0."""
    tracker = FlowTracker()
    assert tracker.observe(trade("a", "100", "2", "buy", at_ns=BASE_NS)) == Decimal(200)
    assert tracker.observe(trade("b", "100", "3", "sell", at_ns=BASE_NS + 1)) == Decimal(-100)
    assert tracker.observe(trade("c", "100", "1", "buy", at_ns=BASE_NS + 2)) == Decimal(0)
    assert tracker.cumulative_delta == Decimal(0)


@pytest.mark.trace("REQ-WP-011")
def test_normalized_delta_is_delta_over_the_window_volume() -> None:
    """FR-011. -100 delta over 500 notional = -0.2."""
    tracker = FlowTracker()
    tracker.observe(trade("a", "100", "2", "buy", at_ns=BASE_NS))
    tracker.observe(trade("b", "100", "3", "sell", at_ns=BASE_NS + 1))

    window = tracker.window(SECOND_NS, as_of_ns=BASE_NS + 1)
    assert window.normalized_delta == pytest.approx(-0.2)


@pytest.mark.trace("REQ-WP-011")
def test_a_window_with_no_volume_has_no_normalized_delta() -> None:
    """FR-012. Not zero: zero means balanced flow, and there was no flow.

    A caller that treats a silent minute as perfectly balanced is reading a
    fact that never happened.
    """
    tracker = FlowTracker()
    tracker.observe(trade("a", "100", "2", "buy", at_ns=BASE_NS))

    silent = tracker.window(SECOND_NS, as_of_ns=BASE_NS + 60 * SECOND_NS)
    assert silent.volume == Decimal(0)
    assert silent.normalized_delta is None
    assert silent.delta == Decimal(0)


@pytest.mark.trace("REQ-WP-011")
def test_the_cvd_slope_is_the_change_across_the_window_per_second() -> None:
    """FR-011.

    The window `(as_of - 2s, as_of]` is half-open, so the trade sitting exactly
    on its lower edge is behind it: CVD enters the window at 200 and leaves at
    500, giving 300 over two seconds.

    The second assertion pins that convention. Slope must equal the window's own
    delta per second -- if the boundary were inclusive the two would disagree,
    and the slope would count flow the window does not contain.
    """
    tracker = FlowTracker()
    tracker.observe(trade("a", "100", "2", "buy", at_ns=BASE_NS))
    tracker.observe(trade("b", "100", "3", "buy", at_ns=BASE_NS + 2 * SECOND_NS))

    window = tracker.window(2 * SECOND_NS, as_of_ns=BASE_NS + 2 * SECOND_NS)
    assert window.cvd_slope_per_second == pytest.approx(150.0)
    assert window.cvd_slope_per_second == pytest.approx(float(window.delta) / 2)


@pytest.mark.trace("REQ-WP-011")
def test_acceleration_compares_a_window_with_the_one_before_it() -> None:
    """FR-011. 100/s in the first second, 400/s in the second: +300/s^2."""
    tracker = FlowTracker()
    tracker.observe(trade("a", "100", "1", "buy", at_ns=BASE_NS + SECOND_NS))
    tracker.observe(trade("b", "100", "4", "buy", at_ns=BASE_NS + 2 * SECOND_NS))

    assert tracker.acceleration(SECOND_NS, as_of_ns=BASE_NS + 2 * SECOND_NS) == pytest.approx(300.0)


@pytest.mark.trace("REQ-WP-011")
def test_trades_must_arrive_in_event_time_order() -> None:
    """The spec's fourth edge case.

    A cumulative total that has already been read cannot be rewritten by a late
    arrival -- Principle III. Refusing is the only honest answer; the caller
    knows whether to buffer or to drop.
    """
    tracker = FlowTracker()
    tracker.observe(trade("a", "100", "2", "buy", at_ns=BASE_NS + SECOND_NS))

    with pytest.raises(ValueError, match="event-time order"):
        tracker.observe(trade("b", "100", "2", "buy", at_ns=BASE_NS))


@pytest.mark.trace("REQ-WP-011")
def test_no_divergence_feature_is_exposed() -> None:
    """ADR-013, asserted rather than trusted to a comment.

    Section 15.4 lists five features; four are built. If someone adds a
    divergence later they must revisit the ADR, because this fails first.
    """
    from channelflow.features import flow

    assert not [name for name in flow.FEATURES if "divergence" in name], (
        "a divergence feature appeared; PRD section 15.4 names it but defines "
        "no formula, and ADR-013 is the record of why it was left out"
    )
