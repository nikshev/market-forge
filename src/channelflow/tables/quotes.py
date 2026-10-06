"""The top-of-book quotes table: one row per quote, its two times kept apart.

# @trace: REQ-WP-091

A quote is one venue's best bid and ask for one symbol at one instant -- the
mid the cross-venue consensus ([[REQ-WP-091]], `crossvenue/consensus.py`) is a
median *of*. The ingest reads trades only today, so no venue's mid exists yet;
this table is where the book subscription's rows will land.

Two times, and they are never the same thing (Principle II). `ts_ns` is
**exchange time**: when the venue says the quote happened, the event time a
point-in-time read filters on -- the consensus at a bar's close may use only
quotes whose `ts_ns` is at or before that close (Principle I, no look-ahead).
`ingest_ns` is **receive time**: when the path observed it, which says how old
the observation was when it arrived and never decides availability. Swapping
them would make a quote taken after the bar's close look knowable at it.

Prices are `decimal`, not `float64`, for the reason every other canonical
table here gives: a price is money, and float64 cannot hold 0.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "quotes"

#: One row per top-of-book quote.
#:
#: `ts_ns` carries event time and is typed `timestamp_ns` -- the storage
#: vocabulary's name for an event time, physically an int64 nanosecond count
#: (`schema.py` maps it to `pa.int64()`). The schema refuses any other type on
#: the event-time column, because a point-in-time filter compares nanosecond
#: counts. `ingest_ns` is plain `int64`: receive time is a fact about the
#: pipeline, not an event anybody reads as of.
SCHEMA = Schema(
    columns=(
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="bid", type="decimal"),
        Column(name="ask", type="decimal"),
        Column(name="mid", type="decimal"),
        Column(name="ts_ns", type="timestamp_ns"),
        Column(name="ingest_ns", type="int64"),
    ),
    event_time_column="ts_ns",
)


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


@dataclass(frozen=True)
class Quote:
    """One venue's top-of-book quote for one symbol, and its two times.

    `ts_ns` is exchange time and `ingest_ns` is receive time (Principle II:
    distinct, and never conflated). `mid` is carried rather than recomputed so
    a venue's own mid -- where it publishes one -- survives the write instead
    of being quietly replaced by `(bid + ask) / 2`.
    """

    venue: str
    symbol: str
    bid: Decimal
    ask: Decimal
    mid: Decimal
    ts_ns: int
    ingest_ns: int


def to_row(quote: Quote) -> dict[str, object]:
    """One quote as a row, in the schema's own column order."""
    return {
        "venue": quote.venue,
        "symbol": quote.symbol,
        "bid": quote.bid,
        "ask": quote.ask,
        "mid": quote.mid,
        "ts_ns": quote.ts_ns,
        "ingest_ns": quote.ingest_ns,
    }
