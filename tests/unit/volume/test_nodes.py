"""PRD section 14.1's high- and low-volume nodes (REQ-WP-012)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.domain import TradeEvent
from channelflow.volume import build, nodes, nodes_at

from .conftest import trade


@pytest.mark.trace("REQ-WP-012")
def test_a_shelf_is_a_high_volume_node(shelved: list[TradeEvent]) -> None:
    """SC-005, FR-008. The 20-volume bin against neighbours averaging 1.75."""
    found = nodes(build(shelved, bin_width=Decimal("1")))

    high = [n for n in found if n.kind == "HVN"]
    assert len(high) == 1
    assert high[0].bin.volume == Decimal("20")
    assert high[0].ratio_to_neighbours > 1.8


@pytest.mark.trace("REQ-WP-012")
def test_a_gap_is_a_low_volume_node() -> None:
    """SC-005, FR-008. A thin bin between two busy ones."""
    with_gap = [
        trade(0, "100.5", "20"),
        trade(1, "101.5", "1"),
        trade(2, "102.5", "20"),
    ]

    found = nodes(build(with_gap, bin_width=Decimal("1")))

    low = [n for n in found if n.kind == "LVN"]
    assert len(low) == 1
    assert low[0].bin.volume == Decimal("1")


@pytest.mark.trace("REQ-WP-012")
def test_a_uniform_profile_has_no_nodes(uniform: list[TradeEvent]) -> None:
    """SC-005, FR-009.

    A flat profile has no structure to report. A detector without this
    property flags every second bin, and then nothing is a node.
    """
    assert nodes(build(uniform, bin_width=Decimal("1"))) == ()


@pytest.mark.trace("REQ-WP-012")
def test_nodes_are_relative_to_neighbours_not_to_the_whole_profile(
    ramp: list[TradeEvent],
) -> None:
    """FR-008, and the test that discriminates.

    Ten bins rising 1 to 10. No bin is 1.8x its immediate neighbours, so
    nothing here is a shelf. Measured against the profile's own mean of 5.5,
    the top bin is 1.8x and the bottom is 0.18x -- so a detector comparing to
    the global average reports two nodes on a smooth ramp, which has none.

    The `shelved` fixture is five bins long and the neighbour window is two
    either side, so there the two rules see the same data and a mutation
    between them survives.

    `low_multiple` is loosened from its default here on purpose. The first bin
    has neighbours on one side only, so its ratio is 1 / mean(2, 3) = 0.4 --
    exactly the default threshold, and flagged by an edge effect rather than by
    structure. Isolating the property under test means stepping past that.
    """
    profile = build(ramp, bin_width=Decimal("1"))

    assert nodes(profile, low_multiple=0.3) == (), (
        "a monotonic ramp has no local structure; anything found here was "
        "measured against the profile's mean instead of against neighbours"
    )


@pytest.mark.trace("REQ-WP-012")
def test_the_thresholds_are_configurable(uniform: list[TradeEvent]) -> None:
    """Principle X. A threshold low enough turns every bin into a node, which
    is the failure the defaults exist to avoid."""
    profile = build(uniform, bin_width=Decimal("1"))

    assert nodes(profile, high_multiple=0.5) != ()


@pytest.mark.trace("REQ-WP-012")
def test_channel_boundaries_are_matched_to_the_nodes_they_fall_inside(
    shelved: list[TradeEvent],
) -> None:
    """FR-011, PRD section 14.1's "node overlap with channel boundaries".

    A boundary resting on a shelf is a different proposition from one hanging
    over a gap, and the difference is the reason the feature exists.
    """
    profile = build(shelved, bin_width=Decimal("1"))

    overlap = nodes_at(profile, [Decimal("100.7"), Decimal("98.7"), Decimal("200")])

    assert overlap[Decimal("100.7")].kind == "HVN"  # type: ignore[union-attr]
    # 98.7 sits in the thin bin beside the shelf, which is itself a low-volume
    # node -- I first expected None here, which was wrong: a boundary hanging
    # over a gap is exactly the case this feature is for.
    assert overlap[Decimal("98.7")].kind == "LVN"  # type: ignore[union-attr]
    assert overlap[Decimal("200")] is None, "outside the profile entirely"


@pytest.mark.trace("REQ-WP-012")
def test_the_volume_package_cannot_consult_a_clock() -> None:
    """FR-014."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "volume"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
