"""PRD §17.3's cross-venue basis as a registered feature (REQ-WP-091).

The derivatives package already registers `basis_bps` -- a perpetual's price
against spot -- which is a different quantity from a venue's distance to the
consensus of its own peers. [[REQ-WP-091]] needs the cross-venue one under a
name that cannot be read as the other, so this file pins both the name and the
arithmetic. `FeatureSpec.test_fixture` points here, which is why the registry
assertion below reads its own path.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.features import exposed_feature_names
from channelflow.features.crossvenue_basis import FEATURES, venue_basis_bps
from channelflow.features.registry import REGISTRY

NAME = "venue_basis_bps"
FIXTURE = "tests/unit/features/test_crossvenue_basis.py"


@pytest.mark.trace("REQ-WP-091")
def test_the_module_exposes_exactly_the_basis_feature() -> None:
    assert FEATURES == (NAME,)


@pytest.mark.trace("REQ-WP-091")
def test_the_registry_carries_the_spec() -> None:
    """PRD §19's fields, as this feature states them."""
    spec = REGISTRY[NAME]

    assert spec.name == NAME
    assert spec.family == "cross_venue"
    assert spec.unit == "bps"
    assert spec.cadence == "per final bar"
    assert spec.point_in_time_safe is True
    assert spec.source_events == ("quote",)
    assert spec.formula == "10000 * (mid_i / consensus_mid - 1) at the bar close"
    # Spot and perp are never blended, and the refusal is absence rather than
    # a zero a reader would take for "this venue is exactly on consensus".
    assert "never blended" in spec.description
    assert "never zero-filled" in spec.null_policy


@pytest.mark.trace("REQ-WP-091")
def test_the_basis_is_the_hand_computed_formula() -> None:
    """10000 * (65000 / 65050 - 1) = -10000 / 1301 = -7.686395... bps.

    The mid sits 50 below a 65050 consensus, so the venue is *cheaper* and the
    basis is negative -- the sign a reader of the pane needs to be able to
    reproduce by hand.
    """
    got = venue_basis_bps(Decimal("65000"), Decimal("65050"))

    assert got == pytest.approx(-7.686395080707149, rel=1e-12)
    assert got == float((Decimal("65000") / Decimal("65050") - 1) * 10000)
    assert got < 0


@pytest.mark.trace("REQ-WP-091")
def test_a_consensus_that_is_not_a_price_is_refused() -> None:
    """A zero or negative consensus is not a price; dividing by it would return
    a number whose sign describes the refusal rather than the venue."""
    for consensus in (Decimal("0"), Decimal("-1")):
        with pytest.raises(ValueError):
            venue_basis_bps(Decimal("65000"), consensus)


@pytest.mark.trace("REQ-WP-091")
def test_the_registration_points_at_this_file() -> None:
    assert REGISTRY[NAME].test_fixture == FIXTURE


@pytest.mark.trace("REQ-WP-091")
def test_the_feature_is_exposed_by_the_package() -> None:
    """The `__init__` half of the registration: a spec nobody can reach is
    documentation of a feature no caller can compute."""
    assert NAME in exposed_feature_names()
