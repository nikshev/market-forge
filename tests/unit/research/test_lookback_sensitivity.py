"""EXP-002's lookback sweep and its plateau rule (REQ-EXP-002)."""

from __future__ import annotations

import pytest

from channelflow.backtest import CostModel, CostsRequired
from channelflow.research.lookback_sensitivity import (
    LOOKBACKS,
    SweepEntry,
    find_plateau,
    recommend,
    sweep_lookbacks,
)

from .test_channel_comparison import series

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def entry(lookback: int, value: float | None) -> SweepEntry:
    return SweepEntry(lookback=lookback, expectancy_r=value, trades=1 if value else 0)


@pytest.mark.trace("REQ-EXP-002")
def test_all_six_lookbacks_are_swept() -> None:
    """SC-001, FR-001.

    EXP-002 lists them: 40, 60, 80, 100, 150, 200. A lookback missing from the
    report is one the recommendation never considered.
    """
    assert LOOKBACKS == (40, 60, 80, 100, 150, 200)

    report = sweep_lookbacks(series(n=800), costs=COSTS)

    assert [e.lookback for e in report.entries] == list(LOOKBACKS)


@pytest.mark.trace("REQ-EXP-002")
def test_a_lookback_the_series_cannot_hold_is_reported_and_the_rest_still_run() -> None:
    """SC-002, FR-003.

    280 bars cannot hold a 200-bar lookback once a split and a horizon are taken
    out, and can hold a 40-bar one. That is a fact about the series, and it must
    not cost the reader the lookbacks that fitted.

    The reason has to be this one: an entry with no expectancy because nothing
    traded is a different absence, and a test satisfied by either would not be
    testing this branch at all.
    """
    report = sweep_lookbacks(series(n=280), costs=COSTS)

    by_lookback = {e.lookback: e for e in report.entries}
    assert "cannot hold" in by_lookback[200].reason
    assert by_lookback[200].expectancy_r is None
    assert by_lookback[40].expectancy_r is not None


@pytest.mark.trace("REQ-EXP-002")
def test_the_plateau_is_the_widest_run_within_the_tolerance() -> None:
    """SC-003, FR-004, FR-005.

    Three adjacent lookbacks agreeing beats two agreeing, whatever the values.
    """
    entries = [
        entry(40, 0.10),
        entry(60, 0.50),
        entry(80, 0.52),
        entry(100, 0.51),
        entry(150, 0.90),
        entry(200, 0.92),
    ]

    plateau = find_plateau(entries, tolerance=0.05)

    assert plateau is not None
    assert plateau.lookbacks == (60, 80, 100)


@pytest.mark.trace("REQ-EXP-002")
def test_a_jagged_sweep_has_no_plateau() -> None:
    """SC-004, FR-005.

    Nothing adjacent agrees, so there is nowhere the choice does not matter --
    which is a result, and the one EXP-002's rule is designed to surface.
    """
    entries = [entry(40, 0.1), entry(60, 0.9), entry(80, 0.2), entry(100, 1.1)]

    assert find_plateau(entries, tolerance=0.05) is None


@pytest.mark.trace("REQ-EXP-002")
def test_a_wider_tolerance_never_shrinks_the_plateau() -> None:
    """SC-005, FR-004.

    Monotonic by construction. A tolerance that could shrink a plateau would
    make the parameter impossible to reason about.
    """
    entries = [entry(40, 0.10), entry(60, 0.20), entry(80, 0.22), entry(100, 0.60)]

    narrow = find_plateau(entries, tolerance=0.05)
    wide = find_plateau(entries, tolerance=0.20)

    assert narrow is not None and wide is not None
    assert len(wide.lookbacks) >= len(narrow.lookbacks)


@pytest.mark.trace("REQ-EXP-002")
def test_an_absent_value_splits_a_plateau_rather_than_being_skipped() -> None:
    """SC-008, FR-010.

    Joining the two sides across a lookback nobody could measure produces a
    plateau that exists only in the report.
    """
    entries = [
        entry(40, 0.50),
        entry(60, 0.51),
        entry(80, None),
        entry(100, 0.50),
        entry(150, 0.49),
    ]

    plateau = find_plateau(entries, tolerance=0.05)

    assert plateau is not None
    assert 80 not in plateau.lookbacks
    assert len(plateau.lookbacks) == 2


