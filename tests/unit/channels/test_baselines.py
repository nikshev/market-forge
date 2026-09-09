"""Channel baselines B, C and D (REQ-CHAN-001, PRD sections 13.3 to 13.5)."""

from __future__ import annotations

import math
from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.bars import Bar
from channelflow.channels import (
    ChannelFitError,
    HuberChannel,
    KalmanChannel,
    QuantileChannel,
    RollingOLSChannel,
)

from .conftest import BASE_NS, MINUTE_NS, log_linear_series, make_bar


def with_wick(bars: list[Bar], *, at: int, factor: float) -> list[Bar]:
    """One bar's close multiplied -- a liquidation wick, in PRD §13.3's words."""
    changed = list(bars)
    spiked = changed[at]
    changed[at] = spiked.model_copy(
        update={"close": Decimal(str(round(float(spiked.close) * factor, 8)))}
    )
    return changed


@pytest.mark.trace("REQ-CHAN-001")
@pytest.mark.parametrize(
    "fitter",
    [HuberChannel(lookback=60), QuantileChannel(lookback=60), KalmanChannel(lookback=60)],
)
def test_every_baseline_names_itself(fitter: object) -> None:
    """SC-001, FR-001.

    A snapshot that named baseline A would make a model comparison compare one
    model with itself, and the report would look entirely reasonable.
    """
    bars = log_linear_series(80, noise=0.004)

    snapshot = fitter.fit(bars, as_of_ns=bars[-1].close_time_ns)  # type: ignore[attr-defined]

    assert snapshot.model_name != "rolling_ols_log_price"
    assert snapshot.model_version


@pytest.mark.trace("REQ-CHAN-001")
@pytest.mark.parametrize(
    "fitter",
    [HuberChannel(lookback=60), QuantileChannel(lookback=60), KalmanChannel(lookback=60)],
)
def test_every_baseline_refuses_a_short_window(fitter: object) -> None:
    """SC-002, FR-003.

    Baseline A's rule: a channel fitted on fewer points than asked for is a
    different model wearing the same name.
    """
    with pytest.raises(ChannelFitError):
        fitter.fit(log_linear_series(20), as_of_ns=BASE_NS + 100 * MINUTE_NS)  # type: ignore[attr-defined]


@pytest.mark.trace("REQ-CHAN-001")
@pytest.mark.parametrize(
    "fitter",
    [HuberChannel(lookback=60), QuantileChannel(lookback=60), KalmanChannel(lookback=60)],
)
def test_every_baseline_ignores_bars_after_the_instant(fitter: object) -> None:
    """FR-002.

    The guard baseline A refuses to leave to its caller: a channel fitted with
    hindsight looks superb, which is exactly why the filtering is the fitter's
    own job.
    """
    bars = log_linear_series(80, noise=0.004)
    at_ns = bars[69].close_time_ns

    early = fitter.fit(bars[:70], as_of_ns=at_ns)  # type: ignore[attr-defined]
    with_future = fitter.fit(bars, as_of_ns=at_ns)  # type: ignore[attr-defined]

    assert early.center_now == pytest.approx(with_future.center_now)
    assert early.source_max_event_time_ns == with_future.source_max_event_time_ns


@pytest.mark.trace("REQ-CHAN-001")
def test_the_robust_centre_ignores_a_wick_the_least_squares_centre_chases() -> None:
    """SC-003, FR-004, FR-005.

    PRD §13.3's goal in one line: "reduce sensitivity to liquidation
    wicks/outliers". A least-squares centre chases the wick, and the zones the
    signal engine reads move with it.
    """
    clean = log_linear_series(80, noise=0.002)
    spiked = with_wick(clean, at=70, factor=1.30)
    at_ns = clean[-1].close_time_ns

    ols_shift = abs(
        RollingOLSChannel(lookback=60).fit(spiked, as_of_ns=at_ns).center_now
        - RollingOLSChannel(lookback=60).fit(clean, as_of_ns=at_ns).center_now
    )
    huber_shift = abs(
        HuberChannel(lookback=60).fit(spiked, as_of_ns=at_ns).center_now
        - HuberChannel(lookback=60).fit(clean, as_of_ns=at_ns).center_now
    )

    assert huber_shift < ols_shift / 2.0, (
        f"the robust centre moved {huber_shift:.4f} against least squares' {ols_shift:.4f}; "
        "a robust fit that tracks the outlier is not one"
    )


@pytest.mark.trace("REQ-CHAN-001")
def test_the_unbuilt_estimators_are_named_in_the_module() -> None:
    """FR-006.

    §13.3 lists three candidates and this builds one. A module silent about the
    other two reads as the section, implemented.
    """
    source = (
        Path(__file__).resolve().parents[3] / "src" / "channelflow" / "channels" / "huber.py"
    ).read_text()

    assert "Theil-Sen" in source
    assert "RANSAC" in source


@pytest.mark.trace("REQ-CHAN-001")
def test_the_quantile_channel_can_be_asymmetric() -> None:
    """SC-004, FR-007.

    §13.4's stated purpose. Baseline A places both bands as residual quantiles
    around one centre, so the two sides move together whatever the market does.
    """
    # Downward spikes only: the lower dispersion is much larger than the upper.
    bars = list(log_linear_series(80, noise=0.001))
    for index in range(10, 80, 7):
        bars[index] = bars[index].model_copy(
            update={"close": Decimal(str(round(float(bars[index].close) * 0.94, 8)))}
        )

    snapshot = QuantileChannel(lookback=60).fit(bars, as_of_ns=bars[-1].close_time_ns)

    above = snapshot.upper_now - snapshot.center_now
    below = snapshot.center_now - snapshot.lower_now
    assert above != pytest.approx(below, rel=0.05), (
        "the channel is symmetric on asymmetric data, which is baseline A's behaviour"
    )


@pytest.mark.trace("REQ-CHAN-001")
def test_crossed_quantiles_come_back_ordered() -> None:
    """SC-005, FR-008.

    §13.4 requires "quantile crossing correction" by name. Uncorrected, the
    upper band sits below the lower one and every position computed on the
    channel is negative -- a number the signal engine would read as a zone.
    """
    bars = log_linear_series(80, noise=0.0)

    snapshot = QuantileChannel(lookback=60).fit(bars, as_of_ns=bars[-1].close_time_ns)

    assert snapshot.lower_now <= snapshot.center_now <= snapshot.upper_now


@pytest.mark.trace("REQ-CHAN-001")
def test_a_flat_series_still_has_the_minimum_width() -> None:
    """SC-006, FR-009.

    §13.4's second required check. A channel of zero width makes every
    normalized position infinite, and PRD §13.10's coordinate is what the signal
    engine reads.
    """
    bars = [make_bar(index=i, close=100.0) for i in range(80)]

    # The natural width of a flat series is zero, so the floor is the only
    # thing producing a channel at all -- which is what makes this a test of it.
    snapshot = QuantileChannel(lookback=60, minimum_width_pct=3.0).fit(
        bars, as_of_ns=bars[-1].close_time_ns
    )

    assert snapshot.width_pct == pytest.approx(3.0, rel=0.01)
    assert snapshot.upper_now > snapshot.lower_now


@pytest.mark.trace("REQ-CHAN-001")
def test_slope_disagreement_between_the_quantiles_is_reported() -> None:
    """SC-007, FR-010.

    §13.4's third required check. Three quantiles fitted independently can
    disagree about the trend, and a channel whose boundaries diverge is a
    channel that will not hold -- visible in the quality submetrics rather than
    discovered later.
    """
    bars = log_linear_series(80, noise=0.003)

    snapshot = QuantileChannel(lookback=60).fit(bars, as_of_ns=bars[-1].close_time_ns)

    assert "slope_consistency" in snapshot.quality.submetrics


@pytest.mark.trace("REQ-CHAN-001")
def test_a_kalman_state_never_changes_when_later_bars_arrive() -> None:
    """SC-008, FR-012.

    §13.5: "use recursive filtering only". A smoother's state at bar 50 changes
    when bar 51 arrives, and every feature derived from it repaints.
    """
    bars = log_linear_series(120, noise=0.003)
    at_ns = bars[69].close_time_ns

    early = KalmanChannel(lookback=60).fit(bars[:70], as_of_ns=at_ns)
    later = KalmanChannel(lookback=60).fit(bars, as_of_ns=at_ns)

    assert early.center_now == pytest.approx(later.center_now)
    assert early.slope_normalized == pytest.approx(later.slope_normalized)


@pytest.mark.trace("REQ-CHAN-001")
def test_the_kalman_module_contains_no_backward_pass() -> None:
    """SC-009, FR-013.

    §13.5 forbids the smoother in one sentence, and a smoother is what a Kalman
    implementation invites -- it is the better estimator, and it reads the
    future. Checked over the source, because "we only used the filter" is a
    claim a comment can make and a structure can carry.
    """
    source = (
        Path(__file__).resolve().parents[3] / "src" / "channelflow" / "channels" / "kalman.py"
    ).read_text()

    # Code, not prose. The module's docstring explains the prohibition at
    # length and names the smoother it refuses to be; a check that failed on
    # that would be satisfied by deleting the explanation.
    code = [
        line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")
    ]
    body = "\n".join(code)

    for forbidden in ("[::-1]", "reversed(", "def _smooth", ".smooth(", "rts_"):
        assert forbidden not in body, f"kalman.py contains {forbidden!r}: a backward pass"


@pytest.mark.trace("REQ-CHAN-001")
def test_the_kalman_channel_reports_its_state_uncertainty() -> None:
    """FR-014.

    §13.5 lists it among the outputs. A filtered level without its uncertainty
    is a point estimate presented as a fact.
    """
    bars = log_linear_series(80, noise=0.003)

    snapshot = KalmanChannel(lookback=60).fit(bars, as_of_ns=bars[-1].close_time_ns)

    assert "state_uncertainty" in snapshot.quality.submetrics


