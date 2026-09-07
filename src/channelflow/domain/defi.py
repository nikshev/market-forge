"""On-chain swaps and liquidity changes. PRD sections 10.6 and 10.7.

# @trace: REQ-WP-002
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from channelflow.domain.meta import ChainMeta, EventMeta


class DexSwapEvent(BaseModel):
    """One swap against an AMM pool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: EventMeta
    chain: ChainMeta

    dex: str = Field(min_length=1)
    pool: str = Field(min_length=1)
    token0: str = Field(min_length=1)
    token1: str = Field(min_length=1)

    #: Signed: negative is out of the pool, positive is in.
    amount0: Decimal
    amount1: Decimal
    price_token1_per_token0: Decimal = Field(gt=0)
    notional_usd: Decimal | None = None

    sqrt_price_x96: int | None = None
    tick: int | None = None
    liquidity: int | None = None

    @property
    def identity(self) -> tuple[int, str, int]:
        """PRD section 11.2: a DEX log is `(chain_id, tx_hash, log_index)`."""
        return (self.chain.chain_id, self.chain.tx_hash, self.chain.log_index)


class DexLiquidityEvent(BaseModel):
    """A change to an AMM pool's liquidity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    meta: EventMeta
    chain: ChainMeta

    dex: str = Field(min_length=1)
    pool: str = Field(min_length=1)
    event_type: Literal["mint", "burn", "collect", "modify"]

    tick_lower: int | None = None
    tick_upper: int | None = None
    #: Signed: burns are negative.
    liquidity_delta: int
    amount0: Decimal | None = None
    amount1: Decimal | None = None

    @property
    def identity(self) -> tuple[int, str, int]:
        """PRD section 11.2: a DEX log is `(chain_id, tx_hash, log_index)`."""
        return (self.chain.chain_id, self.chain.tx_hash, self.chain.log_index)
