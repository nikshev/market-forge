"""PRD section 22's deterministic score v1.

# @trace: REQ-SCORE-001

Section 22.2's worked example is the specification of the arithmetic:

    Channel structure        26/30
    Rejection                17/20
    Order flow               16/20
    Volume                     7/10
    Derivatives                8/10
    DeFi/Cross venue           7/10
    -------------------------------
    Raw score                 81/100
    Data quality multiplier   0.96
    Final score               77.8

And section 22.1's sentence is the design constraint: "Missing family must not
automatically equal zero; score should account for data availability with
explicit confidence downgrade." A missing family is left out of the denominator
and reported in `missing`, and the `confidence` is the share of the 100
available points that was observable at all ([[ADR-044]]).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from channelflow.scoring.groups import GROUP_CAPS, Group, GroupContribution

TOTAL_CAP = sum(GROUP_CAPS.values())


class NothingToScore(ValueError):
    """Every family was missing, so there is nothing to score."""


@dataclass(frozen=True)
class SignalScore:
    """A score, and everything it was computed from."""

    raw: float
    final: float
    data_quality: float
    #: The share of section 22.1's 100 points that any family could speak to.
    #: Section 22.1's "explicit confidence downgrade", made a number.
    confidence: float
    contributions: tuple[GroupContribution, ...]
    missing: tuple[Group, ...] = field(default=())

    @property
    def observed_cap(self) -> float:
        return sum(c.cap for c in self.contributions)


def score_signal(contributions: Sequence[GroupContribution], *, data_quality: float) -> SignalScore:
    """Section 22.1's score, normalized over the families that were present.

    A family that is absent is not a family that scored zero. Scoring an outage
    as a zero costs the setup that family's whole cap and produces a number
    indistinguishable from one where the evidence was genuinely against it.
    """
    if not 0.0 <= data_quality <= 1.0:
        raise ValueError(
            f"data quality multiplier {data_quality} is outside [0, 1]; section 43 has "
            "it penalize stale sources, and a multiplier above 1 would let a stale "
            "source improve a score"
        )

    seen: set[Group] = set()
    for contribution in contributions:
        if contribution.group in seen:
            raise ValueError(
                f"group {contribution.group.value!r} was supplied twice; the second "
                "would double that family's weight past its section 22.1 cap"
            )
        seen.add(contribution.group)

    if not contributions:
        raise NothingToScore(
            "no family contributed, so there is nothing to score; a score computed "
            "from nothing is not a low score"
        )

    observed_cap = sum(c.cap for c in contributions)
    raw = sum(c.value for c in contributions) / observed_cap * TOTAL_CAP
    return SignalScore(
        raw=raw,
        final=raw * data_quality,
        data_quality=data_quality,
        confidence=observed_cap / TOTAL_CAP,
        contributions=tuple(sorted(contributions, key=lambda c: c.group.value)),
        missing=tuple(sorted(set(GROUP_CAPS) - seen, key=lambda g: g.value)),
    )
