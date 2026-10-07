"""`is_gap` decides, from two bars alone, whether a hole sits between them (REQ-WP-087).

FR-001 and FR-006: the detector and the channel each detect a hole from the
bars they are given -- never from a caller's promise that the series is
continuous -- and how many missing bars count as a hole is configuration
(Principle X), not a constant baked into the models.

The rule is `missing = round((next.open_time_ns - prev.close_time_ns) /
timeframe_ns)` and a hole is `missing > threshold`. With the default
threshold of one missing bar bridges, two restart; zero means any positive
distance restarts. A distance that is not a whole number of steps is rounded
rather than floored -- a bar that opens 1.8 steps after the previous close is
two bars late, not one -- and a distance that is zero or negative (a corrected
bar reissued on the previous bar's own timestamps) is not a hole at all, so
`missing` never goes negative.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import Bar
from channelflow.bars.gaps import is_gap

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1_788_838_800_000_000_000

#: prev closes at BASE_NS + MINUTE_NS; every scenario is measured from there.
PREV_OPEN_NS = BASE_NS
PREV_CLOSE_NS = BASE_NS + MINUTE_NS


def bar_at(*, open_ns: int, close_ns: int, tag: str) -> Bar:
    price = Decimal("100")
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_ns,
        close_time_ns=close_ns,
        open=price,
        high=price,
        low=price,
        close=price,
        volume_base=Decimal("1"),
        volume_quote=price,
        trade_count=1,
        aggressive_buy_base=Decimal("1"),
        aggressive_sell_base=Decimal("0"),
        delta_base=Decimal("1"),
        vwap=price,
        high_time_ns=open_ns,
        low_time_ns=open_ns,
        first_trade_id=f"t-{tag}",
        last_trade_id=f"t-{tag}",
        is_final=True,
    )


def prev_bar() -> Bar:
    return bar_at(open_ns=PREV_OPEN_NS, close_ns=PREV_CLOSE_NS, tag="prev")


def next_bar_after(missing_bars: int) -> Bar:
    """The next bar, with `missing_bars` whole slots absent after prev."""
    open_ns = PREV_CLOSE_NS + missing_bars * MINUTE_NS
    return bar_at(open_ns=open_ns, close_ns=open_ns + MINUTE_NS, tag=f"next-{missing_bars}")


@pytest.mark.trace("REQ-WP-087")
def test_contiguous_bars_are_not_a_gap() -> None:
    """FR-001: zero missing bars -- the next bar opens where the previous closed."""
    assert is_gap(prev_bar(), next_bar_after(0), MINUTE_NS, threshold=1) is False


@pytest.mark.trace("REQ-WP-087")
def test_one_missing_bar_bridges_at_the_default_threshold() -> None:
    """FR-006 / SC-003: threshold 1 (the default) lets exactly one missing bar pass."""
    assert is_gap(prev_bar(), next_bar_after(1), MINUTE_NS, threshold=1) is False
    # The default is the deployed default: omitting the argument is not a
    # different policy hiding behind the same name.
    assert is_gap(prev_bar(), next_bar_after(1), MINUTE_NS) is False


@pytest.mark.trace("REQ-WP-087")
def test_two_missing_bars_are_a_gap_at_the_default_threshold() -> None:
    """FR-001 / SC-003: threshold 1 restarts once two bars are missing."""
    assert is_gap(prev_bar(), next_bar_after(2), MINUTE_NS, threshold=1) is True


@pytest.mark.trace("REQ-WP-087")
def test_threshold_zero_restarts_on_any_missing_bar() -> None:
    """FR-006 / SC-003: zero means a single missing bar already ends the run."""
    assert is_gap(prev_bar(), next_bar_after(1), MINUTE_NS, threshold=0) is True
    assert is_gap(prev_bar(), next_bar_after(0), MINUTE_NS, threshold=0) is False


@pytest.mark.trace("REQ-WP-087")
def test_threshold_two_keeps_two_missing_bars_and_restarts_on_three() -> None:
    """FR-006 / US3 acceptance: hole size must exceed the threshold to restart."""
    assert is_gap(prev_bar(), next_bar_after(2), MINUTE_NS, threshold=2) is False
    assert is_gap(prev_bar(), next_bar_after(3), MINUTE_NS, threshold=2) is True


@pytest.mark.trace("REQ-WP-087")
def test_a_corrected_bar_reissued_on_the_previous_timestamps_is_not_a_gap() -> None:
    """Non-positive distance is never a hole, and `missing` never goes negative.

    A correction re-published with the previous bar's own open (or an overlap
    inside the previous bar's window) is data arriving late, not bars absent
    from the middle of the series; counting it as a hole would restart the
    detector over a repair.
    """
    same_open = bar_at(open_ns=PREV_OPEN_NS, close_ns=PREV_OPEN_NS + MINUTE_NS, tag="corrected")
    assert is_gap(prev_bar(), same_open, MINUTE_NS, threshold=1) is False

    overlapping = bar_at(
        open_ns=PREV_CLOSE_NS - MINUTE_NS // 2,
        close_ns=PREV_CLOSE_NS + MINUTE_NS // 2,
        tag="overlap",
    )
    assert is_gap(prev_bar(), overlapping, MINUTE_NS, threshold=0) is False


@pytest.mark.trace("REQ-WP-087")
def test_a_distance_that_is_not_whole_steps_is_rounded_not_floored() -> None:
    """FR-001: 1.4 steps late is one missing bar, 1.6 steps late is two.

    Integer arithmetic keeps the fractions exact so the rounding under test is
    the helper's, not a binary-float artifact of the fixture.
    """
    one_and_two_fifths = PREV_CLOSE_NS + (7 * MINUTE_NS) // 5  # 1.4 steps past close
    bar_14 = bar_at(open_ns=one_and_two_fifths, close_ns=one_and_two_fifths + MINUTE_NS, tag="1-4")
    assert is_gap(prev_bar(), bar_14, MINUTE_NS, threshold=1) is False

    one_and_four_fifths = PREV_CLOSE_NS + (9 * MINUTE_NS) // 5  # 1.8 steps past close
    bar_18 = bar_at(
        open_ns=one_and_four_fifths, close_ns=one_and_four_fifths + MINUTE_NS, tag="1-8"
    )
    assert is_gap(prev_bar(), bar_18, MINUTE_NS, threshold=1) is True


@pytest.mark.trace("REQ-WP-087")
@pytest.mark.parametrize("timeframe_ns", [0, -MINUTE_NS])
def test_a_non_positive_timeframe_is_refused_naming_the_variable(timeframe_ns: int) -> None:
    """A hole measured in steps of zero (or of a negative step) has no meaning."""
    with pytest.raises(ValueError, match="timeframe_ns"):
        is_gap(prev_bar(), next_bar_after(1), timeframe_ns, threshold=1)
