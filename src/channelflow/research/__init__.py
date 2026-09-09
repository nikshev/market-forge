"""Research comparisons over point-in-time datasets.

# @trace: REQ-US-006
# @trace: REQ-EXP-001
# @trace: REQ-EXP-002
# @trace: REQ-EXP-003
"""

from channelflow.research.ablation import (
    ARMS,
    FAMILIES,
    AblationArm,
    AblationReport,
    ArmEntry,
    UnknownFamily,
    rank_arms,
    run_ablation,
)
from channelflow.research.channel_comparison import (
    MODELS,
    ChannelComparisonReport,
    ModelEntry,
    SeriesTooShort,
    compare_channel_models,
)
from channelflow.research.detector_comparison import (
    DETECTORS,
    UNAVAILABLE,
    CandidateLife,
    DetectorComparisonReport,
    DetectorEntry,
    candidate_lives,
    compare_detectors,
    detector_metrics,
)
from channelflow.research.lookback_sensitivity import (
    LOOKBACKS,
    Plateau,
    Recommendation,
    SweepEntry,
    SweepReport,
    find_plateau,
    recommend,
    sweep_lookbacks,
)

__all__ = [
    "ARMS",
    "DETECTORS",
    "CandidateLife",
    "candidate_lives",
    "detector_metrics",
    "UNAVAILABLE",
    "DetectorComparisonReport",
    "DetectorEntry",
    "LOOKBACKS",
    "compare_detectors",
    "MODELS",
    "Plateau",
    "Recommendation",
    "SweepEntry",
    "SweepReport",
    "find_plateau",
    "recommend",
    "sweep_lookbacks",
    "ChannelComparisonReport",
    "ModelEntry",
    "SeriesTooShort",
    "compare_channel_models",
    "FAMILIES",
    "AblationArm",
    "AblationReport",
    "ArmEntry",
    "UnknownFamily",
    "rank_arms",
    "run_ablation",
]
