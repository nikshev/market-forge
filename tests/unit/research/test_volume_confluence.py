"""EXP-005's volume confluence study (REQ-EXP-005)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.backtest.outcomes import Outcome, SignalOutcome
from channelflow.research.volume_confluence import (
    Observation,
    PopulationTooSmall,
    Verdict,
    classify,
    confluence_study,
)
from channelflow.volume import build
from tests.unit.volume.conftest import trade


def outcome(kind: Outcome) -> SignalOutcome:
    return SignalOutcome(
        horizon_end_ns=0,
        first_target_time_ns=1 if kind is Outcome.TARGET else None,
        first_invalidation_time_ns=1 if kind is Outcome.STOP else None,
        mfe_pct=0.0,
        mae_pct=0.0,
        return_h=0.0,
        outcome=kind,
    )


def population(
    *, confluent: bool, targets: int, stops: int, timeouts: int = 0
) -> list[Observation]:
    return (
        [Observation(confluent=confluent, outcome=outcome(Outcome.TARGET))] * targets
        + [Observation(confluent=confluent, outcome=outcome(Outcome.STOP))] * stops
        + [Observation(confluent=confluent, outcome=outcome(Outcome.TIMEOUT))] * timeouts
    )


def profile_with_a_shelf():
    """A profile whose volume piles up at 105 -- a high-volume node."""
    trades = []
    index = 0
    for price, count in (("100", 2), ("101", 2), ("102", 2), ("105", 30), ("108", 2)):
        for _ in range(count):
            trades.append(trade(index, price, "1"))
            index += 1
    return build(trades, bin_width=Decimal("1"))


@pytest.mark.trace("REQ-EXP-005")
def test_a_boundary_on_a_high_volume_node_is_confluent() -> None:
    """PRD §14.1's "node overlap with channel boundaries", which is the question.

    A boundary resting on a shelf is a different proposition from one hanging
    over a gap.
    """
    result = classify(Decimal("105.5"), profile_with_a_shelf())

    assert result.node_kind == "HVN"
    assert result.present


@pytest.mark.trace("REQ-EXP-005")
def test_a_boundary_away_from_every_level_is_not_confluent() -> None:
    """The control: without it, "confluent" could be a constant.

    103.5 is in no bin at all -- nothing traded there -- so it is neither a node
    nor a value-area edge. A price inside a thin bin would be an LVN, which
    EXP-005 counts as a level: a boundary hanging over a gap is exactly the
    proposition the question is about.
    """
    result = classify(Decimal("103.5"), profile_with_a_shelf(), band_bps=1.0)

    assert result.node_kind is None
    assert not result.on_value_area_edge
    assert not result.present


@pytest.mark.trace("REQ-EXP-005")
def test_a_boundary_at_the_value_area_edge_is_confluent() -> None:
    """EXP-005 names VAH and VAL beside the nodes, and they are a different test
    from the node one: an edge is a boundary of a region, not a bin."""
    profile = profile_with_a_shelf()

    result = classify(profile.vah, profile, band_bps=1.0)

    assert result.on_value_area_edge
    assert result.present


@pytest.mark.trace("REQ-EXP-005")
def test_the_band_decides_how_close_counts() -> None:
    """A wider band admits a boundary a narrow one refuses -- and which
    population a setup joins is the whole comparison."""
    profile = profile_with_a_shelf()
    just_off = profile.vah + Decimal("0.05")

    assert not classify(just_off, profile, band_bps=1.0).on_value_area_edge
    assert classify(just_off, profile, band_bps=100.0).on_value_area_edge


@pytest.mark.trace("REQ-EXP-005")
def test_a_higher_probability_with_confluence_is_reported_as_higher() -> None:
    """The first of the three answers.

    70% against 40%, and the caller declared 10 points as material.
    """
    observations = population(confluent=True, targets=70, stops=30) + population(
        confluent=False, targets=40, stops=60
    )

    result = confluence_study(observations, effect_size=0.10)

    assert result.verdict is Verdict.HIGHER
    assert result.with_confluence.target_before_stop == pytest.approx(0.70)
    assert result.without_confluence.target_before_stop == pytest.approx(0.40)
    assert result.difference == pytest.approx(0.30)


@pytest.mark.trace("REQ-EXP-005")
def test_a_lower_probability_with_confluence_is_reported_as_lower() -> None:
    """The second. A study that could only find a positive effect would find one."""
    observations = population(confluent=True, targets=30, stops=70) + population(
        confluent=False, targets=60, stops=40
    )

    result = confluence_study(observations, effect_size=0.10)

    assert result.verdict is Verdict.LOWER
    assert result.difference < 0


@pytest.mark.trace("REQ-EXP-005")
def test_a_small_difference_is_not_materially_different() -> None:
    """The third answer, and the one most confluence claims deserve.

    52% against 50% is a difference. It is not the difference the caller said
    would matter.
    """
    observations = population(confluent=True, targets=52, stops=48) + population(
        confluent=False, targets=50, stops=50
    )

    result = confluence_study(observations, effect_size=0.10)

    assert result.verdict is Verdict.NOT_MATERIAL
    assert result.difference == pytest.approx(0.02)


@pytest.mark.trace("REQ-EXP-005")
def test_the_effect_size_is_the_callers_and_has_no_default() -> None:
    """ "Materially" is the whole question. A threshold chosen after seeing the
    difference is not a finding about the market, and a default is that choice
    made by whoever wrote this module."""
    import inspect

    parameter = inspect.signature(confluence_study).parameters["effect_size"]

    assert parameter.default is inspect.Parameter.empty


@pytest.mark.trace("REQ-EXP-005")
def test_the_same_difference_flips_the_verdict_when_the_effect_size_changes() -> None:
    """The threshold is what makes a difference material, so it has to be able
    to change the answer -- otherwise it is decoration."""
    observations = population(confluent=True, targets=60, stops=40) + population(
        confluent=False, targets=50, stops=50
    )

    assert confluence_study(observations, effect_size=0.05).verdict is Verdict.HIGHER
    assert confluence_study(observations, effect_size=0.20).verdict is Verdict.NOT_MATERIAL


@pytest.mark.trace("REQ-EXP-005")
def test_a_population_too_small_refuses() -> None:
    """Two setups agreeing is not evidence, and a difference over them is noise
    with a decimal point."""
    observations = population(confluent=True, targets=2, stops=1) + population(
        confluent=False, targets=40, stops=40
    )

    with pytest.raises(PopulationTooSmall, match="with-confluence"):
        confluence_study(observations, effect_size=0.10, min_population=20)


@pytest.mark.trace("REQ-EXP-005")
def test_ambiguous_outcomes_are_excluded_and_counted() -> None:
    """PRD §40's rule carried into the study: an ambiguous setup has no known
    result, and counting it either way moves the answer."""
    observations = (
        population(confluent=True, targets=30, stops=20)
        + population(confluent=False, targets=30, stops=20)
        + [Observation(confluent=True, outcome=outcome(Outcome.AMBIGUOUS))] * 5
    )

    result = confluence_study(observations, effect_size=0.10)

    assert result.excluded_ambiguous == 5
    assert result.with_confluence.setups == 50


@pytest.mark.trace("REQ-EXP-005")
def test_timeouts_are_counted_but_are_not_decisions() -> None:
    """ "Target before stop" is a probability over setups that reached one or the
    other. A timeout is neither, and folding it into the denominator would make
    a quiet market look like a losing one."""
    observations = population(confluent=True, targets=30, stops=20, timeouts=25) + population(
        confluent=False, targets=30, stops=20
    )

    result = confluence_study(observations, effect_size=0.10)

    assert result.with_confluence.timeouts == 25
    assert result.with_confluence.decided == 50
    assert result.with_confluence.target_before_stop == pytest.approx(0.60)


@pytest.mark.trace("REQ-EXP-005")
def test_a_population_that_decided_nothing_refuses() -> None:
    """Every setup timed out. There is no target-before-stop probability, which
    is different from one of zero."""
    observations = population(confluent=True, targets=0, stops=0, timeouts=30) + population(
        confluent=False, targets=30, stops=20
    )

    with pytest.raises(PopulationTooSmall, match="decided nothing"):
        confluence_study(observations, effect_size=0.10)


@pytest.mark.trace("REQ-EXP-005")
def test_a_negative_effect_size_is_refused() -> None:
    """It would admit every difference, including none."""
    observations = population(confluent=True, targets=30, stops=20) + population(
        confluent=False, targets=30, stops=20
    )

    with pytest.raises(ValueError, match="magnitude"):
        confluence_study(observations, effect_size=-0.1)
