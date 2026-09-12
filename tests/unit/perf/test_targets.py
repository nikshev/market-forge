"""The measurement arithmetic itself (REQ-WP-057).

`tests/perf/` measures the system; these measure the thing doing the measuring.
The distinction earned its place: a mutation sweep over the arithmetic left six
survivors, because every assertion in `tests/perf/` is about the code under
measurement and none is about the percentile, the headroom or the guards.

A harness whose percentile is a mean reports a number that is confident, plausible
and wrong -- which is the failure this repository keeps meeting, arriving through
the instrument rather than the subject.
"""

from __future__ import annotations

import pytest

from channelflow.perf import Measurement, Target, headroom, scaling_ratio, timed
from channelflow.perf.targets import NS_PER_SECOND, TARGETS

A_TARGET = Target(name="t", stated="a second", budget_ns=NS_PER_SECOND)


@pytest.mark.trace("REQ-WP-057")
def test_a_percentile_is_a_sample_that_happened() -> None:
    """Nearest-rank, not interpolated. An interpolated p95 over twenty samples
    reports a duration nothing took, and the question here is what the slow runs
    cost."""
    measurement = Measurement(name="m", samples_ns=tuple(range(1, 21)))
    assert measurement.percentile_ns(0.95) == 19
    assert measurement.percentile_ns(0.95) in measurement.samples_ns
    assert measurement.percentile_ns(1.0) == 20
    assert measurement.percentile_ns(0.05) == 1


@pytest.mark.trace("REQ-WP-057")
def test_a_p95_is_not_a_p50_and_neither_is_a_mean() -> None:
    """The distinction the whole measurement rests on: §36 states one target as
    a p95, and a mean over a run with one slow outlier hides exactly the outlier
    a percentile exists for."""
    #: Nineteen fast runs and one slow one -- the shape a busy machine produces.
    samples = tuple([10] * 19 + [1_000])
    measurement = Measurement(name="m", samples_ns=samples)

    assert measurement.p50_ns == 10
    assert measurement.p95_ns == 10
    assert measurement.percentile_ns(1.0) == 1_000

    mean = sum(samples) / len(samples)
    assert mean != measurement.p50_ns
    assert mean > measurement.p95_ns


@pytest.mark.trace("REQ-WP-057")
def test_the_p95_moves_when_the_slow_tail_grows() -> None:
    """The direction that makes it a p95 rather than a label."""
    fast = Measurement(name="m", samples_ns=tuple([10] * 19 + [11]))
    slow = Measurement(name="m", samples_ns=tuple([10] * 18 + [900, 1_000]))
    assert fast.p50_ns == slow.p50_ns == 10
    assert slow.p95_ns > fast.p95_ns


@pytest.mark.trace("REQ-WP-057")
def test_a_measurement_of_nothing_measured_nothing() -> None:
    with pytest.raises(ValueError, match="measured nothing"):
        Measurement(name="m", samples_ns=())


@pytest.mark.trace("REQ-WP-057")
@pytest.mark.parametrize("fraction", [0.0, -0.1, 1.1])
def test_a_fraction_outside_a_run_is_refused(fraction: float) -> None:
    measurement = Measurement(name="m", samples_ns=(1, 2, 3))
    with pytest.raises(ValueError, match="fraction of a run"):
        measurement.percentile_ns(fraction)


@pytest.mark.trace("REQ-WP-057")
def test_the_spread_is_the_slowest_over_the_fastest() -> None:
    """What a threshold has to survive, and the reason a tight one measures the
    runner."""
    assert Measurement(name="m", samples_ns=(10, 20, 30)).spread == 3.0
    assert Measurement(name="m", samples_ns=(10,)).spread == 1.0


