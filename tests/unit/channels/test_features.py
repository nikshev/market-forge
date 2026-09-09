"""The channel's numbers as registered features (REQ-PRIN-008, PRD section 19)."""

from __future__ import annotations

import pytest

from channelflow.channels import (
    ChannelQuality,
    ChannelSnapshot,
    channel_position,
    channel_quality_score,
    channel_slope_normalized,
    channel_width_pct,
)
from channelflow.features import REGISTRY, exposed_feature_names


def snapshot(*, center: float = 100.0, half_width: float = 5.0) -> ChannelSnapshot:
    return ChannelSnapshot(
        as_of_ns=0,
        model_name="test",
        model_version="1.0.0",
        lookback=60,
        center_now=center,
        upper_now=center + half_width,
        lower_now=center - half_width,
        slope_normalized=-1.5,
        width_pct=(2 * half_width) / center * 100.0,
        quality=ChannelQuality(score=0.8, submetrics={}, contributing=(), unavailable=()),
        source_max_event_time_ns=0,
    )


@pytest.mark.trace("REQ-PRIN-008")
def test_the_channel_features_are_registered() -> None:
    """PRD §19, and ADR-015's gate.

    These four have been consumed as features since before there was a registry
    -- the score's channel group is exactly them -- while living only as fields
    on a snapshot. An unregistered feature is one nobody can look up the meaning
    of.
    """
    for name in (
        "channel_slope_normalized",
        "channel_width_pct",
        "channel_quality_score",
        "channel_position",
    ):
        assert name in REGISTRY, name
        assert name in exposed_feature_names()
        assert REGISTRY[name].family == "channel"


@pytest.mark.trace("REQ-PRIN-008")
def test_the_features_read_the_snapshot_rather_than_recomputing_it() -> None:
    """The arithmetic belongs to whichever baseline produced the snapshot.

    A second implementation here would be a second definition, and the registry
    would document neither.
    """
    fitted = snapshot()

    assert channel_slope_normalized(fitted) == pytest.approx(-1.5)
    assert channel_quality_score(fitted) == pytest.approx(0.8)


@pytest.mark.trace("REQ-PRIN-008")
def test_the_width_is_a_percentage_of_the_centre() -> None:
    """A width in price units means nothing across symbols; ten dollars is wide
    on a coin at forty and invisible on one at seventy thousand."""
    assert channel_width_pct(snapshot(center=100.0, half_width=5.0)) == pytest.approx(10.0)


@pytest.mark.trace("REQ-PRIN-008")
def test_the_position_is_zero_at_the_lower_boundary() -> None:
    """PRD §13.10's coordinate, which the signal engine reads as a zone."""
    fitted = snapshot(center=100.0, half_width=5.0)

    assert channel_position(fitted, 95.0) == pytest.approx(0.0)
    assert channel_position(fitted, 105.0) == pytest.approx(1.0)
    assert channel_position(fitted, 100.0) == pytest.approx(0.5)


@pytest.mark.trace("REQ-PRIN-008")
def test_a_channel_with_no_width_has_no_position() -> None:
    """Every position on it would be infinite, and the engine reads this number
    as a zone."""
    flat = snapshot(center=100.0, half_width=0.0)

    assert channel_position(flat, 100.0) is None
