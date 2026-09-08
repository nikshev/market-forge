"""PRD section 14.1's shape features.

# @trace: REQ-WP-012
# @trace: REQ-PRIN-008

Entropy, skew, and where price stands relative to the value area. These are the
outputs a signal would actually consume: the profile itself is a picture, and
these are the numbers describing it.
"""

from __future__ import annotations

import math
from decimal import Decimal

from channelflow.features.registry import FeatureSpec, register
from channelflow.volume.profile import VolumeProfile

BPS = 10_000.0

FEATURES: tuple[str, ...] = (
    "profile_entropy",
    "profile_skew",
    "distance_to_poc_bps",
    "distance_to_vah_bps",
    "distance_to_val_bps",
)


def entropy(profile: VolumeProfile) -> float:
    """How spread out the volume is, in nats.

    Zero for a single-bin profile, which is correct rather than degenerate: all
    the volume traded at one price, and there is no uncertainty about where.
    """
    total = profile.total_volume
    if total == 0:
        return 0.0
    result = 0.0
    for current in profile.bins:
        share = float(current.volume / total)
        if share > 0:
            result -= share * math.log(share)
    return result


def skew(profile: VolumeProfile) -> float:
    """Volume above the point of control minus volume below, normalized.

    Positive means more traded above the most-agreed price. Not the statistical
    third moment: this is the asymmetry a reader means when they look at a
    profile, and calling the moment "skew" here would invite comparison with
    numbers computed differently elsewhere.
    """
    total = profile.total_volume
    if total == 0:
        return 0.0
    above = sum((b.volume for b in profile.bins if b.index > profile.poc_index), Decimal(0))
    below = sum((b.volume for b in profile.bins if b.index < profile.poc_index), Decimal(0))
    return float((above - below) / total)


def distance_bps(price: Decimal, target: Decimal) -> float | None:
    """From a price to a level, relative to the price."""
    if price <= 0:
        return None
    return float((target - price) / price) * BPS


def distance_to_poc_bps(profile: VolumeProfile, price: Decimal) -> float | None:
    return distance_bps(price, profile.poc.mid)


def distance_to_vah_bps(profile: VolumeProfile, price: Decimal) -> float | None:
    return distance_bps(price, profile.vah)


def distance_to_val_bps(profile: VolumeProfile, price: Decimal) -> float | None:
    return distance_bps(price, profile.val)


_VOLUME = {
    "family": "volume_structure",
    "source_events": ("trade",),
    "lookback": "the profile window supplied by the caller",
    "cadence": "per profile rebuild",
    "availability_lag_ms": 0,
    "clipping": "none",
    "point_in_time_safe": True,
}


def _register_all() -> None:
    register(
        FeatureSpec(
            name="profile_entropy",
            version=1,
            description="How spread out traded volume is across price bins.",
            formula="-sum(share_i * ln(share_i)) over bins",
            unit="nats",
            null_policy="zero for a single-bin profile, which is a real reading not an absence",
            normalization="none; compare against ln(bin count) for a bounded version",
            test_fixture="tests/unit/volume/test_shape.py::test_entropy_is_lower_when_volume_is_concentrated",
            **_VOLUME,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="profile_skew",
            version=1,
            description="Volume above the point of control minus volume below, normalized.",
            formula="(volume above POC - volume below POC) / total volume",
            unit="normalized",
            null_policy="zero for an empty or perfectly symmetric profile",
            normalization="divided by total volume, so comparable across sessions",
            test_fixture="tests/unit/volume/test_shape.py::test_skew_is_positive_with_more_volume_above",
            **_VOLUME,  # type: ignore[arg-type]
        )
    )
    for name, target in (
        ("distance_to_poc_bps", "the point of control's mid price"),
        ("distance_to_vah_bps", "the value area high"),
        ("distance_to_val_bps", "the value area low"),
    ):
        register(
            FeatureSpec(
                name=name,
                version=1,
                description=f"Distance from the current price to {target}.",
                formula="(target - price) / price * 10_000",
                unit="basis points",
                null_policy="absent when the price is not positive",
                normalization="relative to price, so comparable across symbols",
                test_fixture="tests/unit/volume/test_shape.py::test_distances_are_in_basis_points",
                **_VOLUME,  # type: ignore[arg-type]
            )
        )


_register_all()
