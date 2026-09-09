"""EXP-006's conditional outcomes by derivatives state (REQ-EXP-006)."""

from __future__ import annotations

import pytest

from channelflow.backtest import CostModel, CostsRequired
from channelflow.backtest.outcomes import Outcome, SignalOutcome
from channelflow.research.derivatives_context import (
    DEFAULT_EDGES,
    VARIABLES,
    Observation,
    conditional_study,
)

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def outcome(kind: Outcome, ret: float) -> SignalOutcome:
    return SignalOutcome(
        horizon_end_ns=0,
        first_target_time_ns=1 if kind is Outcome.TARGET else None,
        first_invalidation_time_ns=1 if kind is Outcome.STOP else None,
        mfe_pct=abs(ret),
        mae_pct=-abs(ret) / 2,
        return_h=ret,
        outcome=kind,
    )


def observations(*, funding: float, count: int, ret: float) -> list[Observation]:
    """`count` setups all seen at the same funding reading."""
    return [
        Observation(
            values={
                "funding_z": funding,
                "oi_change_5m": 0.01,
                "liquidation_imbalance_5m": 0.1,
                "basis_bps": 1.0,
            },
            outcome=outcome(Outcome.TARGET if ret > 0 else Outcome.STOP, ret),
        )
        for _ in range(count)
    ]


SAMPLE = (
    observations(funding=-3.0, count=20, ret=0.04)
    + observations(funding=0.5, count=20, ret=0.01)
    + observations(funding=3.0, count=20, ret=-0.03)
)


@pytest.mark.trace("REQ-EXP-006")
def test_all_four_variables_are_reported() -> None:
    """EXP-006 names four. A variable missing from the report is one nobody
    conditioned on, and the reader cannot tell that from one with no effect."""
    report = conditional_study(SAMPLE, costs=COSTS, point_in_time=True)

    assert set(report.conditionals) == set(VARIABLES)
    assert len(VARIABLES) == 4


@pytest.mark.trace("REQ-EXP-006")
def test_a_variable_with_no_data_is_unavailable_not_a_flat_conditional() -> None:
    """The shared criterion. Rendered as one bucket holding everything, "no
    data" and "no relationship" look identical -- and only one of them is a
    finding about the market."""
    without_basis = [
        Observation(
            values={k: v for k, v in o.values.items() if k != "basis_bps"},
            outcome=o.outcome,
        )
        for o in SAMPLE
    ]

    report = conditional_study(without_basis, costs=COSTS, point_in_time=True)

    basis = report.conditionals["basis_bps"]
    assert basis.buckets == ()
    assert "no data" in basis.reason
    assert report.conditionals["funding_z"].buckets


@pytest.mark.trace("REQ-EXP-006")
def test_the_buckets_are_the_declared_edges_and_carry_their_counts() -> None:
    """Edges declared, not quantiles of the sample: quantiles move with the
    window, so two runs would bucket the same funding reading differently and
    their conditionals could not be compared."""
    report = conditional_study(SAMPLE, costs=COSTS, point_in_time=True)

    funding = report.conditionals["funding_z"]
    assert funding.edges == DEFAULT_EDGES["funding_z"]
    # Three edges make four buckets.
    assert len(funding.buckets) == 4
    assert sum(b.setups for b in funding.buckets) == len(SAMPLE)


@pytest.mark.trace("REQ-EXP-006")
def test_the_conditional_separates_the_buckets_it_should() -> None:
    """The control for the whole study: setups at deeply negative funding won
    here and setups at deeply positive funding lost, so the conditional must
    show it. If it did not, the bucketing would not be reaching the outcomes."""
    report = conditional_study(SAMPLE, costs=COSTS, point_in_time=True)

    buckets = {b.label: b for b in report.conditionals["funding_z"].buckets}
    negative = next(b for b in buckets.values() if b.low is None)
    positive = next(b for b in buckets.values() if b.high is None)

    assert negative.report is not None and positive.report is not None
    assert negative.report.expectancy_r > positive.report.expectancy_r


