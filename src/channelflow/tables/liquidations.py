"""PRD §10.5's `LiquidationEvent`, and the stream's heartbeat, in one canonical table.

# @trace: REQ-WP-094

Events and heartbeats share a table because they answer one question together: what was
liquidated, and was anyone listening. **A quiet window is a reading only where the stream was up
for every minute of it** -- zero liquidated in five minutes is true of a market watched and false
of one that was not -- so while the stream's connection is alive the collector writes a
`heartbeat` row per symbol per minute, and the worker calls a window covered only if all its
minutes have one ([[ADR-070]]).

Two times, never conflated (Principle II): `event_time_ns` is the venue's, what a point-in-time
read filters on, and `ingest_time_ns` is when this system received it. A heartbeat is dated at the
minute boundary it covers, in both columns: it is a fact about our own connection, observed when
it is written.

Prices, quantities and notionals are `decimal`, not `float64`, for the reason every canonical
table here gives. A heartbeat has none: null, never a default."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from channelflow.domain import EventMeta, LiquidationEvent
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "liquidations"

EVENT = "event"
HEARTBEAT = "heartbeat"

SCHEMA = Schema(
    columns=(
        Column(name="event_time_ns", type="timestamp_ns"),
        Column(name="ingest_time_ns", type="int64"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="market_type", type="string"),
        Column(name="source", type="string"),
        Column(name="kind", type="string"),
        Column(name="side", type="string"),
        Column(name="price", type="decimal"),
        Column(name="qty", type="decimal"),
        Column(name="notional_usd", type="decimal"),
    ),
    event_time_column="event_time_ns",
)


@dataclass(frozen=True)
class Heartbeat:
    """The stream was connected, and had been for the whole minute that ended at `at_ns`."""

    venue: str
    symbol: str
    at_ns: int


Identity = tuple[object, ...]


def event_identity(event: LiquidationEvent) -> Identity:
    meta = event.meta
    return (EVENT, meta.venue, meta.symbol, meta.event_time_ns, event.price, event.qty, event.side)


def heartbeat_identity(beat: Heartbeat) -> Identity:
    return (HEARTBEAT, beat.venue, beat.symbol, beat.at_ns)


def event_row(event: LiquidationEvent) -> dict[str, object]:
    meta = event.meta
    return {
        "event_time_ns": meta.event_time_ns,
        "ingest_time_ns": meta.ingest_time_ns,
        "venue": meta.venue,
        "symbol": meta.symbol,
        "market_type": meta.market_type,
        "source": meta.source,
        "kind": EVENT,
        "side": event.side,
        "price": event.price,
        "qty": event.qty,
        "notional_usd": event.notional_usd,
    }


def heartbeat_row(beat: Heartbeat) -> dict[str, object]:
    return {
        "event_time_ns": beat.at_ns,
        "ingest_time_ns": beat.at_ns,
        "venue": beat.venue,
        "symbol": beat.symbol,
        "market_type": "perp",
        "source": f"{beat.venue}-ws-liquidation",
        "kind": HEARTBEAT,
        "side": None,
        "price": None,
        "qty": None,
        "notional_usd": None,
    }


def from_row(row: Mapping[str, Any]) -> LiquidationEvent | Heartbeat:
    if row["kind"] == HEARTBEAT:
        return Heartbeat(
            venue=str(row["venue"]), symbol=str(row["symbol"]), at_ns=int(row["event_time_ns"])
        )
    return LiquidationEvent(
        meta=EventMeta(
            source=str(row["source"]),
            venue=str(row["venue"]),
            market_type=str(row["market_type"]),
            symbol=str(row["symbol"]),
            event_time_ns=int(row["event_time_ns"]),
            ingest_time_ns=int(row["ingest_time_ns"]),
            sequence=None,
            source_event_id=None,
        ),
        side=row["side"],
        price=Decimal(str(row["price"])),
        qty=Decimal(str(row["qty"])),
        notional_usd=Decimal(str(row["notional_usd"])),
    )


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


def _identity_of_row(row: Mapping[str, Any]) -> Identity:
    if row["kind"] == HEARTBEAT:
        return (HEARTBEAT, row["venue"], row["symbol"], int(row["event_time_ns"]))
    return (
        EVENT,
        row["venue"],
        row["symbol"],
        int(row["event_time_ns"]),
        Decimal(str(row["price"])),
        Decimal(str(row["qty"])),
        row["side"],
    )


@dataclass
class LiquidationSink:
    """Collects events and heartbeats and writes them in batches, each once.

    An observation already stored -- by this sink, an earlier one, or a process since restarted --
    is dropped on offer: after a reconnect the venue may replay recent events, and a heartbeat is
    written once per symbol per minute however often the stream task steps.
    """

    table: IcebergTable
    _buffer: list[dict[str, object]] = field(default_factory=list)
    _known: set[Identity] | None = None

    def _seen(self) -> set[Identity]:
        if self._known is None:
            self._known = {_identity_of_row(r) for r in self.table.read().to_pylist()}
        return self._known

    def _offer(self, key: Identity, row: dict[str, object]) -> None:
        known = self._seen()
        if key in known:
            return
        known.add(key)
        self._buffer.append(row)

    def __call__(self, event: LiquidationEvent) -> None:
        self._offer(event_identity(event), event_row(event))

    def heartbeat(self, beat: Heartbeat) -> None:
        self._offer(heartbeat_identity(beat), heartbeat_row(beat))

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def flush(self) -> str | None:
        if not self._buffer:
            return None
        snapshot = self.table.append(self._buffer)
        self._buffer.clear()
        return snapshot.content_hash


def read(
    table: IcebergTable,
) -> tuple[dict[tuple[str, str], list[LiquidationEvent]], dict[tuple[str, str], list[int]]]:
    """Events by `(venue, symbol)` sorted by event time, and heartbeat minute-ends the same way."""
    events: dict[tuple[str, str], list[LiquidationEvent]] = defaultdict(list)
    beats: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in table.read().to_pylist():
        item = from_row(row)
        if isinstance(item, Heartbeat):
            beats[(item.venue, item.symbol)].append(item.at_ns)
        else:
            events[(item.meta.venue, item.meta.symbol)].append(item)
    for series in events.values():
        series.sort(key=lambda e: (e.meta.event_time_ns, e.meta.ingest_time_ns))
    for series_beats in beats.values():
        series_beats.sort()
    return dict(events), dict(beats)
