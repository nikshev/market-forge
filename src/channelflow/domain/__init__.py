"""Canonical market data models (PRD section 10).

# @trace: REQ-WP-002

What a connector imports. Every model here is frozen, embeds `EventMeta`, and
uses `Decimal` for anything monetary -- see [ADR-003] for why that differs from
the PRD's literal text in two places.

Serialize with `serialization.dumps` rather than `model_dump_json`: nanosecond
timestamps and decimals must not become JSON numbers, and that module is where
the convention lives.
"""

from channelflow.domain.book import BookDelta, BookSnapshot, PriceLevel
from channelflow.domain.defi import DexLiquidityEvent, DexSwapEvent
from channelflow.domain.derivatives import DerivativesState, LiquidationEvent
from channelflow.domain.meta import ChainMeta, EventMeta
from channelflow.domain.trades import TradeEvent

__all__ = [
    "BookDelta",
    "BookSnapshot",
    "ChainMeta",
    "DerivativesState",
    "DexLiquidityEvent",
    "DexSwapEvent",
    "EventMeta",
    "LiquidationEvent",
    "PriceLevel",
    "TradeEvent",
]
