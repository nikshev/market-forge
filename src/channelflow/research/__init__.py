"""Research comparisons over point-in-time datasets.

# @trace: REQ-US-006
# @trace: REQ-EXP-001
# @trace: REQ-EXP-002
# @trace: REQ-EXP-003
# @trace: REQ-EXP-004
# @trace: REQ-EXP-005
# @trace: REQ-EXP-006
# @trace: REQ-EXP-007
# @trace: REQ-EXP-009
# @trace: REQ-EXP-010
# @trace: REQ-EXP-011
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
from channelflow.research.corridor_calibration import (
    SUPPORTED_COVERAGE,
    CalibrationReport,
    Measurement,
    Method,
    MethodResult,
    NoStableCorridor,
    compare_corridors,
    measure_corridors,
    pick_winner,
)
from channelflow.research.cumulative import (
    Increment,
    IncrementalReport,
    increments_of,
    resolve_membership,
    run_cumulative_ablation,
)
from channelflow.research.derivatives_context import (
    VARIABLES,
    Bucket,
    ConditionalReport,
    VariableConditional,
    conditional_study,
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
from channelflow.research.dex_incremental import (
    DexIncrementalReport,
    run_dex_ablation,
)
from channelflow.research.extremum_detectors import (
    METHODS,
    DetectorComparison,
    RegimeRate,
    volatility_regime,
)
from channelflow.research.extremum_detectors import (
    compare_detectors as compare_extremum_detectors,
)
from channelflow.research.lead_lag_value import (
    DEFAULT_THRESHOLDS,
    DivergenceSignal,
    LeadLagResult,
    evaluate_divergence,
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
    "DEFAULT_THRESHOLDS",
    "METHODS",
    "DetectorComparison",
    "RegimeRate",
    "compare_extremum_detectors",
    "volatility_regime",
    "SUPPORTED_COVERAGE",
    "DivergenceSignal",
    "LeadLagResult",
    "evaluate_divergence",
    "VARIABLES",
    "CalibrationReport",
    "Method",
    "Measurement",
    "MethodResult",
    "NoStableCorridor",
    "compare_corridors",
    "measure_corridors",
    "pick_winner",
    "Bucket",
    "ConditionalReport",
    "DexIncrementalReport",
    "Confluence",
    "VariableConditional",
    "conditional_study",
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
    "increments_of",
    "resolve_membership",
    "run_cumulative_ablation",
    "run_dex_ablation",
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
