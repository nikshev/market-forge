"""Channel quality (REQ-WP-006, PRD section 13.9, ADR-007)."""

from __future__ import annotations

import math

import pytest

from channelflow.channels import RollingOLSChannel
from channelflow.channels.quality import UNAVAILABLE
from tests.unit.channels.conftest import log_linear_series, make_bar


@pytest.mark.trace("REQ-WP-006")
def test_coverage_is_near_the_configured_band_width() -> None:
    """SC-005. Bands at the 10th and 90th percentile should contain about 80%
    of closes -- by construction, since they are quantiles of those residuals."""
    bars = log_linear_series(200, noise=0.01)
    snapshot = RollingOLSChannel(lookback=150).fit(bars, as_of_ns=bars[-1].close_time_ns)
    assert snapshot.quality.submetrics["coverage_score"] > 0.9


@pytest.mark.trace("REQ-WP-006")
def test_a_clean_trend_outscores_noise() -> None:
    """SC-006. The score has to distinguish a channel from a line through
    randomness, or PRD section 1.2's conditional hypothesis has nothing to
    condition on."""
    trend = log_linear_series(200, slope_per_bar=0.002, noise=0.002)

    # Deterministic pseudo-noise: a channel test that reseeds cannot tell a
    # regression from a different draw.
    noisy = [
        make_bar(index=i, close=100.0 * math.exp(0.06 * math.sin(i * 2.399) * math.cos(i * 5.7)))
        for i in range(200)
    ]

    model = RollingOLSChannel(lookback=150)
    trend_score = model.fit(trend, as_of_ns=trend[-1].close_time_ns).quality.score
    noise_score = model.fit(noisy, as_of_ns=noisy[-1].close_time_ns).quality.score

    assert trend_score > noise_score, (
        f"trend {trend_score:.3f} did not beat noise {noise_score:.3f}"
    )


@pytest.mark.trace("REQ-WP-006")
def test_the_score_names_what_produced_it() -> None:
    """SC-007, FR-013. A number in [0,1] assembled from unnamed parts is one
    nobody can argue with."""
    bars = log_linear_series(200, noise=0.01)
    quality = RollingOLSChannel(lookback=150).fit(bars, as_of_ns=bars[-1].close_time_ns).quality

    assert len(quality.contributing) == 6
    assert set(quality.contributing) == set(quality.submetrics)
    assert quality.unavailable == UNAVAILABLE


@pytest.mark.trace("REQ-WP-006")
def test_unavailable_submetrics_are_omitted_not_defaulted() -> None:
    """SC-007, FR-014, ADR-007. A neutral default would drag every score toward
    the middle for a reason no reader could see, and would make this six-part
    score silently comparable with a later nine-part one."""
    bars = log_linear_series(200, noise=0.01)
    quality = RollingOLSChannel(lookback=150).fit(bars, as_of_ns=bars[-1].close_time_ns).quality

    for name in UNAVAILABLE:
        assert name not in quality.submetrics, f"{name} cannot be computed and must not appear"
        assert name not in quality.contributing

    computed = [quality.submetrics[k] for k in quality.contributing]
    assert quality.score == pytest.approx(sum(computed) / len(computed), rel=1e-9), (
        "with equal weights the score is the mean of exactly the contributors"
    )


@pytest.mark.trace("REQ-WP-006")
def test_weights_are_configurable() -> None:
    """FR-012, PRD section 0.12. The weights are a starting point, so changing
    them must actually change the score."""
    bars = log_linear_series(200, noise=0.01)
    as_of = bars[-1].close_time_ns

    default = RollingOLSChannel(lookback=150).fit(bars, as_of_ns=as_of).quality.score
    coverage_only = (
        RollingOLSChannel(lookback=150, weights={"coverage_score": 1.0})
        .fit(bars, as_of_ns=as_of)
        .quality
    )

    assert coverage_only.contributing == ("coverage_score",)
    assert coverage_only.score != pytest.approx(default)


@pytest.mark.trace("REQ-WP-006")
def test_the_score_stays_in_range() -> None:
    """A score outside [0,1] would be uninterpretable, and every consumer would
    have to clamp it themselves."""
    for noise in (0.0, 0.001, 0.05, 0.2):
        bars = log_linear_series(200, noise=noise)
        score = (
            RollingOLSChannel(lookback=150).fit(bars, as_of_ns=bars[-1].close_time_ns).quality.score
        )
        assert 0.0 <= score <= 1.0
