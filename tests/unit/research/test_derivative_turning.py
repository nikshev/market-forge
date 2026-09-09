"""EXP-012's causal derivative turning points (REQ-EXP-012)."""

from __future__ import annotations

import math

import pytest

from channelflow.extrema import CenteredTransformRejected
from channelflow.research.derivative_turning import (
    HORIZONS,
    CenteredCandidateRejected,
    CenteredLabeller,
    Method,
    compare_turning_methods,
    default_methods,
    label_turns,
    local_polynomial,
)
from tests.unit.channels.conftest import make_bar


def swings(n: int = 400, *, period: int = 40, amp: float = 0.03):
    return [
        make_bar(index=i, close=100.0 * math.exp(amp * math.sin(2 * math.pi * i / period)))
        for i in range(n)
    ]


@pytest.mark.trace("REQ-EXP-012")
def test_every_horizon_the_prd_names_is_evaluated() -> None:
    """EXP-012: "at horizons 3/6/12/24 bars"."""
    assert HORIZONS == (3, 6, 12, 24)

    report = compare_turning_methods(swings())

    for result in report.results.values():
        assert [h.horizon for h in result.by_horizon] == list(HORIZONS)


@pytest.mark.trace("REQ-EXP-012")
def test_every_candidate_is_compared() -> None:
    """Four causal methods. The Savitzky-Golay equivalent is absent by design:
    its one-sided form is the causal local polynomial already here, and its
    centred form is a label maker."""
    report = compare_turning_methods(swings())

    assert set(report.results) == {m.name for m in default_methods()}
    assert len(report.results) == 4


@pytest.mark.trace("REQ-EXP-012")
def test_a_centred_candidate_is_refused() -> None:
    """PRD §13A.6, and the line EXP-012 ends on: centred filters are label
    references, never live candidates.

    A centred filter is the best turning-point detector there is -- it sees both
    sides of the turn -- and that is exactly why it cannot be one. Its answer at
    bar `t` changes when bar `t + 1` arrives.
    """
    centred = Method(
        name="cheating",
        transform=CenteredLabeller(name="cheating"),
        slopes=lambda values: list(values),
    )

    with pytest.raises(CenteredCandidateRejected, match="cheating"):
        compare_turning_methods(swings(), methods=(centred,))


@pytest.mark.trace("REQ-EXP-012")
def test_the_refusal_comes_from_the_production_guard() -> None:
    """`require_causal` is REQ-NRT-D's own guard, not a copy of its logic."""
    centred = Method(
        name="cheating",
        transform=CenteredLabeller(name="cheating"),
        slopes=lambda values: list(values),
    )

    with pytest.raises(CenteredCandidateRejected) as raised:
        compare_turning_methods(swings(), methods=(centred,))

    assert isinstance(raised.value.__cause__, CenteredTransformRejected)


@pytest.mark.trace("REQ-EXP-012")
def test_the_labels_are_made_by_a_centred_filter_and_the_report_says_so() -> None:
    """§13A.6 permits exactly this: "centered peak-finding may create labels and
    diagnostics, never live signals". A report that did not say which side of
    that line its labels came from would leave a reader assuming the wrong one.
    """
    report = compare_turning_methods(swings())

    assert report.labelled_turns > 0
    assert report.label_method == "centered_smoother"
    # Both halves of the claim, because either alone is misreadable: "cannot run
    # live" without "centred filter" reads as a caveat about the candidates, and
    # "centred filter" without it reads as a description of the method under test.
    assert "centred filter" in report.note
    assert "cannot run live" in report.note


@pytest.mark.trace("REQ-EXP-012")
def test_the_labeller_declares_itself_centred() -> None:
    """So `require_causal` refuses it if anyone ever hands it to the live path.
    The declaration is the guard; a comment would not be."""
    assert CenteredLabeller().centered is True


