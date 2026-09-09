"""Signal scoring, explainability and the alert ranker (PRD sections 22 and 43).

# @trace: REQ-SCORE-001
"""

from channelflow.scoring.explain import (
    POSITIVE_SHARE,
    TOP_N,
    Explanation,
    Factor,
    ScoreRequired,
    explain,
)
from channelflow.scoring.groups import (
    GROUP_CAPS,
    ContributionOutOfRange,
    Group,
    GroupContribution,
)
from channelflow.scoring.ranker import (
    DEFAULT_ALERT_THRESHOLD,
    AlertThresholds,
    FactorOutOfRange,
    Ranked,
    RankInput,
    ResolvedThreshold,
    rank,
    rank_score,
)
from channelflow.scoring.score import TOTAL_CAP, NothingToScore, SignalScore, score_signal

__all__ = [
    "DEFAULT_ALERT_THRESHOLD",
    "GROUP_CAPS",
    "POSITIVE_SHARE",
    "TOP_N",
    "TOTAL_CAP",
    "ContributionOutOfRange",
    "AlertThresholds",
    "Explanation",
    "FactorOutOfRange",
    "Factor",
    "Group",
    "GroupContribution",
    "NothingToScore",
    "RankInput",
    "Ranked",
    "ResolvedThreshold",
    "ScoreRequired",
    "SignalScore",
    "explain",
    "rank",
    "rank_score",
    "score_signal",
]
