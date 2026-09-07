"""Order book levels, deltas and snapshots. PRD sections 10.2 and 10.3.

# @trace: REQ-WP-002
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from channelflow.domain.meta import EventMeta


class PriceLevel(BaseModel):
    """One rung of one side of a book.

    PRD section 10 references this four times and never defines it. Note that
    `qty` may be zero: in a delta that is how a venue says the rung is gone.
    Rejecting zero here would make removals unrepresentable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    price: Decimal = Field(gt=0)
    qty: Decimal = Field(ge=0)

    @property
    def is_removal(self) -> bool:
        return self.qty == 0


class BookDelta(BaseModel):
    """An incremental book update."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: EventMeta
    first_update_id: int | None = None
    final_update_id: int | None = None
    prev_update_id: int | None = None
    bids: tuple[PriceLevel, ...] = ()
    asks: tuple[PriceLevel, ...] = ()


class BookSnapshot(BaseModel):
    """A full book state at a point in time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: EventMeta
    update_id: int = Field(ge=0)
    bids: tuple[PriceLevel, ...] = ()
    asks: tuple[PriceLevel, ...] = ()
