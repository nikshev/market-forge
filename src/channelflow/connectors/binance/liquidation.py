"""Binance USD-M `forceOrder` frames to canonical liquidation events (REQ-WP-094).

# @trace: REQ-WP-094

Pure: a decoded frame in, events out, no socket.

**The side is the side of the position that was closed.** Binance publishes the *closing order's*
side, so a forced SELL closes a long: `S == "SELL"` is `long_liquidated`. Reading the order's side
as the position's would flip the sign of every liquidation number downstream and be invisible in a
chart, which is why the mapping is pinned by a test per venue.

Price and quantity are what was **filled**: `ap` (average fill price) and `z` (accumulated filled
quantity). `p` and `q` are the order as submitted -- a limit price and a size, not what happened --
and are the fallback only where the venue reports nothing filled. `notional_usd` is price times
quantity, which is USD on a USDT-margined contract by the same convention every other USDT-quoted
figure in this system makes.

The stream is the all-market one (`!forceOrder@arr`): a symbol's own stream is silent for minutes
at a time, and one connection carrying every symbol is filtered here to the ones asked for.
"""

from __future__ import annotations

from collections.abc import Collection
from decimal import Decimal, InvalidOperation
from typing import Any

from channelflow.domain import EventMeta, LiquidationEvent

MS_TO_NS = 1_000_000


class LiquidationRefused(ValueError):
    """A frame that is a liquidation and cannot be read as one; the reason is the message."""


def _decimal(order: dict[str, Any], key: str) -> Decimal:
    try:
        return Decimal(str(order[key]))
    except (KeyError, InvalidOperation) as exc:
        raise LiquidationRefused(f"forceOrder: field {key!r} is missing or not a number") from exc


def liquidation_events(
    frame: dict[str, Any], *, ingest_time_ns: int, symbols: Collection[str] | None = None
) -> list[LiquidationEvent]:
    """The liquidation in a frame, or nothing for a frame that is not one."""
    if frame.get("e") != "forceOrder":
        return []
    order = frame.get("o")
    if not isinstance(order, dict):
        raise LiquidationRefused("forceOrder: the frame carries no order")
    symbol = str(order.get("s", ""))
    if symbols is not None and symbol not in symbols:
        return []

    side = {"SELL": "long_liquidated", "BUY": "short_liquidated"}.get(str(order.get("S")))
    if side is None:
        raise LiquidationRefused(f"forceOrder: unknown side {order.get('S')!r}")

    price = _decimal(order, "ap")
    if price <= 0:
        price = _decimal(order, "p")
    qty = _decimal(order, "z")
    if qty <= 0:
        qty = _decimal(order, "q")
    if price <= 0 or qty <= 0:
        raise LiquidationRefused(f"forceOrder: price {price} and quantity {qty} must be positive")
    try:
        event_time_ns = int(order["T"]) * MS_TO_NS
    except (KeyError, TypeError, ValueError) as exc:
        raise LiquidationRefused("forceOrder: no usable trade time `T`") from exc

    return [
        LiquidationEvent(
            meta=EventMeta(
                source="binance-ws-liquidation",
                venue="binance",
                market_type="perp",
                symbol=symbol,
                event_time_ns=event_time_ns,
                ingest_time_ns=ingest_time_ns,
                sequence=None,
                source_event_id=None,
            ),
            side=side,  # type: ignore[arg-type]
            price=price,
            qty=qty,
            notional_usd=price * qty,
        )
    ]
