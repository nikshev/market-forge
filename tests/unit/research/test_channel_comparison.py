"""EXP-001's channel model comparison (REQ-EXP-001)."""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from channelflow.backtest import BacktestRunner, CostModel
from channelflow.bars import Bar
from channelflow.channels import ChannelFitError, QuantileChannel, RollingOLSChannel
from channelflow.research.channel_comparison import (
    MODELS,
    SeriesTooShort,
    compare_channel_models,
)
from channelflow.signals import CandidateState
from tests.unit.channels.conftest import log_linear_series, make_bar

COSTS = CostModel(fee_bps=5.0, slippage_bps=5.0)


def series(n: int = 400, *, noise: float = 0.01) -> list[Bar]:
    """Enough bars for a 60-bar lookback, a forward horizon and a test split."""
    bars = []
    for i in range(n):
        drift = 0.0004 * i
        wobble = noise * math.sin(i * 0.55)
        swing = -0.05 if i % 90 < 4 else 0.0
        close = 100.0 * math.exp(drift + wobble + swing)
        bar = make_bar(index=i, close=close)
        # A real range, so an outcome can touch a level inside a bar.
        bars.append(
            bar.model_copy(
                update={
                    "high": Decimal(str(round(close * 1.004, 8))),
                    "low": Decimal(str(round(close * 0.996, 8))),
                    "open": Decimal(str(round(close, 8))),
                }
            )
        )
    return bars


@pytest.mark.trace("REQ-EXP-001")
def test_all_five_models_are_compared() -> None:
    """SC-001, FR-001.

    EXP-001 names five. A report missing one is a comparison whose winner might
    not have been in it.
    """
    report = compare_channel_models(series(), costs=COSTS)

    assert set(report.entries) == set(MODELS)
    assert len(MODELS) == 5


@pytest.mark.trace("REQ-EXP-001")
def test_every_model_sees_the_same_bars_and_split() -> None:
    """SC-001, FR-002.

    Models measured over different data are not being compared.
    """
    report = compare_channel_models(series(), costs=COSTS)

    assert report.in_sample_bars > 0
    assert report.out_of_sample_bars > 0
    fitted = [e for e in report.entries.values() if e.coverage is not None]
    assert len({e.fits for e in fitted}) == 1


@pytest.mark.trace("REQ-EXP-001")
def test_a_wider_band_covers_more() -> None:
    """SC-002, FR-004.

    The control for the coverage measure itself: if a model with visibly wider
    bands did not score higher, the number would not be measuring coverage.
    """
    bars = series()

    narrow = compare_channel_models(
        bars, costs=COSTS, models={"narrow": RollingOLSChannel(quantile_low=0.4, quantile_high=0.6)}
    )
    wide = compare_channel_models(
        bars, costs=COSTS, models={"wide": RollingOLSChannel(quantile_low=0.01, quantile_high=0.99)}
    )

    assert wide.entries["wide"].coverage > narrow.entries["narrow"].coverage


@pytest.mark.trace("REQ-EXP-001")
def test_coverage_looks_forward_from_each_fit() -> None:
    """SC-002, FR-004.

    A series that runs flat and then breaks into a hard trend. Looking forward
    from each fit the channel covers 31.7% of what followed; looking back over
    the same span it covers 49.2%, because those are the bars it was fitted on.
    The threshold sits between the two, and the gap is the whole point of the
    measure: a backward-looking version reports the model's own residuals back
    to it whatever the market did next.
    """
    report = compare_channel_models(_regime_break(), costs=COSTS, models={"m": RollingOLSChannel()})

    assert report.entries["m"].coverage < 0.4


def _regime_break() -> list[Bar]:
    """Flat for a hundred and fifty bars, then a trend the bands cannot hold."""
    bars = []
    for i in range(400):
        level = 0.0 if i < 150 else 0.004 * (i - 150)
        close = 100.0 * math.exp(level + 0.001 * math.sin(i * 0.7))
        bars.append(
            make_bar(index=i, close=close).model_copy(
                update={
                    "high": Decimal(str(round(close * 1.002, 8))),
                    "low": Decimal(str(round(close * 0.998, 8))),
                }
            )
        )
    return bars


