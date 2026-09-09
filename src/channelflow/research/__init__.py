"""Research comparisons over point-in-time datasets.

# @trace: REQ-US-006
# @trace: REQ-EXP-001
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

__all__ = [
    "ARMS",
    "MODELS",
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
