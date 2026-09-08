"""Causal turning points (REQ-WP-019, PRD section 13A).

# @trace: REQ-WP-019
"""

from channelflow.extrema.causality import (
    CausalTransform,
    CenteredTransformRejected,
    Transform,
    require_causal,
)
from channelflow.extrema.detector import DirectionalChangeDetector
from channelflow.extrema.models import (
    CandidateInvalidation,
    ConfirmedExtremum,
    ExtremumCandidate,
)
from channelflow.extrema.prominence import ProminenceRule, prominence_bps
from channelflow.extrema.thresholds import ThresholdMode, ThresholdPolicy, ThresholdUnavailable

__all__ = [
    "CandidateInvalidation",
    "CausalTransform",
    "CenteredTransformRejected",
    "ConfirmedExtremum",
    "DirectionalChangeDetector",
    "ExtremumCandidate",
    "ProminenceRule",
    "ThresholdMode",
    "ThresholdPolicy",
    "ThresholdUnavailable",
    "Transform",
    "prominence_bps",
    "require_causal",
]
