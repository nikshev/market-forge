"""PRD section 13A.5's five threshold modes (REQ-WP-019).

"The threshold must be point-in-time and cannot be retroactively optimized per
swing." Section 13A.29's second failure mode is a fixed threshold failing
across volatility regimes, which is why four of the five adapt.
"""

from __future__ import annotations

import pytest

from channelflow.extrema import ThresholdMode, ThresholdPolicy, ThresholdUnavailable

from .conftest import BASE_NS, MINUTE_NS, bar, series


def flat(count: int, price: float = 100.0) -> list:
    return series([price] * count)


def volatile(count: int, *, swing: float = 0.05, start: int = 0) -> list:
    """`start` matters: bars appended "later" must actually carry later
    timestamps. Reusing indices from zero produced a series that overlapped the
    one it was appended to, and the point-in-time test below silently checked
    nothing."""
    return [bar(start + i, 100.0 * (1.0 + (swing if i % 2 == 0 else -swing))) for i in range(count)]


@pytest.mark.trace("REQ-WP-019")
def test_the_fixed_mode_returns_its_configured_value() -> None:
    """FR-005. The only mode that ignores the market, and the one PRD section
    13A.29 warns about."""
    policy = ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=150.0)

    assert policy.at(flat(40), as_of_ns=BASE_NS + 40 * MINUTE_NS) == 150.0


@pytest.mark.trace("REQ-WP-019")
def test_the_atr_mode_rises_with_volatility() -> None:
    """FR-005, SC-003. The property that makes it adaptive at all."""
    policy = ThresholdPolicy(mode=ThresholdMode.ATR_MULTIPLE, atr_period=5)

    calm = policy.at(flat(40), as_of_ns=BASE_NS + 40 * MINUTE_NS)
    rough = policy.at(volatile(40), as_of_ns=BASE_NS + 40 * MINUTE_NS)

    assert rough > calm


@pytest.mark.trace("REQ-WP-019")
def test_the_realized_vol_mode_rises_with_volatility() -> None:
    """FR-005."""
    policy = ThresholdPolicy(mode=ThresholdMode.REALIZED_VOL_MULTIPLE, vol_period=5)

    calm = policy.at(flat(40), as_of_ns=BASE_NS + 40 * MINUTE_NS)
    rough = policy.at(volatile(40), as_of_ns=BASE_NS + 40 * MINUTE_NS)

    assert rough > calm
    assert calm == 0.0, "a flat series has no realized volatility"


@pytest.mark.trace("REQ-WP-019")
def test_the_channel_width_mode_is_a_fraction_of_the_width() -> None:
    """FR-005. Hand-computed: a quarter of a 2% channel is 50 bps.

    The width arrives as a percentage, in `ChannelSnapshot.width_pct`'s own
    units -- 2.0 for a two-percent channel. Read as a fraction of price instead,
    a real channel width produces a threshold a hundred times too wide and the
    detector silently stops confirming.
    """
    policy = ThresholdPolicy(mode=ThresholdMode.CHANNEL_WIDTH_FRACTION, channel_width_fraction=0.25)

    threshold = policy.at(flat(40), as_of_ns=BASE_NS + 40 * MINUTE_NS, channel_width_pct=2.0)

    assert threshold == pytest.approx(50.0)


@pytest.mark.trace("REQ-WP-019")
def test_the_channel_mode_refuses_without_a_channel() -> None:
    """The spec's third edge case, at the threshold level."""
    policy = ThresholdPolicy(mode=ThresholdMode.CHANNEL_WIDTH_FRACTION)

    with pytest.raises(ThresholdUnavailable, match="channel width"):
        policy.at(flat(40), as_of_ns=BASE_NS + 40 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-019")
def test_the_hybrid_is_the_maximum_and_never_below_the_floor() -> None:
    """FR-005, PRD section 13A.5's own formula:

    theta_t = max(min_bps, atr_multiplier * ATR_t / price_t,
                  vol_multiplier * realized_vol_t)
    """
    policy = ThresholdPolicy(mode=ThresholdMode.HYBRID, min_bps=300.0, atr_period=5, vol_period=5)

    calm = policy.at(flat(40), as_of_ns=BASE_NS + 40 * MINUTE_NS)
    assert calm == 300.0, "a flat market falls back to the floor"

    rough = policy.at(volatile(40), as_of_ns=BASE_NS + 40 * MINUTE_NS)
    assert rough > 300.0, "a volatile market lifts it above the floor"


@pytest.mark.trace("REQ-WP-019")
def test_a_threshold_uses_only_bars_at_or_before_the_instant() -> None:
    """FR-006, Principle I.

    The filtering happens inside the policy, for the same reason REQ-WP-006's
    fitter filters its own window: a caller who passes later bars must get the
    same answer as one who does not. Otherwise every call site has to remember,
    and one will not.
    """
    early = flat(40)
    later = [*early, *volatile(40, start=40)]
    policy = ThresholdPolicy(mode=ThresholdMode.HYBRID, atr_period=5, vol_period=5)

    at_t = BASE_NS + 40 * MINUTE_NS
    assert policy.at(early, as_of_ns=at_t) == policy.at(later, as_of_ns=at_t)


@pytest.mark.trace("REQ-WP-019")
def test_too_little_history_refuses_rather_than_approximating() -> None:
    """The spec's third edge case.

    A threshold computed over fewer bars than configured is a different
    threshold wearing the same name, and a confirmation resting on it could not
    be reproduced -- REQ-WP-006's reasoning about short fits, here.
    """
    policy = ThresholdPolicy(mode=ThresholdMode.ATR_MULTIPLE, atr_period=14)

    with pytest.raises(ThresholdUnavailable, match="ATR needs"):
        policy.at(flat(5), as_of_ns=BASE_NS + 5 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-019")
def test_the_hybrid_survives_a_component_without_history() -> None:
    """The hybrid must still answer early in a stream: the floor applies, and
    the alternative is no threshold at all until the longest window fills."""
    policy = ThresholdPolicy(mode=ThresholdMode.HYBRID, min_bps=250.0, atr_period=14)

    assert policy.at(flat(3), as_of_ns=BASE_NS + 3 * MINUTE_NS) == 250.0