@pytest.mark.trace("REQ-EXP-006")
def test_a_bucket_too_small_is_reported_and_not_scored() -> None:
    """A conditional over three setups is noise with a label on it."""
    thin = SAMPLE + observations(funding=1.5, count=3, ret=0.02)

    # An edge at 1.0 so the three setups get a bucket of their own; without it
    # they join the twenty at 0.5 and the bucket is not thin at all.
    report = conditional_study(
        thin,
        costs=COSTS,
        point_in_time=True,
        min_bucket=10,
        edges={"funding_z": (-2.0, 0.0, 1.0, 2.0)},
    )

    lonely = next(
        b for b in report.conditionals["funding_z"].buckets if b.low == 1.0 and b.high == 2.0
    )
    assert lonely.setups == 3
    assert lonely.report is None
    assert "below the minimum" in lonely.reason


@pytest.mark.trace("REQ-EXP-006")
def test_a_contemporaneous_study_says_so() -> None:
    """EXP-014's warning, carried into every conditional: a state read around
    the outcome explains it, and a state read at signal time forecasts it. Only
    one of those is tradeable."""
    forecast = conditional_study(SAMPLE, costs=COSTS, point_in_time=True)
    explanation = conditional_study(SAMPLE, costs=COSTS, point_in_time=False)

    assert "predictive" in forecast.note
    assert "explain rather than forecast" in explanation.note
    assert forecast.point_in_time and not explanation.point_in_time


@pytest.mark.trace("REQ-EXP-006")
def test_the_point_in_time_flag_has_no_default() -> None:
    """It decides whether the answer is a forecast or an explanation, and a
    module that guessed would label somebody else's study."""
    import inspect

    parameter = inspect.signature(conditional_study).parameters["point_in_time"]

    assert parameter.default is inspect.Parameter.empty


@pytest.mark.trace("REQ-EXP-006")
def test_ambiguous_outcomes_are_excluded_and_counted() -> None:
    """PRD §40's rule, carried into the conditionals."""
    with_ambiguous = (
        SAMPLE
        + [
            Observation(
                values={
                    "funding_z": 0.5,
                    "oi_change_5m": 0.0,
                    "liquidation_imbalance_5m": 0.0,
                    "basis_bps": 0.0,
                },
                outcome=outcome(Outcome.AMBIGUOUS, 0.05),
            )
        ]
        * 4
    )

    report = conditional_study(with_ambiguous, costs=COSTS, point_in_time=True)

    assert report.excluded_ambiguous == 4
    assert sum(b.setups for b in report.conditionals["funding_z"].buckets) == len(SAMPLE)


@pytest.mark.trace("REQ-EXP-006")
def test_every_conditional_uses_the_same_costs() -> None:
    """A conditional scored under different costs than its neighbour is a
    comparison of cost models."""
    report = conditional_study(SAMPLE, costs=COSTS, point_in_time=True)

    scored = [
        b.report
        for conditional in report.conditionals.values()
        for b in conditional.buckets
        if b.report is not None
    ]
    assert scored
    assert all(r.costs == COSTS for r in scored)


@pytest.mark.trace("REQ-EXP-006")
def test_raising_the_costs_lowers_every_bucket() -> None:
    """The control for the costs actually reaching the arithmetic."""
    cheap = conditional_study(SAMPLE, costs=COSTS, point_in_time=True)
    dear = conditional_study(
        SAMPLE, costs=CostModel(fee_bps=100.0, slippage_bps=100.0), point_in_time=True
    )

    def expectancies(report):
        return [
            b.report.expectancy_r
            for b in report.conditionals["funding_z"].buckets
            if b.report is not None
        ]

    assert expectancies(cheap)
    assert all(d < c for c, d in zip(expectancies(cheap), expectancies(dear), strict=True))


@pytest.mark.trace("REQ-EXP-006")
def test_the_study_without_costs_is_refused() -> None:
    """PRD §41 rule 9, tested with no variable at all so only this refusal can fire."""
    with pytest.raises(CostsRequired):
        conditional_study(SAMPLE, costs=None, point_in_time=True, variables=())


@pytest.mark.trace("REQ-EXP-006")
def test_two_studies_produce_equal_reports() -> None:
    assert conditional_study(SAMPLE, costs=COSTS, point_in_time=True) == conditional_study(
        SAMPLE, costs=COSTS, point_in_time=True
    )
