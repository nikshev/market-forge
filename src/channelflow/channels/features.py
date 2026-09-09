"""The channel's own numbers, as registered features.

# @trace: REQ-PRIN-008
# @trace: REQ-EXP-004

PRD section 19: "Every feature definition must be registered", with sixteen
required fields. Constitution Principle VI: "An undocumented feature is not
done."

These four have been consumed as features since before there was a registry --
REQ-SCORE-001's `channel_structure` group scores them, REQ-US-004's panel shows
them, and every ablation with a channel arm is an ablation over them -- while
living only as fields on a `ChannelSnapshot`. Registering them closes that gap
and gives the ablations a channel baseline made of declared features rather than
of whatever the caller happened to pass.

Read from a snapshot rather than computed here. The arithmetic belongs to
whichever baseline produced it (REQ-WP-006, REQ-CHAN-001), and a second
implementation would be a second definition.
"""

from __future__ import annotations

from channelflow.channels.models import ChannelSnapshot
from channelflow.features.registry import FeatureSpec, register

FEATURES: tuple[str, ...] = (
    "channel_slope_normalized",
    "channel_width_pct",
    "channel_quality_score",
    "channel_position",
)

_CHANNEL = {
    "family": "channel",
    "source_events": ("bar",),
    "lookback": "the fitting model's own lookback",
    "cadence": "per finalized bar",
    "availability_lag_ms": 0,
    "clipping": "none",
    "point_in_time_safe": True,
}


def channel_slope_normalized(snapshot: ChannelSnapshot) -> float:
    return snapshot.slope_normalized


def channel_width_pct(snapshot: ChannelSnapshot) -> float:
    return snapshot.width_pct


def channel_quality_score(snapshot: ChannelSnapshot) -> float:
    return snapshot.quality.score


def channel_position(snapshot: ChannelSnapshot, price: float) -> float | None:
    """PRD section 13.10's normalized coordinate: 0 at the lower boundary, 1 at the upper.

    `None` for a channel with no width. Every position on it would be infinite,
    and the signal engine reads this number as a zone.
    """
    span = snapshot.upper_now - snapshot.lower_now
    if span <= 0:
        return None
    return (price - snapshot.lower_now) / span


def _register_all() -> None:
    register(
        FeatureSpec(
            name="channel_slope_normalized",
            version=1,
            description="The channel's slope in units of its own residual noise.",
            formula="slope / residual_std, or 0 when the residual spread is negligible",
            unit="noise units per bar",
            null_policy="zero when the residual spread is below the negligible threshold",
            normalization="by residual standard deviation, so it compares across symbols",
            test_fixture="tests/unit/channels/test_fit.py::test_the_same_shape_at_different_price_levels_gives_the_same_slope",
            **_CHANNEL,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="channel_width_pct",
            version=1,
            description="The distance between the boundaries, as a percentage of the centre.",
            formula="(upper_now - lower_now) / center_now * 100",
            unit="percent",
            null_policy="zero when the centre is not positive",
            normalization="relative to the centre, so it compares across symbols",
            test_fixture="tests/unit/channels/test_features.py::test_the_width_is_a_percentage_of_the_centre",
            **_CHANNEL,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="channel_quality_score",
            version=1,
            description="PRD section 13.9's weighted channel quality.",
            formula="weighted mean of the computable submetrics",
            unit="score in [0, 1]",
            null_policy="never absent; the submetrics that could not be computed are named",
            normalization="bounded to [0, 1] by construction",
            test_fixture="tests/unit/channels/test_quality.py::test_the_score_names_what_produced_it",
            **_CHANNEL,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="channel_position",
            version=1,
            description="PRD section 13.10's normalized position of price within the channel.",
            formula="(price - lower_now) / (upper_now - lower_now)",
            unit="fraction of channel width",
            null_policy="absent for a channel with no width, where every position is infinite",
            normalization="0 at the lower boundary, 1 at the upper",
            test_fixture="tests/unit/channels/test_features.py::test_the_position_is_zero_at_the_lower_boundary",
            **_CHANNEL,  # type: ignore[arg-type]
        )
    )


_register_all()
