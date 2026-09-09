"""EXP-003's rejection detector comparison (REQ-EXP-003)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.backtest import CostModel, CostsRequired
from channelflow.channels import ChannelQuality, ChannelSnapshot, RollingOLSChannel
from channelflow.research.detector_comparison import (
    DETECTORS,
    UNAVAILABLE,
    CandidateLife,
    candidate_lives,
    compare_detectors,
    detector_metrics,
)
from channelflow.signals import (
    CandidateState,
    CloseBackInside,
    Transition,
    TwoBarConfirmation,
    WickOnly,
)
from tests.unit.channels.conftest import MINUTE_NS, make_bar

from .test_channel_comparison import series

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def snapshot(*, center: float = 100.0, half_width: float = 5.0) -> ChannelSnapshot:
    return ChannelSnapshot(
        as_of_ns=0,
        model_name="test",
        model_version="1.0.0",
        lookback=60,
        center_now=center,
        upper_now=center + half_width,
        lower_now=center - half_width,
        slope_normalized=-0.5,
        width_pct=2.0,
        quality=ChannelQuality(score=0.9, submetrics={}, contributing=(), unavailable=()),
        source_max_event_time_ns=0,
    )


def shaped(*, open_: float, high: float, low: float, close: float) -> object:
    bar = make_bar(index=0, close=close)
    return bar.model_copy(
        update={
            "open": Decimal(str(open_)),
            "high": Decimal(str(high)),
            "low": Decimal(str(low)),
            "close": Decimal(str(close)),
        }
    )


@pytest.mark.trace("REQ-EXP-003")
def test_all_four_detectors_appear_in_the_report() -> None:
    """FR-001 of the derived criteria.

    EXP-003 names four. Three are built and the fourth is reported as
    unavailable -- a report silent about it reads as a comparison of four.
    """
    report = compare_detectors(series(), costs=COSTS)

    assert set(report.entries) == set(DETECTORS) | set(UNAVAILABLE)
    assert len(report.entries) == 4


@pytest.mark.trace("REQ-EXP-003")
def test_the_unavailable_detector_is_named_and_never_scored() -> None:
    """The second criterion every comparison-shaped experiment shares.

    The order-flow detector cannot see order flow: the protocol carries a bar
    and a channel. Scored anyway it would report a detector that never saw the
    inputs it is named after, and its number would be compared with three that
    did.
    """
    report = compare_detectors(series(), costs=COSTS)

    entry = report.entries["order_flow_confirmation"]
    assert entry.expectancy_r is None
    assert entry.confirmations == 0
    assert "order-flow features" in entry.reason
    assert "order_flow_confirmation" not in report.ranking


@pytest.mark.trace("REQ-EXP-003")
def test_the_wick_detector_reads_the_bar_the_prd_describes() -> None:
    """PRD §21.3: "upper wick/body ratio above threshold".

    A long upper wick over a small body, at the upper boundary, is the shape the
    section names.
    """
    detector = WickOnly(min_wick_body_ratio=2.0)
    channel = snapshot()

    rejected = detector.rejected(
        shaped(open_=104.0, high=110.0, low=103.5, close=104.5),  # type: ignore[arg-type]
        channel,
        boundary="upper",
        direction="short",
    )
    held = detector.rejected(
        shaped(open_=104.0, high=105.0, low=100.0, close=104.5),  # type: ignore[arg-type]
        channel,
        boundary="upper",
        direction="short",
    )

    assert rejected
    assert not held


@pytest.mark.trace("REQ-EXP-003")
def test_a_bodyless_bar_with_a_wick_is_a_rejection_not_a_division_by_zero() -> None:
    """A doji that spiked through the boundary and came back is the shape."""
    detector = WickOnly()

    assert detector.rejected(
        shaped(open_=104.0, high=110.0, low=104.0, close=104.0),  # type: ignore[arg-type]
        snapshot(),
        boundary="upper",
        direction="short",
    )


@pytest.mark.trace("REQ-EXP-003")
def test_the_two_bar_detector_cannot_answer_on_its_first_bar() -> None:
    """PRD §21.3's "next bar closes lower" needs a previous close to compare to.

    Answering on the first bar would make it the single-bar detector it is
    supposed to differ from.
    """
    detector = TwoBarConfirmation()
    channel = snapshot()

    first = detector.rejected(
        shaped(open_=104.0, high=105.0, low=103.0, close=104.0),  # type: ignore[arg-type]
        channel,
        boundary="upper",
        direction="short",
    )
    lower = detector.rejected(
        shaped(open_=104.0, high=104.5, low=102.0, close=102.5),  # type: ignore[arg-type]
        channel,
        boundary="upper",
        direction="short",
    )

    assert not first
    assert lower


@pytest.mark.trace("REQ-EXP-003")
def test_the_two_bar_detector_refuses_a_higher_close() -> None:
    """The direction matters: a short's confirmation is a lower close."""
    detector = TwoBarConfirmation()
    channel = snapshot()

    detector.rejected(
        shaped(open_=104.0, high=105.0, low=103.0, close=104.0),  # type: ignore[arg-type]
        channel,
        boundary="upper",
        direction="short",
    )
    higher = detector.rejected(
        shaped(open_=104.0, high=106.0, low=104.0, close=105.5),  # type: ignore[arg-type]
        channel,
        boundary="upper",
        direction="short",
    )

    assert not higher


