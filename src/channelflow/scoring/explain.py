"""PRD section 22.4's explainability.

# @trace: REQ-SCORE-001

    "Every signal stores:
     - top positive factors;
     - top negative factors;
     - missing factors;
     - raw feature snapshot;
     - model/version used."

PRD section 0 item 10 is the reason: "be able to explain why a signal received
its score". Four of the five items without the fifth is a panel that cannot.

A factor's strength is its share of its own group's cap, never its raw value.
26 of 30 and 8 of 10 are both strong; 4 of 20 is weak while being a larger
number than 1 of 10, which is weaker still -- so ranking by raw contribution
would present the weakest group as the second-best one.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.scoring.groups import Group, GroupContribution
from channelflow.scoring.score import SignalScore

#: How many factors each list carries. Section 22.4 says "top", not "all".
TOP_N = 3

#: A group filling at least this share of its cap is a positive factor, below it
#: a negative one. Half is the neutral point of a `0..cap` range, and this is a
#: presentation boundary rather than a market threshold -- it changes which list
#: a factor appears in, never the score.
POSITIVE_SHARE = 0.5


class ScoreRequired(ValueError):
    """An explanation was requested for a score that was never computed."""


@dataclass(frozen=True)
class Factor:
    """One group's contribution, as a share of what it could have contributed."""

    group: Group
    value: float
    cap: float
    share: float
    names: tuple[str, ...]

    @classmethod
    def of(cls, contribution: GroupContribution) -> Factor:
        return cls(
            group=contribution.group,
            value=contribution.value,
            cap=contribution.cap,
            share=contribution.value / contribution.cap,
            names=contribution.factors,
        )


@dataclass(frozen=True)
class Explanation:
    """Section 22.4's five items, and nothing else."""

    top_positive: tuple[Factor, ...]
    top_negative: tuple[Factor, ...]
    missing: tuple[Group, ...]
    feature_snapshot: dict[str, float]
    model_version: str
    factors: tuple[Factor, ...]


def explain(
    score: SignalScore | None, *, feature_snapshot: dict[str, float], model_version: str
) -> Explanation:
    """Section 22.4's record, for a score that exists.

    A missing family never appears among the negative factors. "We have no DeFi
    data" and "the DeFi evidence is against this setup" are different
    statements, and section 22.4 gives them separate lists for exactly that
    reason.
    """
    if score is None:
        raise ScoreRequired(
            "an explanation needs a computed score; one built without it would read "
            "like a real explanation and account for a number nobody computed"
        )
    if not model_version:
        raise ValueError(
            "a model version is required (section 22.4): an explanation whose version "
            "is unknown cannot be compared against a later model's"
        )

    factors = tuple(Factor.of(c) for c in score.contributions)
    # Sorted by share, then by group name -- so two groups filling the same
    # share of their caps order the same way whichever order they arrived in.
    ordered = sorted(factors, key=lambda f: (-f.share, f.group.value))
    return Explanation(
        top_positive=tuple(f for f in ordered if f.share >= POSITIVE_SHARE)[:TOP_N],
        top_negative=tuple(reversed([f for f in ordered if f.share < POSITIVE_SHARE]))[:TOP_N],
        missing=score.missing,
        feature_snapshot=dict(feature_snapshot),
        model_version=model_version,
        factors=factors,
    )
