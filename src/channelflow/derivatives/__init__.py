"""Derivatives feature engine (REQ-WP-013, PRD section 16).

# @trace: REQ-WP-013
"""

from channelflow.derivatives import registry_entries
from channelflow.derivatives.funding import (
    SettledFunding,
    current_rate,
    funding_acceleration,
    funding_z,
    settled_funding,
)
from channelflow.derivatives.liquidations import (
    LiquidationWindow,
    clusters,
    intensity,
    time_since_spike,
    window,
)
from channelflow.derivatives.openinterest import (
    OpenInterestPoint,
    PriceOIRegime,
    basis_bps,
    mark_premium_bps,
    oi_change,
    oi_series,
    oi_to_volume,
    oi_z,
    price_oi_regime,
)
from channelflow.derivatives.state import (
    DEFAULT_STALENESS_NS,
    AmbiguousState,
    NoStateAvailable,
    StaleState,
    ZScore,
    ZScoreUnavailable,
    ratio,
    require_fresh,
    state_at,
    z_score,
)

FEATURES = registry_entries.FEATURES

__all__ = [
    "FEATURES",
    "AmbiguousState",
    "LiquidationWindow",
    "NoStateAvailable",
    "OpenInterestPoint",
    "PriceOIRegime",
    "SettledFunding",
    "ZScore",
    "ZScoreUnavailable",
    "basis_bps",
    "clusters",
    "current_rate",
    "funding_acceleration",
    "funding_z",
    "intensity",
    "mark_premium_bps",
    "oi_change",
    "oi_series",
    "oi_to_volume",
    "oi_z",
    "price_oi_regime",
    "ratio",
    "settled_funding",
    "DEFAULT_STALENESS_NS",
    "StaleState",
    "require_fresh",
    "state_at",
    "time_since_spike",
    "window",
    "z_score",
]
