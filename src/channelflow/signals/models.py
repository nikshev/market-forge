"""Candidate lifecycle records (PRD section 21.2).

# @trace: REQ-WP-007
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CandidateState(StrEnum):
    """PRD section 21.2's lifecycle, and the only vocabulary -- see ADR-008.

    Section 21.1 names states per family (`APPROACHING_UPPER`, `SIGNAL_SHORT`).
    Those are the same steps seen from one family's point of view; direction and
    boundary live on the candidate instead, so the transition table stays one
    table however many families are added.
    """

    NONE = "none"
    APPROACH = "approach"
    TOUCH = "touch"
    REJECTION_PENDING = "rejection_pending"
    CONFIRMED = "confirmed"
    ALERTED = "alerted"
    RESOLVED = "resolved"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


TERMINAL = frozenset({CandidateState.RESOLVED, CandidateState.INVALIDATED, CandidateState.EXPIRED})

#: The only legal moves. PRD section 21.2 gives the happy path; invalidation and
#: expiry may interrupt it from any live state. Keeping this as data rather than
#: as branching code is what makes "does this skip a step" answerable by reading.
ALLOWED: dict[CandidateState, frozenset[CandidateState]] = {
    CandidateState.NONE: frozenset({CandidateState.APPROACH}),
    CandidateState.APPROACH: frozenset(
        {CandidateState.TOUCH, CandidateState.INVALIDATED, CandidateState.EXPIRED}
    ),
    CandidateState.TOUCH: frozenset(
        {
            CandidateState.REJECTION_PENDING,
            CandidateState.INVALIDATED,
            CandidateState.EXPIRED,
        }
    ),
    CandidateState.REJECTION_PENDING: frozenset(
        {CandidateState.CONFIRMED, CandidateState.INVALIDATED, CandidateState.EXPIRED}
    ),
    CandidateState.CONFIRMED: frozenset(
        {CandidateState.ALERTED, CandidateState.RESOLVED, CandidateState.INVALIDATED}
    ),
    CandidateState.ALERTED: frozenset({CandidateState.RESOLVED, CandidateState.INVALIDATED}),
    CandidateState.RESOLVED: frozenset(),
    CandidateState.INVALIDATED: frozenset(),
    CandidateState.EXPIRED: frozenset(),
}


class Transition(BaseModel):
    """One state change, the bar that caused it, and why.

    Frozen and appended, never edited. A confirmation that happened is not
    unhappened by what follows -- PRD section 0.5.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_state: CandidateState
    to_state: CandidateState
    bar_close_time_ns: int = Field(ge=0)
    reason: str = Field(min_length=1)


class Candidate(BaseModel):
    """A setup being tracked, and the transitions that brought it here."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe_ns: int = Field(gt=0)

    #: Attributes, not states. ADR-008.
    direction: Literal["long", "short"]
    boundary: Literal["upper", "lower", "middle"]

    state: CandidateState
    opened_at_ns: int = Field(ge=0)
    bars_since_open: int = Field(ge=0)
    history: tuple[Transition, ...]

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL
