"""The fit recovers what was constructed (REQ-WP-006)."""

from __future__ import annotations

import math

import pytest

from channelflow.channels import ChannelFitError, RollingOLSChannel
from tests.unit.channels.conftest import log_linear_series, make_bar


@pytest.mark.trace("REQ-WP-006")
def test_a_constructed_slope_is_recovered() -> None:
    """SC-003. Built from a known log-linear trend, so the answer is knowable
    rather than merely plausible."""
    bars = log_linear_series(120, slope_per_bar=0.002, noise=0.0)
    snapshot = RollingOLSChannel(lookback=100).fit(bars, as_of_ns=bars[-1].close_time_ns)

    # With no noise the centre sits on the constructed line at the last bar.
    assert snapshot.center_now == pytest.approx(float(bars[-1].close), rel=1e-6)


@pytest.mark.trace("REQ-WP-006")
def test_the_same_shape_at_different_price_levels_gives_the_same_slope() -> None:
    """SC-004, and the whole reason ADR-007 normalizes by residual spread.

    A scanner ranking many markets cannot compare a raw log slope between a
    symbol at 78,000 and one at 0.4. Divided by its own noise, the number
    answers the question ranking actually asks.
    """
    cheap = log_linear_series(120, start=0.4, slope_per_bar=0.001, noise=0.004)
    dear = log_linear_series(120, start=78000.0, slope_per_bar=0.001, noise=0.004)
    model = RollingOLSChannel(lookback=100)

    a = model.fit(cheap, as_of_ns=cheap[-1].close_time_ns).slope_normalized
    b = model.fit(dear, as_of_ns=dear[-1].close_time_ns).slope_normalized
    assert a == pytest.approx(b, rel=1e-3)


@pytest.mark.trace("REQ-WP-006")
def test_bands_sit_at_the_configured_residual_quantiles() -> None:
    """FR-003. Changing the levels must move the bands, or they are decorative."""
    bars = log_linear_series(200, noise=0.01)
    wide = RollingOLSChannel(lookback=150, quantile_low=0.01, quantile_high=0.99)
    narrow = RollingOLSChannel(lookback=150, quantile_low=0.25, quantile_high=0.75)
    as_of = bars[-1].close_time_ns

    assert wide.fit(bars, as_of_ns=as_of).width_pct > narrow.fit(bars, as_of_ns=as_of).width_pct


@pytest.mark.trace("REQ-WP-006")
def test_the_centre_is_the_exponential_of_the_fitted_line_not_a_mean() -> None:
    """FR-002. On an exponential trend the two differ, and the mean is wrong."""
    bars = log_linear_series(120, start=100.0, slope_per_bar=0.01, noise=0.0)
    snapshot = RollingOLSChannel(lookback=100).fit(bars, as_of_ns=bars[-1].close_time_ns)

    mean_close = sum(float(b.close) for b in bars[-100:]) / 100
    assert snapshot.center_now == pytest.approx(float(bars[-1].close), rel=1e-6)
    assert abs(snapshot.center_now - mean_close) > 1.0, "a mean would be materially different"


@pytest.mark.trace("REQ-WP-006")
def test_insufficient_history_refuses_and_says_so() -> None:
    """SC-008, FR-010. Fitting on fewer points is silently a different model."""
    bars = log_linear_series(20)
    with pytest.raises(ChannelFitError, match="need 60"):
        RollingOLSChannel(lookback=60).fit(bars, as_of_ns=bars[-1].close_time_ns)


@pytest.mark.trace("REQ-WP-006")
def test_a_non_positive_close_refuses_and_names_the_bar() -> None:
    """SC-008, FR-011. Log price is undefined; guessing is not an option."""
    bars = log_linear_series(40)
    bars[10] = make_bar(index=10, close=0.0)
    with pytest.raises(ChannelFitError, match="non-positive close"):
        RollingOLSChannel(lookback=30).fit(bars, as_of_ns=bars[-1].close_time_ns)


@pytest.mark.trace("REQ-WP-006")
def test_a_flat_series_collapses_the_bands_without_dividing_by_zero() -> None:
    """The degenerate case: every close identical, so residuals vanish."""
    bars = [make_bar(index=i, close=100.0) for i in range(40)]
    snapshot = RollingOLSChannel(lookback=30).fit(bars, as_of_ns=bars[-1].close_time_ns)

    assert snapshot.upper_now == pytest.approx(snapshot.lower_now)
    assert snapshot.slope_normalized == 0.0, "no noise means no slope-to-noise ratio"


@pytest.mark.trace("REQ-WP-006")
def test_two_fits_over_the_same_data_are_identical() -> None:
    """FR-016, SC-001's sibling: otherwise 'the channel changed' and 'we
    recomputed' cannot be told apart."""
    bars = log_linear_series(120, noise=0.005)
    model = RollingOLSChannel(lookback=90)
    as_of = bars[-1].close_time_ns
    assert model.fit(bars, as_of_ns=as_of) == model.fit(bars, as_of_ns=as_of)


@pytest.mark.trace("REQ-WP-006")
def test_input_order_does_not_change_the_fit() -> None:
    """Arrival order is not market information."""
    bars = log_linear_series(120, noise=0.005)
    model = RollingOLSChannel(lookback=90)
    as_of = bars[-1].close_time_ns
    assert model.fit(list(reversed(bars)), as_of_ns=as_of) == model.fit(bars, as_of_ns=as_of)


@pytest.mark.trace("REQ-WP-006")
def test_the_snapshot_carries_its_model_identity() -> None:
    """FR-006. Snapshots from different definitions must stay distinguishable,
    which is what makes ADR-007's choices reversible."""
    bars = log_linear_series(120)
    snapshot = RollingOLSChannel(lookback=90).fit(bars, as_of_ns=bars[-1].close_time_ns)
    assert snapshot.model_name and snapshot.model_version
    assert snapshot.lookback == 90
    assert math.isfinite(snapshot.width_pct)
