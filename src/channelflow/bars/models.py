"""The bar PRD section 12 specifies.

# @trace: REQ-WP-005
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Bar(BaseModel):
    """One event-time window's aggregate of trades.

    Frozen, because a published bar that can still change is the repainting
    PRD section 0.5 forbids. `is_final` says whether it may be used for signal
    generation -- PRD section 12 defaults to finalized bars only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe_ns: int = Field(gt=0)
    open_time_ns: int = Field(ge=0)
    close_time_ns: int = Field(gt=0)

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume_base: Decimal = Field(ge=0)
    volume_quote: Decimal = Field(ge=0)
    trade_count: int = Field(ge=0)

    #: Split by the trade's aggressor side. This is what makes order-flow
    #: analysis possible later, and it cannot be recovered from OHLCV alone.
    aggressive_buy_base: Decimal = Field(ge=0)
    aggressive_sell_base: Decimal = Field(ge=0)
    delta_base: Decimal

    vwap: Decimal
    high_time_ns: int = Field(ge=0)
    low_time_ns: int = Field(ge=0)
    first_trade_id: str
    last_trade_id: str

    is_final: bool