@pytest.mark.trace("REQ-EXP-003")
def test_each_detector_runs_inside_the_production_machine() -> None:
    """PRD §25.2 forbids a second implementation of the strategy logic.

    Every entry's confirmations come from `SignalMachine`, so a comparison that
    reimplemented the lifecycle would be comparing its own copy. Checked by
    source: the module names no state and builds no transition.
    """
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "channelflow"
        / "research"
        / "detector_comparison.py"
    ).read_text()

    assert "SignalMachine(" in source
    assert "Transition(" not in source


@pytest.mark.trace("REQ-EXP-003")
def test_the_four_metrics_are_reported_for_a_detector_that_traded() -> None:
    """The derived metric set: count, lag, later-invalidation share, expectancy.

    Each is a different way a detector can be wrong -- too few, too slow, too
    eager, or unprofitable -- and collapsing them into one score would hide
    which.
    """
    report = compare_detectors(series(n=600), costs=COSTS)

    traded = [e for e in report.entries.values() if e.confirmations > 0]
    assert traded, "the fixture must confirm something, or nothing is measured"
    for entry in traded:
        assert entry.median_lag_bars is not None
        assert entry.later_invalidated is not None
        assert 0.0 <= entry.later_invalidated <= 1.0


@pytest.mark.trace("REQ-EXP-003")
def test_a_permissive_detector_confirms_sooner_than_a_strict_one() -> None:
    """The lag metric, and the control for it.

    `WickOnly` answers from one bar's shape; `TwoBarConfirmation` cannot answer
    before its second. If the measure did not show that, it would not be
    measuring lag.
    """
    report = compare_detectors(
        series(n=600),
        costs=COSTS,
        detectors={"wick_only": WickOnly(), "two_bar": TwoBarConfirmation()},
        unavailable={},
    )

    wick = report.entries["wick_only"]
    two_bar = report.entries["two_bar"]
    if wick.median_lag_bars is None or two_bar.median_lag_bars is None:
        pytest.skip("the fixture confirmed nothing under one of the detectors")
    assert wick.median_lag_bars <= two_bar.median_lag_bars


@pytest.mark.trace("REQ-EXP-003")
def test_a_detector_that_confirms_nothing_is_reported_with_its_reason() -> None:
    """Absent is not zero, and a detector that never fires is not one that lost."""

    class NeverRejects:
        name = "never"

        def rejected(self, bar: object, channel: object, **kwargs: object) -> bool:
            return False

    report = compare_detectors(
        series(),
        costs=COSTS,
        detectors={"never": NeverRejects()},  # type: ignore[dict-item]
        unavailable={},
    )

    entry = report.entries["never"]
    assert entry.expectancy_r is None
    assert entry.confirmations == 0
    assert "no candidate reached confirmation" in entry.reason


@pytest.mark.trace("REQ-EXP-003")
def test_the_ranking_is_by_expectancy_and_excludes_the_unscored() -> None:
    """A ranking is an ordering of things that were measured."""
    report = compare_detectors(series(n=600), costs=COSTS)

    scored = {name for name, e in report.entries.items() if e.expectancy_r is not None}
    assert set(report.ranking) == scored
    values = [report.entries[name].expectancy_r or 0.0 for name in report.ranking]
    assert values == sorted(values, reverse=True)


@pytest.mark.trace("REQ-EXP-003")
def test_the_comparison_without_costs_is_refused() -> None:
    """PRD §41 rule 9. Tested with no detector at all, so only this refusal can fire."""
    with pytest.raises(CostsRequired):
        compare_detectors(series(), costs=None, detectors={}, unavailable={})


@pytest.mark.trace("REQ-EXP-003")
def test_two_runs_produce_equal_reports() -> None:
    """One input, one report -- including the stateful two-bar detector.

    Its one bar of memory must not survive from one run into the next, or the
    second run measures a detector the first one left mid-candidate.
    """
    bars = series(n=600)

    assert compare_detectors(bars, costs=COSTS) == compare_detectors(bars, costs=COSTS)


@pytest.mark.trace("REQ-EXP-003")
def test_the_close_back_inside_detector_is_the_one_the_engine_ships_with() -> None:
    """The comparison must include the production default, or it compares alternatives
    to each other and not to what is running."""
    assert isinstance(DETECTORS["close_back_inside"], CloseBackInside)


