"""PRD section 44A's position, anchor and proposal models.

# @trace: REQ-WP-020

Section 44A.2 states the rule the whole engine exists to enforce:

    LONG:  new_stop >= current_effective_stop
    SHORT: new_stop <= current_effective_stop

    "The adaptive stop may tighten risk but must never silently widen the
    maximum risk beyond the accepted initial-risk contract."

Every model here is frozen. Section 44A.39 requires the historical stop path to
be immutable, and a value that cannot be mutated cannot be rewritten.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Side = Literal["LONG", "SHORT"]


class PositionPhase(StrEnum):
    """PRD section 44A.4's lifecycle."""

    OPENED = "OPENED"
    INITIAL_RISK = "INITIAL_RISK"
    PROTECTING = "PROTECTING"
    STRUCTURE_TRAIL = "STRUCTURE_TRAIL"
    TREND_RIDE = "TREND_RIDE"
    EXITING = "EXITING"


class ReasonCode(StrEnum):
    """Why a stop moved, or did not.

    An enumeration rather than free text, so a replay can aggregate them and a
    test can assert on them without matching strings (ADR-032).
    """

    STRUCTURAL_ANCHOR = "moved to a confirmed structural anchor"
    NOISE_BUFFER_APPLIED = "pushed back by the noise buffer"
    HELD_NO_ANCHOR = "held: no anchor was knowable at this instant"
    HELD_WOULD_WIDEN = "held: the proposal would have widened risk"
    HELD_BELOW_THRESHOLD = "held: the improvement was under the threshold"
    HELD_COOLDOWN = "held: a movement is still in cooldown"
    HELD_DATA_QUALITY = "held: the data-quality freeze is active"
    HELD_TOO_CLOSE = "held: the proposal sat inside the minimum distance"
    REFUSED_BEYOND_MARKET = "refused: the stop would sit beyond the market price"


class AnchorKind(StrEnum):
    """What produced a level. No entry derives a stop from price alone --
    section 44A.39 forbids a blind price-following path in the default policy,
    and an enumeration with no `PRICE_ONLY` member is how that is enforced."""

    CONFIRMED_SWING = "confirmed_swing"
    CHANNEL_BOUNDARY = "channel_boundary"
    VOLUME_NODE = "volume_node"
    INITIAL_STOP = "initial_stop"


class PositionState(BaseModel):
    """PRD section 44A.3's required position fields.

    `initial_stop_price` is not optional. Every guard here is measured against
    the accepted initial risk, and without it there is nothing to enforce.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    position_id: uuid.UUID
    instrument_id: str = Field(min_length=1)
    venue: str | None = None
    side: Side
    quantity: Decimal = Field(gt=0)
    entry_time_ns: int = Field(ge=0)
    average_entry_price: Decimal = Field(gt=0)
    initial_stop_price: Decimal = Field(gt=0)
    hard_stop_price: Decimal | None = None
    current_strategy_stop: Decimal = Field(gt=0)
    original_target_price: Decimal | None = None
    fees_paid: Decimal = Field(ge=0, default=Decimal(0))
    status: Literal["OPEN", "REDUCED", "CLOSING", "CLOSED"] = "OPEN"

    @property
    def initial_risk_per_unit(self) -> Decimal:
        """PRD section 44A.24's `R0`."""
        if self.side == "LONG":
            return self.average_entry_price - self.initial_stop_price
        return self.initial_stop_price - self.average_entry_price

    def model_post_init(self, _: object) -> None:
        if self.initial_risk_per_unit <= 0:
            raise ValueError(
                f"a {self.side} position at {self.average_entry_price} with an initial "
                f"stop at {self.initial_stop_price} has no risk to manage: the stop is "
                "on the wrong side of the entry"
            )


class StopAnchor(BaseModel):
    """A structural level, and when it became knowable.

    `known_at_ns` is the field that makes the whole engine causal. PRD section
    44A.3: "no future-confirmed swing may be used before its `known_at`" --
    which is exactly the timestamp REQ-WP-019 built.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: AnchorKind
    price: Decimal = Field(gt=0)
    known_at_ns: int = Field(ge=0)
    description: str = Field(min_length=1)


class StopProposal(BaseModel):
    """What the policy decided, including deciding not to move.

    ADR-032: a hold is a proposal. Returning `None` when nothing should move
    would satisfy section 44A.39's "policy may conclude that leaving the stop
    unchanged is optimal" and quietly defeat its "every movement has a
    structural anchor and reason codes" -- because six different holds would
    all look identical downstream.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    price: Decimal = Field(gt=0)
    anchor: StopAnchor | None
    reasons: tuple[ReasonCode, ...] = Field(min_length=1)
    at_ns: int = Field(ge=0)
    phase: PositionPhase

    @property
    def moved(self) -> bool:
        return not any(
            r.name.startswith("HELD") or r.name.startswith("REFUSED") for r in self.reasons
        )


@dataclass(frozen=True)
class StopPolicyOutcome:
    """What replaying one policy over one path produced.

    Realized R is net of fees and modelled slippage (ADR-031), and the exit
    price is the first executable one -- PRD section 44A.23: "Risk metrics use
    realized executable exit when available, not ideal stop price."
    """

    policy: str
    exited: bool
    requested_stop_price: Decimal | None
    realized_exit_price: Decimal | None
    stop_slippage_bps: float
    fees: Decimal
    realized_r: float | None
    reached_target_after_stop: bool
    stop_updates: int
    reason_counts: dict[str, int]
