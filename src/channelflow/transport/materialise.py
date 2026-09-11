"""Turning a topic into rows on the canonical plane.

# @trace: REQ-WP-042

PRD section 6.4.3's last rule about consumers is the one with teeth:

    all consumers must be replay-safe and idempotent where materialization
    occurs

This repository has already paid for it. Duplicate writes on re-run were a real
defect, fixed by [[ADR-056]]'s per-series watermark, and a consumer that
materialised without that discipline would put it straight back.

So this module does **not** write a table. It decodes records and hands them to
`record_bars`, which reads the watermark first because every entry point does.
The moment this knew how to append, there would be two ways into the canonical
plane and one of them would eventually forget -- which is exactly why
[[ADR-063]] refused a sink connector. Building one here in Python would be the
same mistake in a friendlier language.
"""

from __future__ import annotations

from decimal import Decimal

from channelflow.domain import EventMeta, TradeEvent
from channelflow.lakehouse import Catalog
from channelflow.pipeline.replay import Recording, record_bars
from channelflow.transport import EventConsumer, Record

#: Section 6.4.3's name for the stream this consumes.
TRADES_TOPIC = "market.trade.v1"


def materialise_trades(
    consumer: EventConsumer,
    *,
    catalog: Catalog,
    timeframe_ns: int,
    limit: int = 1_000,
) -> Recording:
    """Consume trades and write the bars the table does not already have.

    The watermark is not here and is not repeated: `record_bars` reads it, as it
    does for every other caller.
    """
    records = consumer.poll(limit=limit)
    trades = [_trade(record) for record in records]
    return record_bars(trades, catalog=catalog, timeframe_ns=timeframe_ns)


def _trade(record: Record) -> TradeEvent:
    """One record as the domain sees it.

    Both timestamps are carried through. The event time is the only clock a
    feature may use; the ingestion time travels beside it so that PRD section
    9's rule stays checkable by whoever reads the row.
    """
    payload = record.payload
    price = Decimal(str(payload["price"]))
    qty = Decimal(str(payload["size"]))
    maker = payload.get("buyer_is_maker")
    return TradeEvent(
        meta=EventMeta(
            source="transport",
            venue=str(payload["venue"]),
            market_type=str(payload.get("market_type", "spot")),
            symbol=str(payload["symbol"]),
            event_time_ns=record.event_time_ns,
            ingest_time_ns=record.ingest_time_ns,
        ),
        trade_id=str(payload["trade_id"]),
        price=price,
        qty_base=qty,
        notional_quote=price * qty,
        # A maker flag says which side was passive, so the aggressor is the
        # other one. Absent, the side is unknown rather than guessed: PRD
        # section 13's trade-side normalization is a real rule and "buy" is not
        # a safe default for a number that decides order-flow imbalance.
        aggressor_side="unknown" if maker is None else ("sell" if maker else "buy"),
        is_buyer_maker=None if maker is None else bool(maker),
    )