@pytest.mark.trace("REQ-EXP-012")
def test_a_local_polynomial_reads_the_right_edge_of_its_window() -> None:
    """Which is what makes it causal.

    On a rising series the slope at the last bar is positive. Fitted to a window
    centred on that bar it would be the same arithmetic and a forbidden
    estimator -- and on this series it would also be wrong, because the series
    turns right after.
    """
    rising_then_falling = [float(i) for i in range(20)] + [float(20 - i) for i in range(20)]

    slopes = local_polynomial(order=2, window=9)(rising_then_falling)

    assert slopes[19] > 0.0, "the fit at the peak should still be rising"
    # Three bars past the peak the window still holds more rise than fall, so a
    # fit read at its centre is still rising (+0.63 here) while the same fit read
    # at its right edge has turned (-0.46). Only the second number is available
    # at bar 22, and only the second one is this estimator's answer.
    assert slopes[22] < 0.0, "past the peak the right edge has turned"


@pytest.mark.trace("REQ-EXP-012")
def test_precision_is_absent_for_a_method_that_calls_nothing() -> None:
    """Precision over no calls is not zero, and a silent method is not a wrong
    one."""
    silent = Method(
        name="silent",
        transform=default_methods()[0].transform,
        slopes=lambda values: [1.0] * len(values),
    )

    report = compare_turning_methods(swings(), methods=(silent,))

    result = report.results["silent"]
    assert result.turns_called == 0
    assert all(h.precision is None for h in result.by_horizon)


@pytest.mark.trace("REQ-EXP-012")
def test_a_longer_horizon_cannot_lower_precision() -> None:
    """A call near a turn at three bars is near it at twenty-four. Monotonic by
    construction, and a measure that was not would make the four horizons
    incomparable."""
    report = compare_turning_methods(swings())

    for result in report.results.values():
        precisions = [h.precision for h in result.by_horizon if h.precision is not None]
        assert precisions == sorted(precisions)


@pytest.mark.trace("REQ-EXP-012")
def test_a_smoother_method_calls_fewer_turns_than_the_raw_one() -> None:
    """The trade-off the comparison exists to show: the raw sign change fires on
    every wiggle, and a fitted slope does not."""
    noisy = [
        make_bar(
            index=i,
            close=100.0
            * math.exp(0.03 * math.sin(2 * math.pi * i / 40) + 0.004 * math.sin(i * 2.3)),
        )
        for i in range(400)
    ]

    report = compare_turning_methods(noisy)

    raw = report.results["trailing_sign_change"].turns_called
    fitted = report.results["local_polynomial_3"].turns_called
    assert raw > fitted


@pytest.mark.trace("REQ-EXP-012")
def test_two_runs_produce_equal_reports() -> None:
    bars = swings()

    assert compare_turning_methods(bars) == compare_turning_methods(bars)


@pytest.mark.trace("REQ-EXP-012")
def test_a_call_beyond_the_tolerance_counts_only_at_the_longer_horizons() -> None:
    """The horizon is what the four numbers differ by, so a case has to exist
    where they differ. A call eight bars before the turn is outside the two-bar
    tolerance and outside a three-bar horizon; it is inside a twelve-bar one.

    Without this, every horizon could report the same number and the comparison
    would be four copies of one measurement.
    """
    triangle = [100.0 + i for i in range(30)] + [130.0 - i for i in range(1, 31)]
    bars = [make_bar(index=i, close=value) for i, value in enumerate(triangle)]
    assert label_turns(bars) == [30], "one labelled turn, so the arithmetic is readable"

    calls_at_22 = Method(
        name="early",
        transform=default_methods()[0].transform,
        slopes=lambda values: [1.0] * 22 + [-1.0] * (len(values) - 22),
    )

    report = compare_turning_methods(bars, methods=(calls_at_22,), tolerance_bars=2)

    by_horizon = {h.horizon: h for h in report.results["early"].by_horizon}
    assert by_horizon[3].calls == 1
    assert by_horizon[3].precision == 0.0
    assert by_horizon[6].precision == 0.0
    assert by_horizon[12].precision == 1.0
    assert by_horizon[24].precision == 1.0
