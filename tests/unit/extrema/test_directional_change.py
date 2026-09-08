"""The two timestamps PRD section 13A.1 exists for (REQ-WP-019).

    extremum_time  when the price made the high
    known_at       when the system could first legally say so

The PRD's own example: a high at 10:00, a reversal threshold crossed at 10:30,
`confirmation_lag = 2 bars`, and "any backtest that acts on the 10:00 label
before 10:30 is invalid".
"""

from __future__ import annotations

import pytest

from channelflow.bars import Bar
from channelflow.extrema import (
    DirectionalChangeDetector,
    ProminenceRule,
    ThresholdMode,
    ThresholdPolicy,
)

from .conftest import BASE_NS, MINUTE_NS, series


def index_of(event_time_ns: int) -> int:
    """Bar index from a close time, so failures read in bar numbers."""
    return (event_time_ns - BASE_NS) // MINUTE_NS - 1


def detector(*, min_bps: float = 200.0, prominence: ProminenceRule | None = None):
    return DirectionalChangeDetector(
        thresholds=ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=min_bps),
        prominence=prominence
        or ProminenceRule(min_prominence_bps=0.0, min_prominence_atr=None, min_bars_between=0),
    )


@pytest.mark.trace("REQ-WP-019")
@pytest.mark.trace("REQ-NRT-C")
def test_a_high_is_dated_to_its_peak_and_known_at_the_crossing(
    peak_then_fall: list[Bar],
) -> None:
    """SC-001.

    The series peaks at 110 on bar 5. With a 200 bps threshold the reversal
    crosses at 107.8, which first happens on bar 8 (107.0). So the high is
    dated to bar 5 and could not be known before bar 8.
    """
    confirmed = detector().run(peak_then_fall)

    assert len(confirmed) == 1
    high = confirmed[0]
    assert high.extremum_type == "HIGH"
    assert index_of(high.extremum_time_ns) == 5
    assert index_of(high.known_at_ns) == 8
    assert float(high.price) == 110.0


@pytest.mark.trace("REQ-WP-019")
def test_the_confirmation_lag_is_the_distance_between_them(
    peak_then_fall: list[Bar],
) -> None:
    """SC-001. PRD section 13A.1 reports the lag in bars."""
    high = detector().run(peak_then_fall)[0]

    assert high.confirmation_lag_bars == 3
    assert high.known_at_ns - high.extremum_time_ns == 3 * MINUTE_NS


@pytest.mark.trace("REQ-WP-019")
def test_a_low_is_detected_symmetrically(trough_then_rise: list[Bar]) -> None:
    """FR-003's other half. A detector handling only one direction would pass
    every test above."""
    confirmed = detector().run(trough_then_rise)

    assert len(confirmed) == 1
    low = confirmed[0]
    assert low.extremum_type == "LOW"
    assert index_of(low.extremum_time_ns) == 5
    assert float(low.price) == 90.0


@pytest.mark.trace("REQ-WP-019")
def test_a_running_high_that_never_reverses_far_enough_confirms_nothing(
    noise: list[Bar],
) -> None:
    """The spec's US1 scenario 3: a running high is not a high.

    Every wiggle in this series is under 1%; a 200 bps threshold sees none of
    them. A detector confirming here would be reporting the noise PRD section
    13A.29 names as its first failure mode.
    """
    assert detector().run(noise) == []


@pytest.mark.trace("REQ-WP-019")
@pytest.mark.trace("REQ-NRT-C")
def test_known_at_is_never_before_extremum_time_over_a_long_series() -> None:
    """SC-002, Test C's first half, over something longer than one fixture.

    A sawtooth of twenty swings, so the property is checked against many
    confirmations rather than one.
    """
    closes: list[float] = []
    price = 100.0
    for swing in range(20):
        step = 1.0 if swing % 2 == 0 else -1.0
        for _ in range(8):
            price *= 1.0 + step * 0.01
            closes.append(price)

    confirmed = detector().run(series(closes))

    assert len(confirmed) > 5, "the fixture must actually produce confirmations"
    for extremum in confirmed:
        assert extremum.known_at_ns >= extremum.extremum_time_ns


@pytest.mark.trace("REQ-WP-019")
def test_the_threshold_in_force_is_stored_on_the_confirmation(
    peak_then_fall: list[Bar],
) -> None:
    """FR-006.

    Stored rather than recomputable: recomputing it later -- for a report, a
    chart, or a backtest -- is exactly how a point-in-time value silently
    becomes a hindsight one.
    """
    high = detector(min_bps=200.0).run(peak_then_fall)[0]

    assert high.threshold_bps == 200.0
    assert high.reversal_bps >= high.threshold_bps


@pytest.mark.trace("REQ-WP-019")
def test_a_record_cannot_be_edited_after_the_fact(peak_then_fall: list[Bar]) -> None:
    """FR-009, PRD section 13A.19: "All models are immutable after
    finalization"."""
    from pydantic import ValidationError

    high = detector().run(peak_then_fall)[0]

    with pytest.raises(ValidationError):
        high.known_at_ns = 0  # type: ignore[misc]


@pytest.mark.trace("REQ-WP-019")
@pytest.mark.trace("REQ-NRT-C")
def test_a_record_claiming_to_be_known_before_it_happened_cannot_be_built() -> None:
    """Test C, enforced by the type rather than by convention.

    A record with `known_at < extremum_time` would let a backtest act on a
    label before it could be known -- PRD section 13A.1's invalid backtest,
    expressed as data.
    """
    from decimal import Decimal

    from channelflow.extrema import ConfirmedExtremum

    with pytest.raises(ValueError, match="known_at"):
        ConfirmedExtremum.create(
            instrument_id="BTCUSDT",
            timeframe_ns=MINUTE_NS,
            extremum_type="HIGH",
            extremum_time_ns=BASE_NS + 10 * MINUTE_NS,
            known_at_ns=BASE_NS + 5 * MINUTE_NS,
            price=Decimal("110"),
            confirmation_method="directional_change",
            confirmation_lag_bars=0,
            reversal_bps=300.0,
            threshold_bps=200.0,
        )