@pytest.mark.trace("REQ-CHAN-001")
def test_the_kalman_band_widens_with_the_innovations() -> None:
    """SC-010, FR-014.

    §13.5's "adaptive band based on innovation variance". A band that ignores
    them is a fixed band with extra arithmetic.
    """
    calm = log_linear_series(80, noise=0.001)
    choppy = log_linear_series(80, noise=0.02)
    at_ns = calm[-1].close_time_ns

    narrow = KalmanChannel(lookback=60).fit(calm, as_of_ns=at_ns)
    wide = KalmanChannel(lookback=60).fit(choppy, as_of_ns=at_ns)

    # By a margin, not by any amount. A band derived from a constant instead of
    # from the innovations still came out a few floating-point bits wider on the
    # choppy series, and a bare `>` accepted that as evidence.
    assert wide.width_pct > narrow.width_pct * 1.5


@pytest.mark.trace("REQ-CHAN-001")
def test_no_baseline_consults_a_clock() -> None:
    """SC-011, FR-015."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "channels"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"


@pytest.mark.trace("REQ-CHAN-001")
def test_the_robust_band_does_not_blow_out_on_one_wick() -> None:
    """SC-003, FR-004.

    The "+ MAD" half of REQ-EXP-001's "Huber + MAD". A robust centre with a
    standard-deviation band is half a robust channel: the centre holds and the
    boundaries jump, so the zones the signal engine reads move anyway.
    """
    clean = log_linear_series(80, noise=0.002)
    spiked = with_wick(clean, at=70, factor=1.30)
    at_ns = clean[-1].close_time_ns

    huber_clean = HuberChannel(lookback=60).fit(clean, as_of_ns=at_ns).width_pct
    huber_spiked = HuberChannel(lookback=60).fit(spiked, as_of_ns=at_ns).width_pct
    ols_clean = RollingOLSChannel(lookback=60).fit(clean, as_of_ns=at_ns).width_pct
    ols_spiked = RollingOLSChannel(lookback=60).fit(spiked, as_of_ns=at_ns).width_pct

    assert ols_spiked > ols_clean * 2.0, "the fixture must move baseline A's band"
    assert huber_spiked < huber_clean * 1.2


@pytest.mark.trace("REQ-CHAN-001")
def test_the_kalman_filter_tracks_the_series_it_is_given() -> None:
    """FR-012.

    A filter that ignores its observations still satisfies every invariance
    test -- it returns the same thing whatever arrives, which is exactly what
    "no later bar changes an earlier state" asks for. This is the test that
    says it followed the data.
    """
    rising = log_linear_series(80, slope_per_bar=0.002, noise=0.001)
    falling = log_linear_series(80, slope_per_bar=-0.002, noise=0.001)

    up = KalmanChannel(lookback=60).fit(rising, as_of_ns=rising[-1].close_time_ns)
    down = KalmanChannel(lookback=60).fit(falling, as_of_ns=falling[-1].close_time_ns)

    assert up.center_now == pytest.approx(float(rising[-1].close), rel=0.01)
    assert down.center_now == pytest.approx(float(falling[-1].close), rel=0.01)
    assert up.slope_normalized > 0.0
    assert down.slope_normalized < 0.0


@pytest.mark.trace("REQ-CHAN-001")
def test_a_tied_quantile_fit_is_resolved_by_a_stated_rule() -> None:
    """FR-011.

    Several candidate lines through `y = [-2, -1, -1, -1]` reach the same
    pinball loss at the median, and the first one the enumeration reaches is not
    the one the stated rule picks -- so this distinguishes a declared tie-break
    from whichever pair happened to come out of the loop first. A channel that
    is a function of a loop's index order is not a market fact.
    """
    import numpy as np

    from channelflow.channels.quantile import _pinball_fit

    x = np.arange(4.0)
    y = np.array([-2.0, -1.0, -1.0, -1.0])

    intercept, slope = _pinball_fit(x, y, tau=0.5)

    # Lowest loss, then lowest slope, then lowest intercept. Enumeration order
    # would give slope 0.5 through the first pair; the rule gives the flat line.
    assert slope == pytest.approx(0.0)
    assert intercept == pytest.approx(-1.0)


@pytest.mark.trace("REQ-CHAN-001")
def test_quantile_lines_that_cross_are_reordered() -> None:
    """SC-005, FR-008.

    A closing funnel: the dispersion narrows to nothing part-way through the
    window and then opens the other way, so the fitted q10 line rises while the
    q90 line falls and the two cross before the window ends. Uncorrected, the
    upper band sits below the lower one and PRD §13.10's normalized position --
    the number the signal engine reads as a zone -- comes out negative.
    """
    bars = []
    for i in range(80):
        # The amplitude passes through zero at bar 40 and goes negative, which
        # swaps the envelopes and makes the two fitted lines cross.
        amplitude = 0.05 * (1.0 - i / 40.0)
        offset = amplitude if i % 2 == 0 else -amplitude
        bars.append(make_bar(index=i, close=100.0 * math.exp(offset)))

    snapshot = QuantileChannel(lookback=60).fit(bars, as_of_ns=bars[-1].close_time_ns)

    assert snapshot.lower_now <= snapshot.center_now <= snapshot.upper_now
