"""PRD section 13A.6's prominence filter (REQ-WP-019).

"Noise can create many tiny extrema." Section 13A.29's first named failure mode
is tiny noisy pivots generating alert spam.
"""

from __future__ import annotations

import pytest

from channelflow.extrema import (
    DirectionalChangeDetector,
    ProminenceRule,
    ThresholdMode,
    ThresholdPolicy,
    prominence_bps,
)

from .conftest import series


def detector(rule: ProminenceRule) -> DirectionalChangeDetector:
    return DirectionalChangeDetector(
        thresholds=ThresholdPolicy(mode=ThresholdMode.FIXED_BPS, min_bps=150.0),
        prominence=rule,
    )


#: Two swings: a small one of about 2%, then a large one of about 12%.
SMALL_THEN_LARGE = [
    100.0,
    101.0,
    102.0,
    101.0,
    100.0,
    102.0,
    106.0,
    110.0,
    114.0,
    112.0,
    108.0,
    104.0,
    100.0,
]


@pytest.mark.trace("REQ-WP-019")
def test_prominence_is_the_excursion_from_the_baseline() -> None:
    """FR-007. Hand-computed: 110 against a baseline of 100 is 1000 bps."""
    assert prominence_bps(110.0, 100.0) == pytest.approx(1000.0)
    assert prominence_bps(90.0, 100.0) == pytest.approx(1000.0)


@pytest.mark.trace("REQ-WP-019")
def test_a_swing_below_the_minimum_prominence_is_not_confirmed() -> None:
    """SC-004, FR-008. The small swing is filtered; the large one is not."""
    permissive = detector(
        ProminenceRule(min_prominence_bps=0.0, min_prominence_atr=None, min_bars_between=0)
    ).run(series(SMALL_THEN_LARGE))
    selective = detector(
        ProminenceRule(min_prominence_bps=500.0, min_prominence_atr=None, min_bars_between=0)
    ).run(series(SMALL_THEN_LARGE))

    assert len(permissive) > len(selective), "the filter must actually remove something"
    assert all(e.prominence_bps is not None and e.prominence_bps >= 500.0 for e in selective)


@pytest.mark.trace("REQ-WP-019")
def test_two_extrema_too_close_together_are_rejected() -> None:
    """FR-008, PRD section 13A.6's own example:

    prominence_atr >= 0.8 AND bars_since_previous_extremum >= 3
    """
    rule = ProminenceRule(min_prominence_bps=0.0, min_prominence_atr=None, min_bars_between=8)

    assert not rule.accepts(prominence_bps=900.0, prominence_atr=None, bars_since_previous=2)
    assert rule.accepts(prominence_bps=900.0, prominence_atr=None, bars_since_previous=9)


@pytest.mark.trace("REQ-WP-019")
def test_the_first_extremum_has_no_predecessor_to_be_too_close_to() -> None:
    """`None` means there is no previous extremum, which cannot be too near.
    Treating it as zero would suppress the first confirmation of every run."""
    rule = ProminenceRule(min_prominence_bps=0.0, min_prominence_atr=None, min_bars_between=8)

    assert rule.accepts(prominence_bps=900.0, prominence_atr=None, bars_since_previous=None)


@pytest.mark.trace("REQ-WP-019")
def test_the_atr_criterion_applies_only_when_atr_is_known() -> None:
    """FR-007. An unknown ATR is not a failing one: rejecting on absent data
    would silence the detector wherever ATR has too little history."""
    rule = ProminenceRule(min_prominence_bps=0.0, min_prominence_atr=0.8, min_bars_between=0)

    assert rule.accepts(prominence_bps=900.0, prominence_atr=None, bars_since_previous=None)
    assert not rule.accepts(prominence_bps=900.0, prominence_atr=0.2, bars_since_previous=None)
