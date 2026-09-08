"""PRD section 14.1's shape features (REQ-WP-012)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import TradeEvent
from channelflow.volume import (
    build,
    distance_to_poc_bps,
    distance_to_vah_bps,
    distance_to_val_bps,
    entropy,
    skew,
)

from .conftest import trade


@pytest.mark.trace("REQ-WP-012")
def test_entropy_is_lower_when_volume_is_concentrated(
    shelved: list[TradeEvent], uniform: list[TradeEvent]
) -> None:
    """SC-006, FR-010. The property that makes the number mean anything."""
    concentrated = entropy(build(shelved, bin_width=Decimal("1")))
    dispersed = entropy(build(uniform, bin_width=Decimal("1")))

    assert concentrated < dispersed


@pytest.mark.trace("REQ-WP-012")
def test_a_single_price_profile_has_zero_entropy() -> None:
    """The spec's first edge case: correct, not degenerate. All the volume
    traded at one price, and there is no uncertainty about where."""
    one = [trade(i, "100.5", "5") for i in range(3)]

    assert entropy(build(one, bin_width=Decimal("1"))) == 0.0


@pytest.mark.trace("REQ-WP-012")
def test_skew_is_positive_with_more_volume_above() -> None:
    """SC-006, FR-010."""
    above = [
        trade(0, "100.5", "10"),
        trade(1, "101.5", "3"),
        trade(2, "102.5", "3"),
    ]
    below = [
        trade(0, "100.5", "3"),
        trade(1, "101.5", "3"),
        trade(2, "102.5", "10"),
    ]

    assert skew(build(above, bin_width=Decimal("1"))) > 0
    assert skew(build(below, bin_width=Decimal("1"))) < 0


@pytest.mark.trace("REQ-WP-012")
def test_a_symmetric_profile_has_no_skew() -> None:
    """The value that makes the sign readable."""
    symmetric = [
        trade(0, "100.5", "3"),
        trade(1, "101.5", "10"),
        trade(2, "102.5", "3"),
    ]

    assert skew(build(symmetric, bin_width=Decimal("1"))) == pytest.approx(0.0)


@pytest.mark.trace("REQ-WP-012")
def test_distances_are_in_basis_points(shelved: list[TradeEvent]) -> None:
    """FR-010. Signed: negative means the level is below the price."""
    profile = build(shelved, bin_width=Decimal("1"), value_area_share=0.9)

    assert distance_to_poc_bps(profile, Decimal("101")) == pytest.approx(
        float((profile.poc.mid - Decimal("101")) / Decimal("101")) * 10_000
    )
    assert distance_to_vah_bps(profile, Decimal("101")) > distance_to_val_bps(
        profile, Decimal("101")
    )


@pytest.mark.trace("REQ-WP-012")
def test_a_non_positive_price_has_no_distance(shelved: list[TradeEvent]) -> None:
    """FR-010. Dividing by it would be a crash or an infinity, and both would
    reach a chart."""
    profile = build(shelved, bin_width=Decimal("1"))

    assert distance_to_poc_bps(profile, Decimal("0")) is None
