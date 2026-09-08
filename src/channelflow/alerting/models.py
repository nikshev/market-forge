"""What an alert is, and how it is identified.

# @trace: REQ-WP-008

The signal id is derived, never generated (ADR-017). A random UUID would
satisfy PRD section 27.1's URL format and quietly break two principles: XI
(reproducible results) and VII (live and replay are the same code). A replay
producing fresh ids would produce different alerts, different dedupe decisions
and a different audit -- every one of them looking correct.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from channelflow.channels import ChannelSnapshot
from channelflow.signals import Candidate

#: A fixed namespace, so the digest is stable across processes and releases.
#: Regenerating this would change every signal id in existence.
SIGNAL_NAMESPACE = uuid.UUID("6f3d1a2e-8b47-5c19-9f2a-1d4e7c05b3a8")


def signal_id_for(candidate: Candidate) -> uuid.UUID:
    """A UUID that is a function of the setup, not of when it was computed.

    The tuple is the candidate's identity. REQ-WP-007 allows one candidate per
    symbol and timeframe (FR-014) and forbids reopening on the bar that closed
    one (FR-018), so `opened_at_ns` cannot repeat within it.

    This has no entropy and must not be used where unguessability matters. It
    names a public market setup; anyone holding the same data derives the same
    id, which is the point.
    """
    key = "|".join(
        (
            candidate.venue,
            candidate.symbol,
            str(candidate.timeframe_ns),
            str(candidate.opened_at_ns),
            candidate.direction,
            candidate.boundary,
        )
    )
    return uuid.uuid5(SIGNAL_NAMESPACE, key)


class OrderFlowSummary(BaseModel):
    """The order-flow block of PRD section 26.1, already reduced to words.

    The reduction happens at the call site rather than here: "bearish" is a
    judgement about a number, and a formatter is the wrong place to make one.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ofi_30s: str = Field(min_length=1)
    depth_imbalance_25bps: float
    wall_persistence: str = Field(min_length=1)


class Alert(BaseModel):
    """One thing worth saying, and everything needed to say it.

    Frozen. PRD section 0.5 forbids rewriting a finalized record, and an alert
    describes what was true when it was queued -- a later terminal state does
    not unmake it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: Candidate
    #: Optional because ADR-016 omits what has no source. A missing channel
    #: means the block is absent, not empty.
    channel: ChannelSnapshot | None = None
    order_flow: OrderFlowSummary | None = None

    price: Decimal = Field(gt=0)
    invalidation_price: Decimal = Field(gt=0)
    research_target_price: Decimal = Field(gt=0)
    event_time_ns: int = Field(ge=0)
    #: No default. A hard-coded host works in exactly one deployment, and a
    #: message whose only actionable element is broken is worse than none.
    chart_base_url: str = Field(min_length=1)

    @property
    def signal_id(self) -> uuid.UUID:
        return signal_id_for(self.candidate)


class AttemptOutcome(BaseModel):
    """One try at delivering one alert."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempt: int = Field(ge=1)
    ok: bool
    detail: str = Field(min_length=1)
    #: Event time, never a clock reading (ADR-018).
    at_ns: int = Field(ge=0)


class AuditRecord(BaseModel):
    """What happened to one alert, from queueing to its final state.

    Append-only, and the observation point for every test here -- which is also
    what an operator reads when something goes wrong.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_id: uuid.UUID
    symbol: str = Field(min_length=1)
    queued_at_ns: int = Field(ge=0)
    status: Literal["delivered", "dead_lettered", "suppressed"]
    reason: str = Field(min_length=1)
    attempts: tuple[AttemptOutcome, ...] = ()
