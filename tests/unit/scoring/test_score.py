"""PRD section 22.1's deterministic score (REQ-SCORE-001)."""

from __future__ import annotations

import pytest

from channelflow.scoring import (
    GROUP_CAPS,
    ContributionOutOfRange,
    Group,
    GroupContribution,
    NothingToScore,
    score_signal,
)

#: PRD section 22.2's worked example, group for group.
WORKED_EXAMPLE = (
    GroupContribution(group=Group.CHANNEL_STRUCTURE, value=26.0, factors=("slope_stability",)),
    GroupContribution(group=Group.REJECTION_QUALITY, value=17.0, factors=("wick_rejection",)),
    GroupContribution(group=Group.ORDER_FLOW, value=16.0, factors=("ofi_agrees",)),
    GroupContribution(group=Group.VOLUME, value=7.0, factors=("poc_confluence",)),
    GroupContribution(group=Group.DERIVATIVES, value=8.0, factors=("funding_z",)),
    GroupContribution(group=Group.DEFI_CROSSVENUE, value=7.0, factors=("basis_bps",)),
)


@pytest.mark.trace("REQ-SCORE-001")
def test_the_prds_own_worked_example_reproduces_exactly() -> None:
    """SC-001, FR-003, FR-004, FR-005.

    Section 22.2 prints every intermediate number: 81 raw, a 0.96 multiplier and
    77.8 final. An engine that cannot reproduce them is not the one the PRD
    describes, whatever else it does.
    """
    score = score_signal(WORKED_EXAMPLE, data_quality=0.96)

    assert score.raw == pytest.approx(81.0)
    assert score.data_quality == pytest.approx(0.96)
    assert score.final == pytest.approx(77.8, abs=0.05)


@pytest.mark.trace("REQ-SCORE-001")
def test_the_six_groups_and_their_caps_are_the_prds() -> None:
    """FR-001.

    Section 22.1 writes the caps out. They sum to 100, which is what makes the
    raw score a score out of 100 rather than a total that happens to look like
    a percentage.
    """
    assert GROUP_CAPS == {
        Group.CHANNEL_STRUCTURE: 30.0,
        Group.REJECTION_QUALITY: 20.0,
        Group.ORDER_FLOW: 20.0,
        Group.VOLUME: 10.0,
        Group.DERIVATIVES: 10.0,
        Group.DEFI_CROSSVENUE: 10.0,
    }
    assert sum(GROUP_CAPS.values()) == 100.0


@pytest.mark.trace("REQ-SCORE-001")
def test_a_contribution_above_its_cap_is_refused_not_clipped() -> None:
    """SC-002, FR-002.

    Clipping turns a caller's mistake into a maximum score. The group would read
    as a perfect one, and nothing downstream would ever say the value had been
    altered on the way in.
    """
    with pytest.raises(ContributionOutOfRange, match="volume"):
        GroupContribution(group=Group.VOLUME, value=11.0, factors=("poc",))


@pytest.mark.trace("REQ-SCORE-001")
def test_a_negative_contribution_is_refused() -> None:
    """SC-002, FR-002.

    Section 22.1's groups are `0..cap`. A negative contribution is a different
    scoring scheme -- one where a family can subtract from the others -- and
    accepting it here would mean the caps no longer bound anything.
    """
    with pytest.raises(ContributionOutOfRange):
        GroupContribution(group=Group.DERIVATIVES, value=-1.0, factors=("oi_z",))


@pytest.mark.trace("REQ-SCORE-001")
def test_a_data_quality_multiplier_outside_its_range_is_refused() -> None:
    """FR-004.

    Above 1 it is not a penalty but a bonus, and section 43 says data quality
    "penalizes stale/missing sources". A multiplier that can raise a score would
    let a stale source improve one.
    """
    with pytest.raises(ValueError, match="data quality"):
        score_signal(WORKED_EXAMPLE, data_quality=1.2)


@pytest.mark.trace("REQ-SCORE-001")
def test_the_same_input_scores_identically_twice() -> None:
    """SC-005, FR-008."""
    first = score_signal(WORKED_EXAMPLE, data_quality=0.96)
    second = score_signal(WORKED_EXAMPLE, data_quality=0.96)

    assert first == second


@pytest.mark.trace("REQ-SCORE-001")
def test_a_missing_family_is_not_scored_as_zero() -> None:
    """SC-003, FR-003, FR-006, ADR-044.

    Section 22.1: "Missing family must not automatically equal zero." A DeFi
    outage would otherwise cost ten points, and the resulting score would be
    indistinguishable from one where the DeFi evidence was genuinely against
    the setup.
    """
    without_defi = tuple(c for c in WORKED_EXAMPLE if c.group is not Group.DEFI_CROSSVENUE)

    missing = score_signal(without_defi, data_quality=1.0)
    scored_zero = score_signal(
        (*without_defi, GroupContribution(group=Group.DEFI_CROSSVENUE, value=0.0, factors=())),
        data_quality=1.0,
    )

    assert missing.raw > scored_zero.raw
    assert Group.DEFI_CROSSVENUE in missing.missing
    assert Group.DEFI_CROSSVENUE not in scored_zero.missing


@pytest.mark.trace("REQ-SCORE-001")
def test_a_missing_family_lowers_the_confidence_by_its_own_cap() -> None:
    """SC-003, FR-006.

    The "explicit confidence downgrade" section 22.1 asks for. Excluding a
    family from the denominator keeps the score honest about the evidence it
    has; the confidence is what says how much evidence that was.
    """
    complete = score_signal(WORKED_EXAMPLE, data_quality=1.0)
    without_defi = score_signal(
        tuple(c for c in WORKED_EXAMPLE if c.group is not Group.DEFI_CROSSVENUE),
        data_quality=1.0,
    )

    assert complete.confidence == pytest.approx(1.0)
    # The DeFi group is 10 of the 100 available points.
    assert without_defi.confidence == pytest.approx(0.9)


@pytest.mark.trace("REQ-SCORE-001")
def test_a_score_with_nothing_present_is_refused() -> None:
    """SC-004, FR-007.

    A score computed from nothing is not a low score. Reporting one would put an
    empty setup on the same axis as a weak one, and the ranker would then sort
    them against each other.
    """
    with pytest.raises(NothingToScore):
        score_signal((), data_quality=1.0)


@pytest.mark.trace("REQ-SCORE-001")
def test_the_same_group_cannot_be_supplied_twice() -> None:
    """FR-001.

    Two contributions for one group means a score that depends on which one the
    summation happened to see -- or on both, silently doubling a family's weight
    past its cap.
    """
    with pytest.raises(ValueError, match="twice"):
        score_signal(
            (*WORKED_EXAMPLE, GroupContribution(group=Group.VOLUME, value=3.0, factors=())),
            data_quality=1.0,
        )


@pytest.mark.trace("REQ-SCORE-001")
def test_a_partial_score_is_normalized_over_what_was_observable() -> None:
    """FR-003, ADR-044.

    Channel structure alone, at 24 of its 30 points, is a score of 80 out of the
    30 points that existed -- not 24 out of 100. The alternative reads a
    complete-data score of 24, which no downstream threshold can interpret.
    """
    only_channel = (
        GroupContribution(group=Group.CHANNEL_STRUCTURE, value=24.0, factors=("slope",)),
    )

    score = score_signal(only_channel, data_quality=1.0)

    assert score.raw == pytest.approx(80.0)
    assert score.confidence == pytest.approx(0.3)
