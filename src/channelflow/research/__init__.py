"""Research comparisons over point-in-time datasets.

# @trace: REQ-US-006
# @trace: REQ-EXP-001
# @trace: REQ-EXP-002
# @trace: REQ-EXP-003
# @trace: REQ-EXP-004
# @trace: REQ-EXP-005
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
from channelflow.research.ofi_incremental import (
    Increment,
    IncrementalReport,
    available_from_registry,
    run_ofi_ablation,
)
from channelflow.research.volume_confluence import (
    Confluence,
    ConfluenceResult,
    Observation,
    Population,
    PopulationTooSmall,
    Verdict,
    classify,
    confluence_study,
)

__all__ = [
    "ARMS",
    "DETECTORS",
    "Confluence",
    "ConfluenceResult",
    "Increment",
    "Observation",
    "Population",
    "PopulationTooSmall",
    "Verdict",
    "classify",
    "confluence_study",
    "IncrementalReport",
    "available_from_registry",
    "run_ofi_ablation",
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
