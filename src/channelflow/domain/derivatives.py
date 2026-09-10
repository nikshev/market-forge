"""Derivatives state and liquidations. PRD sections 10.4 and 10.5.

# @trace: REQ-WP-002

Prices here are Decimal, where PRD section 10 writes float. ADR-003: a mark
price is a price in exactly the same sense as a trade price, and the PRD gives
no reason for the difference. Rates and ratios stay floating -- they are
estimates, and a rounding error in one is not a correctness failure.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from channelflow.domain.meta import EventMeta


class DerivativesState(BaseModel):
    """Funding, open interest and basis at a point in time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: EventMeta
    mark_price: Decimal | None = None
    index_price: Decimal | None = None

    #: Signed by nature -- funding can be negative.
    funding_rate: float | None = None
    next_funding_time_ns: int | None = None
    open_interest_base: float | None = None
    open_interest_usd: float | None = None
    #: Signed by nature -- basis can be negative.
    basis_bps: float | None = None

    #: Longs over shorts among all accounts, as the venue reports it. `None`
    #: when the venue publishes none: an absent ratio says nobody knows, and a
    #: ratio of 1.0 says longs and shorts are even. A silent venue is not a
    #: balanced market ([[REQ-WP-031]]).
    long_short_ratio: float | None = Field(default=None, gt=0.0)
    #: The same among the venue's largest accounts. A separate field rather than
    #: an average with the one above: they measure different populations, and
    #: their mean describes neither.
    top_trader_long_short_ratio: float | None = Field(default=None, gt=0.0)


class LiquidationEvent(BaseModel):
    """A forced position closure."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: EventMeta
    side: Literal["long_liquidated", "short_liquidated", "unknown"]
    price: Decimal = Field(gt=0)
    qty: Decimal = Field(gt=0)
    notional_usd: Decimal = Field(ge=0)
