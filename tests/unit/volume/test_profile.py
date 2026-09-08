"""PRD section 14.1's binning and value area (REQ-WP-012)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import TradeEvent
from channelflow.volume import EmptyProfile, build

from .conftest import trade


@pytest.mark.trace("REQ-WP-012")
def test_bins_hold_the_volume_that_traded_in_them(shelved: list[TradeEvent]) -> None:
    """SC-001, FR-001. Hand-summed: 1, 2, 20, 2, 1 with a bin width of one."""
    profile = build(shelved, bin_width=Decimal("1"))

    assert [b.volume for b in profile.bins] == [
        Decimal("1"),
        Decimal("2"),
        Decimal("20"),
        Decimal("2"),
        Decimal("1"),
    ]
    assert profile.total_volume == Decimal("26")


@pytest.mark.trace("REQ-WP-012")
def test_sides_come_from_the_aggressor_never_from_bar_direction() -> None:
    """SC-002, FR-002, PRD section 14.1's prohibition:

        "Do not infer buy/sell direction from candle color if aggressor-side
        trades are available."

    A profile built from bar direction is a different, worse measurement
    wearing the same name -- and it is the easy one to write, because bars are
    already aggregated.
    """
    mixed = [
        trade(0, "100.5", "3", "buy"),
        trade(1, "100.5", "5", "sell"),
        trade(2, "100.5", "7", "unknown"),
    ]

    profile = build(mixed, bin_width=Decimal("1"))
    only = profile.bins[0]

    assert only.buy_volume == Decimal("3")
    assert only.sell_volume == Decimal("5")
    assert only.volume == Decimal("15"), "the unknown trade counts in the total"
    assert only.buy_volume + only.sell_volume < only.volume


@pytest.mark.trace("REQ-WP-012")
def test_a_trade_on_a_boundary_falls_in_the_upper_bin() -> None:
    """FR-003, the spec's third edge case.

    Consistently, so the same trades always give the same profile whatever
    order they arrive in.
    """
    on_edge = [trade(0, "100", "1"), trade(1, "101", "1"), trade(2, "100.999", "1")]

    profile = build(on_edge, bin_width=Decimal("1"), anchor=Decimal("100"))

    assert [b.volume for b in profile.bins] == [Decimal("2"), Decimal("1")]


@pytest.mark.trace("REQ-WP-012")
def test_the_poc_is_the_busiest_bin(shelved: list[TradeEvent]) -> None:
    """SC-003, FR-004."""
    profile = build(shelved, bin_width=Decimal("1"))

    assert profile.poc.volume == Decimal("20")
    assert profile.poc.low == Decimal("100.5")
    assert not profile.poc_tie


@pytest.mark.trace("REQ-WP-012")
def test_a_tie_goes_to_the_lower_price_and_is_recorded() -> None:
    """FR-004, ADR-028.

    The direction is arbitrary; what matters is that it is the same every run,
    and that a reader comparing two profiles can see the tie happened.
    """
    tied = [trade(0, "100.5", "10"), trade(1, "101.5", "10")]

    profile = build(tied, bin_width=Decimal("1"))

    assert profile.poc.low == Decimal("100.5")
    assert profile.poc_tie


@pytest.mark.trace("REQ-WP-012")
def test_the_value_area_is_contiguous_and_contains_the_poc(
    shelved: list[TradeEvent],
) -> None:
    """SC-004, FR-005, ADR-028.

    Both properties are assumed from the name and neither follows from the 70%
    target: taking bins by descending volume reaches it faster and can leave a
    hole, and a narrowest-window search need not contain the POC at all.
    """
    profile = build(shelved, bin_width=Decimal("1"), value_area_share=0.70)

    indices = list(profile.value_area_indices)
    assert profile.poc_index in indices
    assert indices == list(range(min(indices), max(indices) + 1)), "contiguous"


@pytest.mark.trace("REQ-WP-012")
def test_the_value_area_is_contiguous_on_a_bimodal_profile(
    bimodal: list[TradeEvent],
) -> None:
    """SC-004, FR-005, ADR-028 -- and the test that actually discriminates.

    On a single-peaked profile every construction agrees, so the assertion
    above passes whichever rule is implemented. Here they diverge: expanding
    from the POC gives {0, 1, 2}; taking bins by descending volume gives
    {0, 2, 4}, which holds more than 70% and has a hole in it.

    A mutation swapping the rules survived the earlier test and fails this one.
    """
    profile = build(bimodal, bin_width=Decimal("1"), value_area_share=0.70)

    indices = list(profile.value_area_indices)
    assert indices == list(range(min(indices), max(indices) + 1)), (
        f"value area {indices} is not contiguous"
    )
    assert profile.poc_index in indices
    assert 1 in indices, "the gap beside the POC is inside the area, not skipped"


@pytest.mark.trace("REQ-WP-012")
def test_the_value_area_holds_at_least_the_configured_share(
    shelved: list[TradeEvent],
) -> None:
    """SC-004, FR-005."""
    for share in (0.5, 0.7, 0.9):
        profile = build(shelved, bin_width=Decimal("1"), value_area_share=share)
        held = sum((b.volume for b in profile.value_area), Decimal(0))

        assert float(held / profile.total_volume) >= share


@pytest.mark.trace("REQ-WP-012")
def test_vah_and_val_bound_the_value_area(shelved: list[TradeEvent]) -> None:
    """SC-003, FR-006."""
    profile = build(shelved, bin_width=Decimal("1"), value_area_share=0.9)

    assert profile.vah == max(b.high for b in profile.value_area)
    assert profile.val == min(b.low for b in profile.value_area)
    assert profile.val <= profile.poc.low
    assert profile.vah >= profile.poc.high


@pytest.mark.trace("REQ-WP-012")
def test_an_unreachable_target_takes_the_whole_profile_and_says_so(
    shelved: list[TradeEvent],
) -> None:
    """FR-005, the spec's second edge case.

    A value area spanning everything looks like a wide market; it may instead
    mean the target could not be met by a proper subset, and the flag is what
    distinguishes them.
    """
    profile = build(shelved, bin_width=Decimal("1"), value_area_share=1.0)

    assert len(profile.value_area) == len(profile.bins)
    assert profile.value_area_is_whole_profile


@pytest.mark.trace("REQ-WP-012")
def test_a_single_price_profile_is_its_own_value_area() -> None:
    """The spec's first edge case: one bin, which is the POC, and no flag --
    the whole profile *is* a proper answer when there is only one bin."""
    one_price = [trade(i, "100.5", "5") for i in range(4)]

    profile = build(one_price, bin_width=Decimal("1"))

    assert len(profile.bins) == 1
    assert profile.value_area_indices == (0,)


@pytest.mark.trace("REQ-WP-012")
def test_an_empty_window_refuses() -> None:
    """SC-007, FR-007.

    A profile with no bins has no point of control, and every consumer would
    then need its own answer to what that means.
    """
    with pytest.raises(EmptyProfile):
        build([], bin_width=Decimal("1"))


@pytest.mark.trace("REQ-WP-012")
def test_building_is_deterministic(shelved: list[TradeEvent]) -> None:
    """Principle XI, and what the fixed tie-breaks are for."""
    first = build(shelved, bin_width=Decimal("1"))
    shuffled = build(list(reversed(shelved)), bin_width=Decimal("1"))

    assert [b.volume for b in first.bins] == [b.volume for b in shuffled.bins]
    assert first.poc_index == shuffled.poc_index
    assert first.value_area_indices == shuffled.value_area_indices
