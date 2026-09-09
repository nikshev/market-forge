"""PRD section 22.4's explainability (REQ-SCORE-001)."""

from __future__ import annotations

import pytest

from channelflow.scoring import (
    Group,
    GroupContribution,
    SignalScore,
    explain,
    score_signal,
)
from channelflow.scoring.explain import ScoreRequired

SNAPSHOT = {"ofi_1m": 0.62, "funding_z": 1.8, "poc_distance_bps": 12.0}

CONTRIBUTIONS = (
    GroupContribution(group=Group.CHANNEL_STRUCTURE, value=26.0, factors=("slope_stability",)),
    GroupContribution(group=Group.REJECTION_QUALITY, value=4.0, factors=("weak_wick",)),
    GroupContribution(group=Group.ORDER_FLOW, value=16.0, factors=("ofi_agrees",)),
    GroupContribution(group=Group.VOLUME, value=1.0, factors=("poc_far",)),
    GroupContribution(group=Group.DERIVATIVES, value=8.0, factors=("funding_z",)),
)


@pytest.mark.trace("REQ-SCORE-001")
def test_an_explanation_carries_all_five_of_section_22_4s_items() -> None:
    """SC-006, FR-009.

    Section 22.4 lists exactly five things every signal stores. Four of them
    without the fifth is a panel that cannot answer "why this score".
    """
    score = score_signal(CONTRIBUTIONS, data_quality=0.9)

    explanation = explain(score, feature_snapshot=SNAPSHOT, model_version="deterministic-v1")

    assert explanation.top_positive
    assert explanation.top_negative
    assert explanation.missing == (Group.DEFI_CROSSVENUE,)
    assert explanation.feature_snapshot == SNAPSHOT
    assert explanation.model_version == "deterministic-v1"


@pytest.mark.trace("REQ-SCORE-001")
def test_every_group_appears_as_a_contribution_or_as_an_absence() -> None:
    """SC-006, FR-010.

    REQ-US-004 asks to see channel, OFI, volume profile, derivatives and DeFi.
    A group that is simply absent from the panel reads as "not relevant", when
    what happened was "no data" -- the same conflation section 22.1's
    missing-family rule exists to prevent.
    """
    score = score_signal(CONTRIBUTIONS, data_quality=0.9)

    explanation = explain(score, feature_snapshot=SNAPSHOT, model_version="deterministic-v1")

    accounted = {f.group for f in explanation.factors} | set(explanation.missing)
    assert accounted == set(Group)


@pytest.mark.trace("REQ-SCORE-001")
def test_positive_and_negative_are_measured_against_each_groups_own_cap() -> None:
    """FR-009.

    26 of 30 and 8 of 10 are both strong; 4 of 20 is weak while being a larger
    number than 1 of 10, which is weaker still. Ranking by raw contribution
    would call the weakest group the second-best one.
    """
    score = score_signal(CONTRIBUTIONS, data_quality=1.0)

    explanation = explain(score, feature_snapshot=SNAPSHOT, model_version="deterministic-v1")

    assert explanation.top_positive[0].group is Group.CHANNEL_STRUCTURE
    assert explanation.top_negative[0].group is Group.VOLUME
    assert explanation.top_negative[1].group is Group.REJECTION_QUALITY


@pytest.mark.trace("REQ-SCORE-001")
def test_a_tie_is_broken_by_a_declared_key_not_by_input_order() -> None:
    """SC-006, FR-009.

    Two groups filling the same share of their caps must order the same way
    whichever order they arrived in, or the panel changes between two runs over
    one signal.
    """
    tied = (
        GroupContribution(group=Group.DERIVATIVES, value=5.0, factors=()),
        GroupContribution(group=Group.VOLUME, value=5.0, factors=()),
    )
    forward = explain(score_signal(tied, data_quality=1.0), feature_snapshot={}, model_version="v1")
    backward = explain(
        score_signal(tuple(reversed(tied)), data_quality=1.0),
        feature_snapshot={},
        model_version="v1",
    )

    assert [f.group for f in forward.top_positive] == [f.group for f in backward.top_positive]


@pytest.mark.trace("REQ-SCORE-001")
def test_an_explanation_needs_a_score() -> None:
    """SC-007, FR-011.

    An explanation built without one would be a list of factors nobody scored:
    it would read exactly like a real explanation and account for a number that
    was never computed.
    """
    with pytest.raises(ScoreRequired):
        explain(None, feature_snapshot=SNAPSHOT, model_version="deterministic-v1")


@pytest.mark.trace("REQ-SCORE-001")
def test_a_missing_family_is_never_listed_among_the_negative_factors() -> None:
    """FR-010.

    "We have no DeFi data" and "the DeFi evidence is against this setup" are
    different statements. Section 22.4 gives them separate lists for that
    reason, and merging them would make an outage read as evidence.
    """
    score = score_signal(CONTRIBUTIONS, data_quality=1.0)

    explanation = explain(score, feature_snapshot=SNAPSHOT, model_version="deterministic-v1")

    assert Group.DEFI_CROSSVENUE not in {f.group for f in explanation.top_negative}
    assert Group.DEFI_CROSSVENUE in explanation.missing


@pytest.mark.trace("REQ-SCORE-001")
def test_the_model_version_is_required() -> None:
    """FR-009.

    Section 22.4 stores the "model/version used". An explanation whose version
    is unknown cannot be compared against one produced by a later model, which
    is the comparison the field exists for.
    """
    score = score_signal(CONTRIBUTIONS, data_quality=1.0)

    with pytest.raises(ValueError, match="model version"):
        explain(score, feature_snapshot=SNAPSHOT, model_version="")


@pytest.mark.trace("REQ-SCORE-001")
def test_a_smaller_number_filling_more_of_its_cap_outranks_a_larger_one() -> None:
    """FR-009.

    The case the share exists for. Channel structure at 20 of 30 is the larger
    number; derivatives at 9 of 10 is the stronger signal. Ranked by raw
    contribution the panel leads with the weaker of the two, and does so on
    every setup, because the channel group's cap is the largest.
    """
    score = score_signal(
        (
            GroupContribution(group=Group.CHANNEL_STRUCTURE, value=20.0, factors=("slope",)),
            GroupContribution(group=Group.DERIVATIVES, value=9.0, factors=("funding_z",)),
        ),
        data_quality=1.0,
    )

    explanation = explain(score, feature_snapshot={}, model_version="v1")

    assert [f.group for f in explanation.top_positive] == [
        Group.DERIVATIVES,
        Group.CHANNEL_STRUCTURE,
    ]


@pytest.mark.trace("REQ-SCORE-001")
def test_the_tie_break_holds_for_a_score_built_by_hand() -> None:
    """SC-006, FR-009.

    `score_signal` already sorts its contributions, which hides whether the
    explanation has a tie-break of its own -- two guards over one property, and
    the panel is reachable from any stored `SignalScore`, not only from a fresh
    computation. Built here in reverse, so only the explanation's own ordering
    can produce the answer.
    """
    tied = (
        GroupContribution(group=Group.VOLUME, value=5.0, factors=()),
        GroupContribution(group=Group.DERIVATIVES, value=5.0, factors=()),
    )
    by_hand = SignalScore(
        raw=50.0,
        final=50.0,
        data_quality=1.0,
        confidence=0.2,
        contributions=tied,
        missing=(),
    )

    explanation = explain(by_hand, feature_snapshot={}, model_version="v1")

    assert [f.group for f in explanation.top_positive] == [
        Group.DERIVATIVES,
        Group.VOLUME,
    ]