# --- headroom ---------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-057")
def test_headroom_is_how_many_times_over_it_could_grow() -> None:
    """Reported rather than only compared: a target met with fifty times to
    spare and one met with one and a half are the same pass."""
    fast = Measurement(name="m", samples_ns=tuple([NS_PER_SECOND // 100] * 20))
    assert headroom(fast, A_TARGET) == pytest.approx(100.0)

    tight = Measurement(name="m", samples_ns=tuple([NS_PER_SECOND // 2] * 20))
    assert headroom(tight, A_TARGET) == pytest.approx(2.0)


@pytest.mark.trace("REQ-WP-057")
def test_headroom_shrinks_as_the_measurement_grows() -> None:
    """Inverted, it would grow -- and a report of "headroom rising" while a
    system slows down is worse than no report."""
    faster = Measurement(name="m", samples_ns=(NS_PER_SECOND // 100,))
    slower = Measurement(name="m", samples_ns=(NS_PER_SECOND // 10,))
    assert headroom(faster, A_TARGET) > headroom(slower, A_TARGET)
    assert headroom(slower, A_TARGET) > 1.0


@pytest.mark.trace("REQ-WP-057")
def test_a_measurement_over_budget_has_headroom_below_one() -> None:
    over = Measurement(name="m", samples_ns=(2 * NS_PER_SECOND,))
    assert headroom(over, A_TARGET) < 1.0


# --- scaling ----------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-057")
def test_scaling_reports_ratios_and_not_durations() -> None:
    """The ratios are the point: two measurements from one run divide the
    machine out, which is what makes this assertable where a duration is not."""
    doubling = [Measurement(name=str(n), samples_ns=(n * 1_000,)) for n in (1, 2, 4, 8)]
    assert scaling_ratio(doubling) == (2.0, 2.0, 2.0)

    #: The same series on a machine ten times slower gives the same ratios.
    slower = [Measurement(name=str(n), samples_ns=(n * 10_000,)) for n in (1, 2, 4, 8)]
    assert scaling_ratio(slower) == scaling_ratio(doubling)


@pytest.mark.trace("REQ-WP-057")
def test_a_quadratic_series_is_distinguishable_from_a_linear_one() -> None:
    linear = [Measurement(name=str(n), samples_ns=(n * 1_000,)) for n in (1, 2, 4)]
    quadratic = [Measurement(name=str(n), samples_ns=(n * n * 1_000,)) for n in (1, 2, 4)]
    assert scaling_ratio(linear) == (2.0, 2.0)
    assert scaling_ratio(quadratic) == (4.0, 4.0)


@pytest.mark.trace("REQ-WP-057")
def test_a_ratio_is_the_later_over_the_earlier() -> None:
    """Divided the other way, a slowdown reads as an improvement."""
    growing = [
        Measurement(name="a", samples_ns=(1_000,)),
        Measurement(name="b", samples_ns=(4_000,)),
    ]
    assert scaling_ratio(growing) == (4.0,)


@pytest.mark.trace("REQ-WP-057")
def test_one_measurement_is_not_a_scaling_series() -> None:
    """There is nothing to compare it against, and returning an empty tuple
    would make a caller's loop assert nothing at all."""
    with pytest.raises(ValueError, match="at least two"):
        scaling_ratio([Measurement(name="m", samples_ns=(1,))])


# --- timing -----------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-057")
def test_timing_keeps_every_run() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1

    measurement = timed(operation, name="m", repeats=5)
    assert calls == 5
    assert len(measurement.samples_ns) == 5
    assert all(sample >= 0 for sample in measurement.samples_ns)


@pytest.mark.trace("REQ-WP-057")
def test_a_run_of_nothing_is_refused() -> None:
    """Zero repeats produces an empty measurement, which would then refuse
    itself three layers down with a less useful message."""
    with pytest.raises(ValueError, match="at least one run"):
        timed(lambda: None, name="m", repeats=0)


# --- the targets themselves ---------------------------------------------------------


@pytest.mark.trace("REQ-WP-057")
def test_the_targets_are_the_ones_section_36_states() -> None:
    """Budgets in the section's own units, so a typo is visible rather than
    generous."""
    budgets = {target.name: target.budget_ns for target in TARGETS}
    assert budgets == {
        "chart_historical_load": 2 * NS_PER_SECOND,
        "signal_after_bar_close": 2 * NS_PER_SECOND,
        "feature_update": NS_PER_SECOND,
    }
    for target in TARGETS:
        assert target.stated, target.name
