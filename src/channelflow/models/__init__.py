"""GMDH and the baselines it must beat (REQ-WP-018, PRD section 23).

# @trace: REQ-WP-018
# @trace: REQ-EXP-008
"""

from channelflow.models.base import (
    BaseRate,
    LogisticRegression,
    Model,
    NotEnoughData,
    SplitOverlap,
    require_disjoint,
)
from channelflow.models.boosting import GradientBoostedTrees, TreeNode
from channelflow.models.gmdh import GMDHNetwork, Node, SearchResult, StopReason
from channelflow.models.metrics import (
    BucketExpectancy,
    Calibration,
    CalibrationBin,
    calibration,
    expectancy_by_bucket,
    feature_stability,
    pr_auc,
)
from channelflow.models.registry import (
    MODEL_REGISTRY_SCHEMA,
    MODEL_REGISTRY_TABLE,
    ModelNotFitted,
    ModelRegistry,
    Registration,
    artifact_hash,
    require_registered,
)
from channelflow.models.regularized import ElasticNetLogistic
from channelflow.models.report import (
    NOT_RUN,
    REQUIRED_BASELINES,
    ComparisonReport,
    Score,
    brier,
    compare,
)

__all__ = [
    "MODEL_REGISTRY_SCHEMA",
    "MODEL_REGISTRY_TABLE",
    "ModelNotFitted",
    "ModelRegistry",
    "Registration",
    "artifact_hash",
    "require_registered",
    "NOT_RUN",
    "REQUIRED_BASELINES",
    "BaseRate",
    "BucketExpectancy",
    "Calibration",
    "CalibrationBin",
    "ElasticNetLogistic",
    "GradientBoostedTrees",
    "Node",
    "TreeNode",
    "ComparisonReport",
    "GMDHNetwork",
    "LogisticRegression",
    "Model",
    "Node",
    "TreeNode",
    "NotEnoughData",
    "Score",
    "SearchResult",
    "SplitOverlap",
    "StopReason",
    "brier",
    "calibration",
    "expectancy_by_bucket",
    "feature_stability",
    "pr_auc",
    "compare",
    "require_disjoint",
]