@pytest.mark.trace("REQ-EXP-001")
def test_a_degenerate_channel_has_no_coverage_rather_than_perfect_coverage() -> None:
    """FR-004.

    A zero-width band covers nothing or everything depending on which way the
    rounding falls, and either reads as a measurement. There isn't one.
    """
    flat = [make_bar(index=i, close=100.0) for i in range(400)]

    report = compare_channel_models(
        flat, costs=COSTS, models={"q": QuantileChannel(minimum_width_pct=0.0)}
    )

    assert report.entries["q"].coverage is None


@pytest.mark.trace("REQ-EXP-001")
def test_stability_is_the_dispersion_not_the_average() -> None:
    """SC-003, FR-005.

    A steady trend has a large average slope and almost no variation in it; an
    oscillating series has an average near zero and a great deal of variation.
    Reporting the average would call the steady series the unstable one -- and a
    fixture where the two move together cannot tell the difference.
    """
    steady = _shaped(alternating=False)
    swinging = _shaped(alternating=True)

    one = compare_channel_models(steady, costs=COSTS, models={"m": RollingOLSChannel()})
    other = compare_channel_models(swinging, costs=COSTS, models={"m": RollingOLSChannel()})

    assert one.entries["m"].slope_stability < other.entries["m"].slope_stability
    assert one.entries["m"].width_stability < other.entries["m"].width_stability


def _shaped(*, alternating: bool) -> list[Bar]:
    """A steady trend, or an oscillation of the same amplitude."""
    bars = []
    for i in range(300):
        level = 0.02 * math.sin(i * 0.09) if alternating else 0.004 * i
        close = 100.0 * math.exp(level + 0.002 * math.sin(i * 1.7))
        bars.append(make_bar(index=i, close=close))
    return bars


@pytest.mark.trace("REQ-EXP-001")
def test_a_repainted_touch_is_counted_as_false() -> None:
    """SC-004, FR-007.

    A bar the later channel calls a perfect touch and the channel of the time did
    not. This is the measure PRD §2.1's critical risk shows up in: a chart full
    of perfect touches that were never touches when they happened.
    """
    report = compare_channel_models(series(noise=0.02), costs=COSTS)

    counts = [e.false_perfect_touches for e in report.entries.values() if e.coverage is not None]
    assert counts
    assert all(c >= 0 for c in counts)
    assert any(c > 0 for c in counts), (
        "no model repainted a touch on a noisy series; the measure is not seeing them"
    )


@pytest.mark.trace("REQ-EXP-001")
def test_the_cost_figure_is_deterministic() -> None:
    """SC-005, FR-008.

    A wall-clock figure changes between runs, and a report that cannot be
    compared with itself cannot be compared with another ([[ADR-049]]).
    """
    bars = series()

    first = compare_channel_models(bars, costs=COSTS)
    second = compare_channel_models(bars, costs=COSTS)

    assert [e.cost_units for e in first.entries.values()] == [
        e.cost_units for e in second.entries.values()
    ]
    assert all(e.cost_units > 0 for e in first.entries.values())


@pytest.mark.trace("REQ-EXP-001")
def test_the_cost_figure_separates_the_expensive_model_from_the_cheap_one() -> None:
    """SC-005, FR-008.

    The quantile fit enumerates every pair of points and the OLS fit does one
    least squares, so the first costs two orders of magnitude more per fit. A
    figure that did not say so would be counting fits, not cost.
    """
    report = compare_channel_models(
        series(),
        costs=COSTS,
        models={"cheap": RollingOLSChannel(), "dear": QuantileChannel()},
    )

    assert report.entries["dear"].cost_units > report.entries["cheap"].cost_units * 10


@pytest.mark.trace("REQ-EXP-001")
def test_expectancy_counts_only_out_of_sample_confirmations() -> None:
    """SC-006, FR-009.

    PRD §41 rule 10 keeps the test segment separate. The whole run confirms more
    setups than the held-out quarter does, so an expectancy computed over every
    confirmation is measuring the training data -- and would look better for it.
    """
    bars = series()

    report = compare_channel_models(
        bars, costs=COSTS, models={"m": RollingOLSChannel()}, test_fraction=0.25
    )

    whole_run = BacktestRunner(channel=RollingOLSChannel()).run(bars)
    all_confirmations = sum(
        1 for t in whole_run.transitions if t.to_state is CandidateState.CONFIRMED
    )

    assert report.entries["m"].trades > 0, "the fixture must trade, or nothing is measured"
    assert report.entries["m"].trades < all_confirmations


