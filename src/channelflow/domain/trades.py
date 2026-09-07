"""Executed trades. PRD section 10.1.

# @trace: REQ-WP-002
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from channelflow.domain.meta import EventMeta


class TradeEvent(BaseModel):
    """One executed trade on a centralized venue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: EventMeta
    trade_id: str = Field(min_length=1)
    price: Decimal = Field(gt=0)
    qty_base: Decimal = Field(gt=0)
    notional_quote: Decimal = Field(ge=0)
    aggressor_side: Literal["buy", "sell", "unknown"]
    is_buyer_maker: bool | None = None

    @property
    def identity(self) -> tuple[str, str, str]:
        """PRD section 11.2: a CEX trade is `(venue, symbol, trade_id)`."""
        return (self.meta.venue, self.meta.symbol, self.trade_id)
