"""PRD section 25.5's metrics, after costs (REQ-BT-001, section 41 rule 9)."""

from __future__ import annotations

import pytest

from channelflow.backtest.economics import (
    CostModel,
    CostsRequired,
    NothingResolved,
    economic_report,
)
from channelflow.backtest.outcomes import Outcome, SignalOutcome

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def outcome(*, kind: Outcome, ret: float, mfe: float = 0.0, mae: float = 0.0) -> SignalOutcome:
    return SignalOutcome(
        horizon_end_ns=0,
        first_target_time_ns=1 if kind is Outcome.TARGET else None,
        first_invalidation_time_ns=1 if kind is Outcome.STOP else None,
        mfe_pct=mfe,
        mae_pct=mae,
        return_h=ret,
        outcome=kind,
    )


WINNERS_AND_LOSERS = [
    outcome(kind=Outcome.TARGET, ret=0.04, mfe=0.05, mae=-0.01),
    outcome(kind=Outcome.TARGET, ret=0.04, mfe=0.06, mae=-0.02),
    outcome(kind=Outcome.STOP, ret=-0.02, mfe=0.01, mae=-0.02),
    outcome(kind=Outcome.TIMEOUT, ret=0.00, mfe=0.02, mae=-0.01),
]


@pytest.mark.trace("REQ-BT-001")
def test_every_section_25_5_metric_is_reported() -> None:
    """SC-001, FR-011.

    Section 25.5 lists them by name. A report missing one is a report a reader
    has to compute the rest of themselves, from numbers it did not give them.
    """
    report = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)

    for field in (
        "win_rate",
        "average_return",
        "median_return",
        "expectancy_r",
        "profit_factor",
        "sharpe",
        "sortino",
        "max_drawdown",
        "average_mfe",
        "average_mae",
        "target_hit_probability",
    ):
        assert getattr(report, field) is not None, field


@pytest.mark.trace("REQ-BT-001")
def test_metrics_without_a_cost_model_are_refused() -> None:
    """SC-007, FR-012.

    PRD §41 rule 9: "Fees/slippage must be included in economic evaluation."
    [[ADR-009]] says why a caveat is not enough -- a 62% gross win rate is
    quoted as 62%, because the caveat does not travel with the number.
    """
    with pytest.raises(CostsRequired):
        economic_report(WINNERS_AND_LOSERS, costs=None, risk_per_trade=0.02)


@pytest.mark.trace("REQ-BT-001")
def test_the_metrics_are_computed_after_costs() -> None:
    """SC-008, SC-009, FR-011, FR-013.

    Two trades at +4% and one at -2%, with 10bp round trip: each return loses
    0.002. Gross average is 1.5%; net is 1.3%.
    """
    report = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)

    assert report.average_return == pytest.approx((0.038 + 0.038 - 0.022 - 0.002) / 4)
    assert report.costs.round_trip_pct == pytest.approx(0.002)


@pytest.mark.trace("REQ-BT-001")
def test_raising_the_costs_lowers_the_expectancy() -> None:
    """SC-009, FR-011.

    The control for the whole rule. If the costs did not reach the arithmetic,
    every metric here would be a gross figure with a cost model attached to it
    for decoration.
    """
    cheap = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)
    dear = economic_report(
        WINNERS_AND_LOSERS,
        costs=CostModel(fee_bps=50.0, slippage_bps=50.0),
        risk_per_trade=0.02,
    )

    assert dear.expectancy_r < cheap.expectancy_r
    assert dear.average_return < cheap.average_return


@pytest.mark.trace("REQ-BT-001")
def test_the_costs_are_reported_with_the_metrics() -> None:
    """FR-013.

    A net figure whose costs are not beside it cannot be checked, and cannot be
    compared against another run's.
    """
    report = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)

    assert report.costs.fee_bps == pytest.approx(5.0)
    assert report.costs.slippage_bps == pytest.approx(5.0)


@pytest.mark.trace("REQ-BT-001")
def test_ambiguous_outcomes_are_excluded_and_counted() -> None:
    """SC-010, FR-014.

    An ambiguous trade has no known result. Counted as a win it flatters the
    run; as a loss it flatters the next configuration that avoids them. Excluded
    and reported, it is what it is.
    """
    with_ambiguous = [*WINNERS_AND_LOSERS, outcome(kind=Outcome.AMBIGUOUS, ret=0.04)]

    report = economic_report(with_ambiguous, costs=COSTS, risk_per_trade=0.02)

    assert report.excluded_ambiguous == 1
    assert report.trades == 4
    assert report.win_rate == pytest.approx(0.5)


@pytest.mark.trace("REQ-BT-001")
def test_no_resolved_outcome_is_refused() -> None:
    """SC-011, FR-015.

    A profit factor over nothing is not zero, and a win rate over nothing is not
    0%.
    """
    with pytest.raises(NothingResolved):
        economic_report(
            [outcome(kind=Outcome.AMBIGUOUS, ret=0.04)], costs=COSTS, risk_per_trade=0.02
        )


@pytest.mark.trace("REQ-BT-001")
def test_expectancy_is_measured_in_units_of_risk() -> None:
    """SC-008, FR-011.

    "Expectancy in R" is what makes two setups comparable when one risks 2% and
    the other 0.5%. Net average is 1.3%, risk is 2%, so expectancy is 0.65R.
    """
    report = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)

    assert report.expectancy_r == pytest.approx(report.average_return / 0.02)


@pytest.mark.trace("REQ-BT-001")
def test_the_profit_factor_is_gross_gains_over_gross_losses() -> None:
    """SC-008.

    Net of costs, the winners give 0.076 and the losers 0.024.
    """
    report = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)

    assert report.profit_factor == pytest.approx(0.076 / 0.024, rel=1e-6)


@pytest.mark.trace("REQ-BT-001")
def test_a_run_with_no_losses_reports_no_profit_factor() -> None:
    """SC-008.

    Dividing by zero losses gives infinity, which reads as a spectacular result
    rather than as a sample with nothing to divide by.
    """
    winners = [outcome(kind=Outcome.TARGET, ret=0.04) for _ in range(3)]

    report = economic_report(winners, costs=COSTS, risk_per_trade=0.02)

    assert report.profit_factor is None


@pytest.mark.trace("REQ-BT-001")
def test_the_same_outcomes_report_identically_twice() -> None:
    """SC-008, FR-016."""
    first = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)
    second = economic_report(WINNERS_AND_LOSERS, costs=COSTS, risk_per_trade=0.02)

    assert first == second


@pytest.mark.trace("REQ-BT-001")
def test_the_drawdown_is_of_the_equity_path_not_of_one_trade() -> None:
    """SC-008.

    Three losses in a row draw down more than the worst of them. A maximum
    drawdown equal to the worst single trade is a different statistic under the
    same name.
    """
    losses = [outcome(kind=Outcome.STOP, ret=-0.02) for _ in range(3)]

    report = economic_report(losses, costs=COSTS, risk_per_trade=0.02)

    assert report.max_drawdown < -0.06


@pytest.mark.trace("REQ-BT-001")
def test_the_backtest_package_consults_no_clock() -> None:
    """SC-012, FR-017."""
    from pathlib import Path

    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "backtest"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock"