@pytest.mark.trace("REQ-EXP-001")
def test_expectancy_without_costs_is_refused() -> None:
    """SC-007, FR-011.

    PRD §41 rule 9, inherited from [[REQ-BT-001]]: the refusal belongs to the
    metric, so every consumer gets it.
    """
    from channelflow.backtest import CostsRequired

    # A model set that confirms nothing, so no downstream metric is ever
    # reached: only this function's own refusal can raise, which is what makes
    # it load-bearing rather than a duplicate of REQ-BT-001's.
    with pytest.raises(CostsRequired):
        compare_channel_models(
            series(), costs=None, models={"m": RollingOLSChannel()}, min_quality=1.01
        )


@pytest.mark.trace("REQ-EXP-001")
def test_a_model_with_no_setups_reports_absent_expectancy() -> None:
    """SC-008, FR-012.

    Zero expectancy means "traded and broke even". No setups means "never
    traded". A report that writes zero for both makes an untested model look
    like a mediocre one.
    """
    # A quality floor nothing can pass, so the machine opens nothing.
    report = compare_channel_models(
        series(), costs=COSTS, models={"a": RollingOLSChannel()}, min_quality=1.01
    )

    entry = report.entries["a"]
    assert entry.expectancy_r is None
    assert entry.trades == 0
    assert "no confirmed setup" in entry.expectancy_note


@pytest.mark.trace("REQ-EXP-001")
def test_two_runs_produce_equal_reports() -> None:
    """SC-009, FR-013."""
    bars = series()

    assert compare_channel_models(bars, costs=COSTS) == compare_channel_models(bars, costs=COSTS)


@pytest.mark.trace("REQ-EXP-001")
def test_a_series_too_short_for_the_longest_lookback_is_refused() -> None:
    """SC-010, FR-014.

    Models fitted on different amounts of history are not being compared with
    each other.
    """
    with pytest.raises(SeriesTooShort):
        compare_channel_models(log_linear_series(70), costs=COSTS)


@pytest.mark.trace("REQ-EXP-001")
def test_a_model_that_cannot_fit_is_reported_and_does_not_stop_the_others() -> None:
    """SC-001, FR-003.

    One model's refusal is a fact about that model. Ending the run would make
    the comparison unavailable whenever any candidate failed -- which is when it
    is most wanted.
    """

    class Unfittable:
        """A model whose lookback is fine and whose fit is not.

        A stub rather than a real model with an impossible lookback: that would
        trip the series-length guard first, which is a different refusal, about
        the comparison as a whole rather than about one model.
        """

        lookback = 60

        def fit(self, bars: list[Bar], *, as_of_ns: int) -> object:
            raise ChannelFitError("this model refuses this data")

    report = compare_channel_models(
        series(),
        costs=COSTS,
        models={
            "fine": RollingOLSChannel(lookback=60),
            "impossible": Unfittable(),  # type: ignore[dict-item]
        },
    )

    assert report.entries["fine"].coverage is not None
    assert report.entries["impossible"].coverage is None
    assert report.entries["impossible"].reason


@pytest.mark.trace("REQ-EXP-001")
def test_a_model_whose_outcomes_are_all_ambiguous_reports_no_expectancy() -> None:
    """FR-012, and PRD §40's rule carried into the experiment.

    Every bar here spans both the channel's centre and its boundary, so every
    setup resolves ambiguous. The model traded and nothing can be said about the
    result -- which is a different statement from breaking even, and from never
    trading. Without this the experiment raises out of the metric layer instead
    of reporting what happened.
    """
    wide = [
        b.model_copy(
            update={
                "high": Decimal(str(round(float(b.close) * 1.30, 8))),
                "low": Decimal(str(round(float(b.close) * 0.70, 8))),
            }
        )
        for b in series()
    ]

    report = compare_channel_models(wide, costs=COSTS, models={"m": RollingOLSChannel()})

    entry = report.entries["m"]
    assert entry.expectancy_r is None
    assert "resolvable" in entry.expectancy_note
