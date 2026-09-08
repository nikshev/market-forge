"""What a venue tells the cross-venue engine (PRD section 17).

# @trace: REQ-WP-016

A quote is one venue's view of one asset at one instant. The registry
(REQ-ASSET-001) is what makes two quotes comparable -- never their tickers,
which is PRD section 18.13's prohibition and the reason that registry exists.

Executable quotes are supplied rather than computed (ADR-039). Fees, gas and
MEV margins are venue-specific operational inputs, and an engine holding
assumptions about them would hide those assumptions at every call site.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from channelflow.assets import VenueKind


class VenueQuote(BaseModel):
    """One venue's mid for one representation, and when it was observed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str = Field(min_length=1)
    kind: VenueKind
    #: The registry key of the representation being quoted. Two venues are
    #: comparable when their representations resolve to one canonical asset.
    representation_key: str = Field(min_length=1)
    mid: Decimal = Field(gt=0)
    observed_at_ns: int = Field(ge=0)


class ExecutableQuote(BaseModel):
    """What a given size actually costs on one venue (PRD section 18.14).

    `all_in_cost_bps` is the caller's figure: spread plus fee plus book impact
    for an order book, AMM fee plus price impact plus gas for a pool. The
    engine ranks these; it does not compute them (ADR-039).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str = Field(min_length=1)
    kind: VenueKind
    notional: Decimal = Field(gt=0)
    #: `None` when the venue cannot fill the size. Excluded rather than ranked
    #: last: "cannot fill" and "expensive" are different answers.
    executable_price: Decimal | None = None
    all_in_cost_bps: float | None = None

    @property
    def fillable(self) -> bool:
        return self.executable_price is not None and self.all_in_cost_bps is not None