@pytest.mark.trace("REQ-EXP-002")
def test_equally_wide_plateaus_are_broken_by_a_declared_rule() -> None:
    """SC-003, FR-006.

    Two runs of two. Taking whichever the scan reached first makes the
    recommendation depend on iteration order, which is not a market fact.
    """
    entries = [
        entry(40, 0.50),
        entry(60, 0.51),
        entry(80, 0.10),
        entry(100, 0.80),
        entry(150, 0.81),
    ]

    plateau = find_plateau(entries, tolerance=0.05)

    # The declared rule: widest, then the highest expectancy in it.
    assert plateau is not None
    assert plateau.lookbacks == (100, 150)


@pytest.mark.trace("REQ-EXP-002")
def test_the_recommendation_comes_from_the_plateau_not_the_peak() -> None:
    """SC-006, FR-007, FR-008.

    EXP-002's instruction, and the case it is about: the best expectancy sits on
    a lookback whose neighbours disagree with it, and the steady region scores
    lower. A report that named only the peak would be selecting on maximum PnL
    whatever its surrounding text said.
    """
    entries = [
        entry(40, 0.50),
        entry(60, 0.51),
        entry(80, 0.52),
        entry(100, 0.10),
        entry(150, 2.00),
        entry(200, 0.05),
    ]

    result = recommend(entries, tolerance=0.05)

    assert result.peak_lookback == 150
    assert result.lookback in (40, 60, 80)
    assert result.lookback != result.peak_lookback
    assert result.plateau is not None


@pytest.mark.trace("REQ-EXP-002")
def test_with_no_plateau_nothing_is_recommended_and_the_peak_is_not_substituted() -> None:
    """SC-007, FR-009.

    The fallback is the whole failure mode. "No stable region" is a finding; the
    peak offered in its place is the rule broken by a default.
    """
    entries = [entry(40, 0.1), entry(60, 0.9), entry(80, 0.2), entry(100, 1.1)]

    result = recommend(entries, tolerance=0.05)

    assert result.lookback is None
    assert result.plateau is None
    assert result.peak_lookback == 100
    assert "no plateau" in result.reason


@pytest.mark.trace("REQ-EXP-002")
def test_a_recommendation_carries_the_plateau_it_came_from() -> None:
    """FR-007.

    A number without the region behind it cannot be checked, and the region is
    the reason the number is trustworthy at all.
    """
    entries = [entry(40, 0.50), entry(60, 0.51), entry(80, 0.52)]

    result = recommend(entries, tolerance=0.05)

    assert result.plateau is not None
    assert result.lookback in result.plateau.lookbacks


@pytest.mark.trace("REQ-EXP-002")
def test_the_recommendation_is_the_middle_of_the_plateau_not_its_edge() -> None:
    """FR-007.

    The centre is the furthest point from either edge, which is the whole reason
    to prefer a plateau: an edge is one noisy neighbour away from being off it.
    """
    entries = [
        entry(40, 0.10),
        entry(60, 0.50),
        entry(80, 0.52),
        entry(100, 0.51),
        entry(150, 0.90),
    ]

    result = recommend(entries, tolerance=0.05)

    assert result.plateau is not None
    assert result.plateau.lookbacks == (60, 80, 100)
    assert result.lookback == 80


@pytest.mark.trace("REQ-EXP-002")
def test_a_sweep_without_costs_is_refused() -> None:
    """SC-009, FR-011.

    Expectancy is an economic metric, and PRD §41 rule 9 governs it wherever it
    is computed.
    """
    # An empty sweep, so nothing downstream is ever called: only this
    # function's own refusal can raise, which is what makes it load-bearing
    # rather than a restatement of the one inside the comparison.
    with pytest.raises(CostsRequired):
        sweep_lookbacks(series(), costs=None, lookbacks=())


@pytest.mark.trace("REQ-EXP-002")
def test_two_sweeps_produce_equal_reports() -> None:
    """SC-010, FR-012."""
    bars = series()

    assert sweep_lookbacks(bars, costs=COSTS) == sweep_lookbacks(bars, costs=COSTS)


@pytest.mark.trace("REQ-EXP-002")
def test_a_single_lookback_is_not_a_plateau() -> None:
    """FR-005.

    A run of one is the peak with another name, and recommending it would be
    exactly what EXP-002 forbids.
    """
    entries = [entry(40, 0.5), entry(60, 5.0), entry(80, 0.1)]

    plateau = find_plateau(entries, tolerance=0.01)

    assert plateau is None or len(plateau.lookbacks) >= 2
