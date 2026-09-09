"""PRD section 40's signal outcomes and section 25.4's fills (REQ-BT-001)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.backtest.fills import (
    NoFillAvailable,
    market_at_next_open,
    market_at_signal_close,
)
from channelflow.backtest.outcomes import (
    HorizonUnavailable,
    Outcome,
    resolve_outcome,
)
from channelflow.bars import Bar

from .conftest import bar


def ohlc(index: int, *, open_: float, high: float, low: float, close: float) -> Bar:
    """A bar with a real range, unlike the flat helper the other tests use."""
    return bar(index, close).model_copy(
        update={
            "open": Decimal(str(open_)),
            "high": Decimal(str(high)),
            "low": Decimal(str(low)),
            "close": Decimal(str(close)),
        }
    )


@pytest.mark.trace("REQ-BT-001")
def test_a_target_reached_first_is_a_target() -> None:
    """SC-001, FR-001, FR-002."""
    bars = [
        ohlc(0, open_=100.0, high=101.0, low=99.5, close=100.5),
        ohlc(1, open_=100.5, high=105.0, low=100.0, close=104.0),
        ohlc(2, open_=104.0, high=106.0, low=103.0, close=105.0),
    ]

    outcome = resolve_outcome(
        bars,
        entry_index=0,
        fill_price=100.0,
        target=105.0,
        stop=95.0,
        direction="long",
        horizon_bars=2,
    )

    assert outcome.outcome is Outcome.TARGET
    assert outcome.first_target_time_ns == bars[1].close_time_ns
    assert outcome.first_invalidation_time_ns is None


@pytest.mark.trace("REQ-BT-001")
def test_a_stop_reached_first_is_a_stop() -> None:
    """SC-001, FR-002."""
    bars = [
        ohlc(0, open_=100.0, high=101.0, low=99.5, close=100.0),
        ohlc(1, open_=100.0, high=100.5, low=94.0, close=95.0),
        ohlc(2, open_=95.0, high=106.0, low=95.0, close=105.0),
    ]

    outcome = resolve_outcome(
        bars,
        entry_index=0,
        fill_price=100.0,
        target=105.0,
        stop=95.0,
        direction="long",
        horizon_bars=2,
    )

    assert outcome.outcome is Outcome.STOP
    assert outcome.first_invalidation_time_ns == bars[1].close_time_ns


@pytest.mark.trace("REQ-BT-001")
def test_neither_touched_is_a_timeout_with_its_horizon_return() -> None:
    """SC-001, FR-002, FR-006."""
    bars = [
        ohlc(0, open_=100.0, high=100.5, low=99.5, close=100.0),
        ohlc(1, open_=100.0, high=101.0, low=99.0, close=100.5),
        ohlc(2, open_=100.5, high=102.0, low=100.0, close=101.0),
    ]

    outcome = resolve_outcome(
        bars,
        entry_index=0,
        fill_price=100.0,
        target=105.0,
        stop=95.0,
        direction="long",
        horizon_bars=2,
    )

    assert outcome.outcome is Outcome.TIMEOUT
    assert outcome.return_h == pytest.approx(0.01)
    assert outcome.mfe_pct == pytest.approx(0.02)
    assert outcome.mae_pct == pytest.approx(-0.01)


@pytest.mark.trace("REQ-BT-001")
def test_a_bar_containing_both_levels_is_ambiguous() -> None:
    """SC-002, FR-003.

    PRD §40, emphasised in the section itself: "never choose the favorable
    ordering". This is the single place a backtest can flatter itself with both
    readings looking plausible -- and only one of them profitable.
    """
    bars = [
        ohlc(0, open_=100.0, high=100.5, low=99.5, close=100.0),
        ohlc(1, open_=100.0, high=106.0, low=94.0, close=100.0),
    ]

    outcome = resolve_outcome(
        bars,
        entry_index=0,
        fill_price=100.0,
        target=105.0,
        stop=95.0,
        direction="long",
        horizon_bars=1,
    )

    assert outcome.outcome is Outcome.AMBIGUOUS


@pytest.mark.trace("REQ-BT-001")
def test_an_ambiguous_outcome_claims_neither_touch_time() -> None:
    """SC-002, FR-004.

    Recording a target time on an ambiguous bar is choosing the ordering in a
    field instead of in the verdict.
    """
    bars = [
        ohlc(0, open_=100.0, high=100.5, low=99.5, close=100.0),
        ohlc(1, open_=100.0, high=106.0, low=94.0, close=100.0),
    ]

    outcome = resolve_outcome(
        bars,
        entry_index=0,
        fill_price=100.0,
        target=105.0,
        stop=95.0,
        direction="long",
        horizon_bars=1,
    )

    assert outcome.first_target_time_ns is None
    assert outcome.first_invalidation_time_ns is None


@pytest.mark.trace("REQ-BT-001")
def test_a_touch_at_exactly_the_level_counts() -> None:
    """SC-003, FR-005.

    Requiring a strict breach is choosing the favourable ordering by one tick,
    every time, on every trade.
    """
    bars = [
        ohlc(0, open_=100.0, high=100.5, low=99.5, close=100.0),
        ohlc(1, open_=100.0, high=105.0, low=99.0, close=104.0),
    ]

    outcome = resolve_outcome(
        bars,
        entry_index=0,
        fill_price=100.0,
        target=105.0,
        stop=95.0,
        direction="long",
        horizon_bars=1,
    )

    assert outcome.outcome is Outcome.TARGET


@pytest.mark.trace("REQ-BT-001")
def test_a_short_resolves_by_its_own_direction() -> None:
    """FR-002.

    A short's target is below the fill and its stop above. Resolved with the
    long's comparisons, every short reads as an immediate stop.
    """
    bars = [
        ohlc(0, open_=100.0, high=100.5, low=99.5, close=100.0),
        ohlc(1, open_=100.0, high=100.5, low=94.0, close=95.0),
    ]

    outcome = resolve_outcome(
        bars,
        entry_index=0,
        fill_price=100.0,
        target=95.0,
        stop=105.0,
        direction="short",
        horizon_bars=1,
    )

    assert outcome.outcome is Outcome.TARGET
    assert outcome.return_h == pytest.approx(0.05)


@pytest.mark.trace("REQ-BT-001")
def test_a_horizon_past_the_data_is_refused() -> None:
    """SC-004, FR-007.

    An unfinished horizon is not a timeout: the answer may be in the bars that
    do not exist yet, and recording absence as evidence teaches every study that
    the end of the dataset is calm.
    """
    bars = [ohlc(0, open_=100.0, high=101.0, low=99.0, close=100.0)]

    with pytest.raises(HorizonUnavailable):
        resolve_outcome(
            bars,
            entry_index=0,
            fill_price=100.0,
            target=105.0,
            stop=95.0,
            direction="long",
            horizon_bars=5,
        )


@pytest.mark.trace("REQ-BT-001")
def test_the_next_open_fill_is_the_next_bars_open() -> None:
    """SC-005, FR-008.

    §25.4's first phase-1 model. A fill at the signal's own close is a fill at a
    price that was already gone when the decision was made.
    """
    bars = [
        ohlc(0, open_=100.0, high=101.0, low=99.0, close=100.5),
        ohlc(1, open_=102.0, high=103.0, low=101.0, close=102.5),
    ]

    fill = market_at_next_open(bars, signal_index=0)

    assert fill.price == pytest.approx(102.0)
    assert fill.model == "market_at_next_bar_open"


@pytest.mark.trace("REQ-BT-001")
def test_the_next_open_fill_refuses_without_a_next_bar() -> None:
    """SC-005, FR-008.

    Falling back to the close would fill the last signal of every dataset at a
    better price than any other -- a bias that grows with how recently the
    backtest ends.
    """
    bars = [ohlc(0, open_=100.0, high=101.0, low=99.0, close=100.5)]

    with pytest.raises(NoFillAvailable):
        market_at_next_open(bars, signal_index=0)


@pytest.mark.trace("REQ-BT-001")
@pytest.mark.parametrize(
    ("direction", "expected"),
    [("long", 100.5 * 1.001), ("short", 100.5 * 0.999)],
)
def test_slippage_moves_the_fill_against_the_trade(direction: str, expected: float) -> None:
    """SC-006, FR-009.

    §25.4's second phase-1 model. Slippage that helps is not slippage.
    """
    bars = [ohlc(0, open_=100.0, high=101.0, low=99.0, close=100.5)]

    fill = market_at_signal_close(bars, signal_index=0, direction=direction, slippage_bps=10.0)

    assert fill.price == pytest.approx(expected)


@pytest.mark.trace("REQ-BT-001")
def test_the_phase_two_fills_are_named_as_unbuilt() -> None:
    """FR-010.

    §25.4 lists four models across two phases. A module silent about the other
    two reads as the section, implemented.
    """
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3] / "src" / "channelflow" / "backtest" / "fills.py"
    ).read_text()

    assert "trade-through limit" in source
    assert "L2-aware" in source
