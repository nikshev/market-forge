"""PRD §29.4's `bars`, as a canonical table.

# @trace: REQ-TBL-001

    ## 29.4. `bars`
    Order: `(venue, symbol, timeframe, open_time)`

This is the first of PRD §29.B's seventeen canonical tables to hold real domain
data, and it lives here rather than in either package it joins. The lakehouse
must not import domain code -- a row that had to be a `Bar` would tie the plane
to one subsystem -- and the bar builder must not import a storage backend, which
is PRD §29.0's rule and a test in `tests/unit/lakehouse/test_isolation.py`.

So the adapter is a third place, which is what §29.0 asks for in as many words:
"any backend-specific DDL must live behind migrations/adapters and must not leak
into signal/channel domain code".

**Only finalized bars are written.** `BarBuilder` calls `on_final` when a window
closes and never again for that window ([[ADR-005]]); a canonical table holding
an unfinalized bar would hold a row that is still going to change, which is the
repainting PRD §0.5 forbids one level below the domain.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.bars import Bar
from channelflow.lakehouse import Column, ObjectStore, Schema, Table

#: PRD §29.B's name for it.
TABLE_NAME = "bars"

#: Every field of `Bar`, in the model's own order.
#:
#: Prices and sizes are `decimal` rather than `float64`. A bar is money and
#: float64 cannot hold 0.1; a canonical table that rounded on the way in would
#: make every downstream figure wrong by an amount nobody could reconstruct.
#:
#: The event-time column is `close_time_ns`, not `open_time_ns`. A bar becomes
#: knowable when it closes, so a point-in-time read as of an instant inside a
#: window must not return that window -- which is exactly the look-ahead PRD
#: §12 and §35.4 are about, and `open_time_ns` would hand it over.
SCHEMA = Schema(
    columns=(
        Column(name="close_time_ns", type="timestamp_ns"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="open_time_ns", type="int64"),
        Column(name="open", type="decimal"),
        Column(name="high", type="decimal"),
        Column(name="low", type="decimal"),
        Column(name="close", type="decimal"),
        Column(name="volume_base", type="decimal"),
        Column(name="volume_quote", type="decimal"),
        Column(name="trade_count", type="int64"),
        Column(name="aggressive_buy_base", type="decimal"),
        Column(name="aggressive_sell_base", type="decimal"),
        Column(name="delta_base", type="decimal"),
        Column(name="vwap", type="decimal"),
        Column(name="high_time_ns", type="int64"),
        Column(name="low_time_ns", type="int64"),
        Column(name="first_trade_id", type="string"),
        Column(name="last_trade_id", type="string"),
    ),
    event_time_column="close_time_ns",
)

#: PRD §29.4's ordering key. A read returns rows in it, so two readers of one
#: snapshot see the same series in the same order.
ORDER = ("venue", "symbol", "timeframe_ns", "open_time_ns")

_DECIMALS = SCHEMA.decimal_columns


class UnfinalizedBar(ValueError):
    """A bar that may still change was offered to a canonical table."""


def to_row(bar: Bar) -> dict[str, object]:
    """One bar as a row. Refuses an unfinalized one.

    `is_final` is not a column: every row in this table is final, so a column
    holding `true` on every row would be a field nobody reads and a door left
    open. The refusal is what carries the meaning instead.
    """
    if not bar.is_final:
        raise UnfinalizedBar(
            f"{bar.venue} {bar.symbol} {bar.timeframe_ns}ns at {bar.open_time_ns} is not "
            "final; a canonical table holding a bar that may still change holds a row "
            "that will be rewritten, which is the repainting PRD section 0.5 forbids"
        )
    return {
        "close_time_ns": bar.close_time_ns,
        "venue": bar.venue,
        "symbol": bar.symbol,
        "timeframe_ns": bar.timeframe_ns,
        "open_time_ns": bar.open_time_ns,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume_base": bar.volume_base,
        "volume_quote": bar.volume_quote,
        "trade_count": bar.trade_count,
        "aggressive_buy_base": bar.aggressive_buy_base,
        "aggressive_sell_base": bar.aggressive_sell_base,
        "delta_base": bar.delta_base,
        "vwap": bar.vwap,
        "high_time_ns": bar.high_time_ns,
        "low_time_ns": bar.low_time_ns,
        "first_trade_id": bar.first_trade_id,
        "last_trade_id": bar.last_trade_id,
    }


def from_row(row: dict[str, object]) -> Bar:
    """A row back into a `Bar`, with its decimals restored.

    `is_final` comes back as `True` because that is the only kind of bar this
    table holds -- see `to_row`. Reconstructing it from a stored column would
    mean trusting a field that could say otherwise.
    """
    values: dict[str, object] = {
        name: (Decimal(str(row[name])) if name in _DECIMALS else row[name]) for name in SCHEMA.names
    }
    values["is_final"] = True
    return Bar(**values)  # type: ignore[arg-type]


@dataclass
class BarSink:
    """Collects finalized bars and writes them to the table in batches.

    Suitable as `BarBuilder.on_final` directly. It buffers rather than appending
    per bar because every append is a commit, and a commit per bar would make
    the snapshot chain as long as the series -- a table with a manifest per row
    is a table whose metadata is larger than its data.

    Nothing here flushes on a timer, because nothing here reads a clock. The
    caller flushes: at the end of a backfill, at the end of a replay, or when
    `pending` reaches whatever size it has decided on.
    """

    table: Table
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, bar: Bar) -> None:
        self._buffer.append(to_row(bar))

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def flush(self) -> str | None:
        """Commit what is buffered; return the new snapshot's content hash.

        `None` when there was nothing to write, rather than an empty commit: a
        snapshot identical to its parent under a new id would make every
        consumer keyed by snapshot see a change that did not happen.
        """
        if not self._buffer:
            return None
        snapshot = self.table.append(self._buffer)
        self._buffer.clear()
        return snapshot.content_hash


def table_for(store: ObjectStore) -> Table:
    return Table(name=TABLE_NAME, schema=SCHEMA, store=store)


def read_bars(
    table: Table,
    *,
    venue: str | None = None,
    symbol: str | None = None,
    timeframe_ns: int | None = None,
    as_of_ns: int | None = None,
    snapshot_id: int | None = None,
) -> list[Bar]:
    """Bars in PRD §29.4's order, optionally filtered and as of an instant.

    `as_of_ns` is the storage layer's point-in-time read on `close_time_ns`, so a
    bar whose window had not closed at that instant is not returned. Filtering
    afterwards in Python would be the same answer for a small table and the
    wrong shape for a large one; doing it here keeps one meaning of "as of".
    """
    rows = table.read(snapshot_id=snapshot_id, as_of_ns=as_of_ns).to_pylist()
    matched = [
        row
        for row in rows
        if (venue is None or row["venue"] == venue)
        and (symbol is None or row["symbol"] == symbol)
        and (timeframe_ns is None or row["timeframe_ns"] == timeframe_ns)
    ]
    matched.sort(key=lambda row: tuple(row[name] for name in ORDER))
    return [from_row(row) for row in matched]


def write_bars(table: Table, bars: Sequence[Bar]) -> str | None:
    """Write a batch directly, for a backfill that already has its bars."""
    sink = BarSink(table=table)
    for bar in bars:
        sink(bar)
    return sink.flush()
