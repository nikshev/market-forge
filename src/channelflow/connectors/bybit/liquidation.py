"""Bybit `allLiquidation` frames to canonical liquidation events (REQ-WP-094).

# @trace: REQ-WP-094

Pure: a decoded frame in, events out.

**Bybit's side is the position's, the opposite convention from Binance's and OKX's order side.**
The documentation for the field says that receiving a `Buy` update means a long position has been
liquidated. So `S == "Buy"` is `long_liquidated` here, where a Binance `BUY` is a short. Both are
pinned by a test per venue, because the two conventions look identical in the data and are opposite
in meaning.

`v` is the size in base units on the linear contract and `p` the bankruptcy price; the frame carries
a list, so one frame may hold several events.
"""

from __future__ import annotations

from collections.abc import Collection
from decimal import Decimal, InvalidOperation
from typing import Any

from channelflow.domain import EventMeta, LiquidationEvent

MS_TO_NS = 1_000_000


class LiquidationRefused(ValueError):
    """A row that is a liquidation and cannot be read as one; the reason is the message."""


def _decimal(row: dict[str, Any], key: str) -> Decimal:
    try:
        return Decimal(str(row[key]))
    except (KeyError, InvalidOperation) as exc:
        raise LiquidationRefused(
            f"allLiquidation: field {key!r} is missing or not a number"
        ) from exc


def liquidation_events(
    frame: dict[str, Any], *, ingest_time_ns: int, symbols: Collection[str] | None = None
) -> list[LiquidationEvent]:
    topic = frame.get("topic")
    if not isinstance(topic, str) or not topic.startswith("allLiquidation."):
        return []  # an acknowledgement, a pong, another topic
    rows = frame.get("data")
    if not isinstance(rows, list):
        raise LiquidationRefused("allLiquidation: the frame carries no data list")

    events = []
    for row in rows:
        symbol = str(row.get("s", ""))
        if symbols is not None and symbol not in symbols:
            continue
        side = {"Buy": "long_liquidated", "Sell": "short_liquidated"}.get(str(row.get("S")))
        if side is None:
            raise LiquidationRefused(f"allLiquidation: unknown side {row.get('S')!r}")
        price, qty = _decimal(row, "p"), _decimal(row, "v")
        if price <= 0 or qty <= 0:
            raise LiquidationRefused(
                f"allLiquidation: price {price} and size {qty} must be positive"
            )
        try:
            event_time_ns = int(row["T"]) * MS_TO_NS
        except (KeyError, TypeError, ValueError) as exc:
            raise LiquidationRefused("allLiquidation: no usable time `T`") from exc
        events.append(
            LiquidationEvent(
                meta=EventMeta(
                    source="bybit-ws-liquidation",
                    venue="bybit",
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
        )
    return events
