"""Turning-point baselines and the GMDH derivative experiment.

# @trace: REQ-WP-019
"""

from channelflow.turning.direct import (
    HORIZON_TARGETS,
    DirectBaselineResult,
    FeatureMissing,
    design_matrix,
    run_direct_baseline,
)
from channelflow.turning.experiment import (
    ExperimentOutcome,
    Verdict,
    run_derivative_experiment,
)
from channelflow.turning.path import (
    CURVATURE_ZERO,
    PathCoefficients,
    RootCandidate,
    TurnType,
    derivative_roots,
    slope_zeros,
)
from channelflow.turning.roots import (
    DEFERRED_CONDITIONS,
    PromotionDecision,
    PromotionGate,
    RootStability,
    assess_root_stability,
)

__all__ = [
    "CURVATURE_ZERO",
    "DEFERRED_CONDITIONS",
    "HORIZON_TARGETS",
    "DirectBaselineResult",
    "ExperimentOutcome",
    "FeatureMissing",
    "PathCoefficients",
    "PromotionDecision",
    "PromotionGate",
    "RootCandidate",
    "RootStability",
    "Verdict",
    "TurnType",
    "assess_root_stability",
    "design_matrix",
    "derivative_roots",
    "run_derivative_experiment",
    "run_direct_baseline",
    "slope_zeros",
]
