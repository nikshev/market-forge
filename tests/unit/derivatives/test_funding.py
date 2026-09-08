"""PRD section 16.1's funding features (REQ-WP-013, REQ-BIAS-005).

Rule 5 of PRD section 41: "No using current funding settlement before it
becomes known." A rate belongs to the interval *ending* at
`next_funding_time`; before that the venue may revise it.
"""

from __future__ import annotations

import pytest

from channelflow.derivatives import (
    ZScoreUnavailable,
    current_rate,
    funding_acceleration,
    funding_z,
    settled_funding,
)
from channelflow.domain import DerivativesState

from .conftest import BASE_NS, MINUTE_NS, state


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


@pytest.mark.trace("REQ-WP-013")
@pytest.mark.trace("REQ-BIAS-005")
def test_an_unsettled_rate_is_not_used_at_t(settled_history: list[DerivativesState]) -> None:
    """SC-001, FR-001, PRD section 41 rule 5.

    At minute 500 the last interval to have closed is the one ending at 480.
    The state whose interval ends at 540 carries a rate of 0.0099 -- an
    outlier, deliberately, so using it would be obvious in any downstream
    number.
    """
    settled = settled_funding(settled_history, at_ns=at(500))

    assert all(s.settled_at_ns <= at(500) for s in settled)
    assert 0.0099 not in [s.rate for s in settled]
    assert current_rate(settled_history, at_ns=at(500)) == pytest.approx(0.0008)


@pytest.mark.trace("REQ-BIAS-005")
def test_the_unsettled_rate_becomes_usable_once_its_interval_closes(
    settled_history: list[DerivativesState],
) -> None:
    """The other side of the boundary: the rule delays the rate, it does not
    discard it."""
    assert current_rate(settled_history, at_ns=at(600)) == pytest.approx(0.0099)


@pytest.mark.trace("REQ-WP-013")
def test_no_settled_interval_means_no_rate() -> None:
    """The spec's first edge case: no settlement is not a settlement of zero."""
    early = [state(at=0, funding=0.0005, next_funding_at=60)]

    assert current_rate(early, at_ns=at(10)) is None
    assert settled_funding(early, at_ns=at(10)) == []


@pytest.mark.trace("REQ-WP-013")
def test_the_z_score_uses_only_settled_rates(
    settled_history: list[DerivativesState],
) -> None:
    """FR-001 again, through the statistic rather than the raw feature."""
    z = funding_z(settled_history, at_ns=at(500), window=8)

    assert z.observations == 8
    assert z.mean == pytest.approx(0.00045)


@pytest.mark.trace("REQ-WP-013")
def test_a_short_window_refuses(settled_history: list[DerivativesState]) -> None:
    """SC-002, FR-002, ADR-026."""
    with pytest.raises(ZScoreUnavailable, match="needs 24"):
        funding_z(settled_history, at_ns=at(500), window=24)


@pytest.mark.trace("REQ-WP-013")
def test_a_constant_series_has_no_z_score() -> None:
    """SC-002, FR-003, ADR-026.

    Zero is the most meaningful value a z-score can take -- exactly average --
    and a venue reporting an unchanged rate for a week is telling us something
    that "exactly average" would hide.
    """
    flat = [state(at=i * 60, funding=0.0001, next_funding_at=(i + 1) * 60) for i in range(10)]

    with pytest.raises(ZScoreUnavailable, match="constant"):
        funding_z(flat, at_ns=at(1000), window=5)


@pytest.mark.trace("REQ-WP-013")
def test_acceleration_needs_three_intervals(
    settled_history: list[DerivativesState],
) -> None:
    """FR-004. With two it would be the first difference wearing another name,
    which reads as a second signal in a feature list."""
    assert funding_acceleration(settled_history, at_ns=at(130)) is None
    assert funding_acceleration(settled_history, at_ns=at(500)) == pytest.approx(0.0)


@pytest.mark.trace("REQ-WP-013")
def test_acceleration_is_signed() -> None:
    """A rate whose increments are growing accelerates positively."""
    accelerating = [
        state(at=0, funding=0.0001, next_funding_at=60),
        state(at=60, funding=0.0002, next_funding_at=120),
        state(at=120, funding=0.0005, next_funding_at=180),
    ]

    assert funding_acceleration(accelerating, at_ns=at(200)) == pytest.approx(0.0002)
