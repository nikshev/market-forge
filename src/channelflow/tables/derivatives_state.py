"""PRD §10.4's `DerivativesState`, as a canonical table.

# @trace: REQ-WP-093

The collector ([[REQ-WP-093]]) stores one row per observation and **computes no feature**; the
worker reads these rows and writes the features as of each bar's close ([[ADR-070]]).

Two times, and they are never the same thing (Principle II). `event_time_ns` is the venue's: when
the figure was true, which is what a point-in-time read filters on. `ingest_time_ns` is when this
system received it, and the worker also requires it to be at or before a bar's close for a polled
state -- a state the collector saw after the close was not knowable at it.

`source` says what kind of row it is and is part of its identity: `<venue>-rest` for a poll,
`binance-rest-oi` for Binance's open-interest bucket, and `<venue>-funding-history` for a settled
funding rate loaded from the venue's history. The history rows are the funding series; polled
states carry the venue's current, still-revisable estimate and are never read as settled.

Prices are `decimal`, not `float64`, for the reason every canonical table here gives. Rates and
ratios stay floating, as `DerivativesState` has them: estimates, and a rounding error in one is
not a correctness failure.

An absent field is a null, never a default: a `funding_rate` of 0.0 and no funding rate are
different facts ([[REQ-WP-031]]).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from channelflow.domain import DerivativesState, EventMeta
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "derivatives_state"

SCHEMA = Schema(
    columns=(
        Column(name="event_time_ns", type="timestamp_ns"),
        Column(name="ingest_time_ns", type="int64"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="market_type", type="string"),
        Column(name="source", type="string"),
        Column(name="mark_price", type="decimal"),
        Column(name="index_price", type="decimal"),
        Column(name="funding_rate", type="float64"),
        Column(name="next_funding_time_ns", type="int64"),
        Column(name="open_interest_base", type="float64"),
        Column(name="open_interest_usd", type="float64"),
        Column(name="basis_bps", type="float64"),
    ),
    event_time_column="event_time_ns",
)

Identity = tuple[str, str, int, str]


def identity(state: DerivativesState) -> Identity:
    """What makes two observations the same one: venue, symbol, venue time and kind of row."""
    meta = state.meta
    return (meta.venue, meta.symbol, meta.event_time_ns, meta.source)


def to_row(state: DerivativesState) -> dict[str, object]:
    meta = state.meta
    return {
        "event_time_ns": meta.event_time_ns,
        "ingest_time_ns": meta.ingest_time_ns,
        "venue": meta.venue,
        "symbol": meta.symbol,
        "market_type": meta.market_type,
        "source": meta.source,
        "mark_price": state.mark_price,
        "index_price": state.index_price,
        "funding_rate": state.funding_rate,
        "next_funding_time_ns": state.next_funding_time_ns,
        "open_interest_base": state.open_interest_base,
        "open_interest_usd": state.open_interest_usd,
        "basis_bps": state.basis_bps,
    }


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def from_row(row: Mapping[str, Any]) -> DerivativesState:
    return DerivativesState(
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
        mark_price=_decimal(row["mark_price"]),
        index_price=_decimal(row["index_price"]),
        funding_rate=row["funding_rate"],
        next_funding_time_ns=row["next_funding_time_ns"],
        open_interest_base=row["open_interest_base"],
        open_interest_usd=row["open_interest_usd"],
        basis_bps=row["basis_bps"],
    )


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


def stored_identities(table: IcebergTable) -> set[Identity]:
    """Every observation already on record: one read, so a restart does not store a row twice."""
    rows = table.read()
    if rows.num_rows == 0:
        return set()
    columns = [rows[name].to_pylist() for name in ("venue", "symbol", "event_time_ns", "source")]
    return {(str(v), str(s), int(t), str(k)) for v, s, t, k in zip(*columns, strict=True)}


@dataclass
class DerivativesStateSink:
    """Collects states and writes them to the table in batches, each observation once.

    Buffered, for `BarSink`'s reason: every append is a commit, and a commit per poll would make
    the snapshot chain as long as the series. An observation already stored -- by this sink, by an
    earlier one, or by a process that has since restarted -- is dropped on offer, so the hourly
    funding-history refresh and a restart are both safe.

    Nothing here flushes on a timer, because nothing here reads a clock: the collector decides.
    """

    table: IcebergTable
    _buffer: list[dict[str, object]] = field(default_factory=list)
    _known: set[Identity] | None = None

    def _seen(self) -> set[Identity]:
        if self._known is None:
            self._known = stored_identities(self.table)
        return self._known

    def __call__(self, state: DerivativesState) -> None:
        key = identity(state)
        known = self._seen()
        if key in known:
            return
        known.add(key)
        self._buffer.append(to_row(state))

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def flush(self) -> str | None:
        """Commit what is buffered and return the snapshot's content hash; `None` if nothing is.

        A failed commit keeps the rows: they stay buffered for the next flush rather than being
        lost, and the exception is the caller's to count.
        """
        if not self._buffer:
            return None
        snapshot = self.table.append(self._buffer)
        self._buffer.clear()
        return snapshot.content_hash


def read_states(table: IcebergTable) -> dict[tuple[str, str], list[DerivativesState]]:
    """Every stored state by `(venue, symbol)`, sorted by event time, then ingest time."""
    rows = table.read()
    grouped: dict[tuple[str, str], list[DerivativesState]] = defaultdict(list)
    for row in rows.to_pylist():
        state = from_row(row)
        grouped[(state.meta.venue, state.meta.symbol)].append(state)
    for states in grouped.values():
        states.sort(key=lambda s: (s.meta.event_time_ns, s.meta.ingest_time_ns))
    return dict(grouped)