@pytest.mark.trace("REQ-EXP-003")
def test_a_confirmation_the_market_takes_back_is_counted() -> None:
    """The "too eager" metric, over hand-built transitions.

    A detector that confirms setups the market immediately invalidates is wrong
    in a way none of the other three metrics shows: it confirms plenty, quickly,
    and its expectancy is somebody else's problem. Forcing that path through the
    whole pipeline is far harder than describing it.
    """
    lives = candidate_lives(
        [
            Transition(
                from_state=CandidateState.NONE,
                to_state=CandidateState.APPROACH,
                bar_close_time_ns=1,
                reason="entered the zone",
            ),
            Transition(
                from_state=CandidateState.REJECTION_PENDING,
                to_state=CandidateState.CONFIRMED,
                bar_close_time_ns=4,
                reason="rejection held",
            ),
            Transition(
                from_state=CandidateState.CONFIRMED,
                to_state=CandidateState.INVALIDATED,
                bar_close_time_ns=6,
                reason="close beyond outer tolerance",
            ),
        ]
    )

    assert len(lives) == 1
    assert lives[0].confirmed_at_ns == 4
    assert lives[0].invalidated_after_confirm


@pytest.mark.trace("REQ-EXP-003")
def test_an_invalidation_before_confirmation_is_not_counted_as_taken_back() -> None:
    """A candidate that died on the way to confirmation was never confirmed.

    Counting it would make every detector look eager in proportion to how many
    setups it declined.
    """
    lives = candidate_lives(
        [
            Transition(
                from_state=CandidateState.NONE,
                to_state=CandidateState.APPROACH,
                bar_close_time_ns=1,
                reason="entered the zone",
            ),
            Transition(
                from_state=CandidateState.TOUCH,
                to_state=CandidateState.INVALIDATED,
                bar_close_time_ns=3,
                reason="channel quality collapsed",
            ),
        ]
    )

    assert lives[0].confirmed_at_ns is None
    assert not lives[0].invalidated_after_confirm


@pytest.mark.trace("REQ-EXP-003")
def test_the_lag_is_the_distance_from_opening_to_confirmation() -> None:
    """The lifecycle is at least three moves -- approach, touch, pending, confirmed --
    so a confirmation can never be zero bars after its own opening. A lag of zero
    means the measure is subtracting a number from itself."""
    report = compare_detectors(series(n=600), costs=COSTS)

    measured = [e for e in report.entries.values() if e.median_lag_bars is not None]
    assert measured
    assert all(e.median_lag_bars >= 2.0 for e in measured)


@pytest.mark.trace("REQ-EXP-003")
def test_expectancy_counts_only_out_of_sample_confirmations() -> None:
    """PRD §41 rule 10. The whole run confirms more than the held-out segment does."""
    bars = series(n=600)

    report = compare_detectors(bars, costs=COSTS)

    for entry in report.entries.values():
        if entry.expectancy_r is None:
            continue
        assert entry.trades < entry.confirmations


@pytest.mark.trace("REQ-EXP-003")
def test_the_wick_detector_reads_the_lower_wick_for_a_long() -> None:
    """A long rejects off the lower boundary, and its wick points down.

    Reading the upper wick for both directions passes every short-only fixture
    and inverts the detector on half the setups it will ever see.
    """
    detector = WickOnly(min_wick_body_ratio=2.0)
    channel = snapshot()

    long_rejection = detector.rejected(
        shaped(open_=96.0, high=96.5, low=90.0, close=95.5),  # type: ignore[arg-type]
        channel,
        boundary="lower",
        direction="long",
    )
    upper_wick_only = detector.rejected(
        shaped(open_=95.5, high=102.0, low=95.4, close=96.0),  # type: ignore[arg-type]
        channel,
        boundary="lower",
        direction="long",
    )

    assert long_rejection
    assert not upper_wick_only


@pytest.mark.trace("REQ-EXP-003")
def test_the_taken_back_share_reaches_the_report() -> None:
    """The "too eager" metric, end to end over constructed lives.

    Two confirmations, one of which the market invalidated afterwards. No bar
    series found so far drives the machine down that path, so the metric is
    measured where it can be: from the lives that describe it. A detector that
    confirms plenty, quickly, and has half of them taken back is wrong in a way
    the other three metrics do not show.
    """
    lives = [
        CandidateLife(opened_at_ns=0, confirmed_at_ns=3 * MINUTE_NS),
        CandidateLife(
            opened_at_ns=10 * MINUTE_NS,
            confirmed_at_ns=14 * MINUTE_NS,
            invalidated_after_confirm=True,
        ),
    ]

    entry = detector_metrics(
        "constructed",
        lives,
        series(),
        model=RollingOLSChannel(),
        split=200,
        horizon=10,
        costs=COSTS,
        risk_per_trade=0.02,
    )

    assert entry.confirmations == 2
    assert entry.later_invalidated == pytest.approx(0.5)
    assert entry.median_lag_bars == pytest.approx(3.5)
