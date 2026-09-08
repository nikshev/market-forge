"""Adaptive stop management (REQ-WP-020, PRD section 44A).

# @trace: REQ-WP-020
"""

from channelflow.stops.models import (
    AnchorKind,
    PositionPhase,
    PositionState,
    ReasonCode,
    Side,
    StopAnchor,
    StopPolicyOutcome,
    StopProposal,
)
from channelflow.stops.policy import StopPolicy, swing_anchors
from channelflow.stops.replay import (
    ComparisonReport,
    CostModel,
    NaiveATRTrailing,
    NaiveFixedPercent,
    PricePoint,
    Replay,
)

__all__ = [
    "AnchorKind",
    "ComparisonReport",
    "CostModel",
    "NaiveATRTrailing",
    "NaiveFixedPercent",
    "PositionPhase",
    "PositionState",
    "PricePoint",
    "ReasonCode",
    "Replay",
    "Side",
    "StopAnchor",
    "StopPolicy",
    "StopPolicyOutcome",
    "StopProposal",
    "swing_anchors",
]
