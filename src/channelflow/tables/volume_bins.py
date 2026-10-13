"""The price bins table: what the ingest collects for the volume profile.

# @trace: REQ-WP-089

One row per `(venue, symbol, block, bin)`. The event-time column is the block's **close**: a block
is knowable only when it has closed, so a point-in-time read as of an instant inside it must not
return it (the same rule the bars table follows, for the same reason). Volumes are `decimal`, not
`float64`: they are quantities of an asset, and a profile built from rows that rounded on the way
in would be wrong by an amount nobody could reconstruct.

Every row carries its `bin_width`. A symbol's width is configured or derived once, and a restart
with a different configuration must not silently mix two grids: the reader uses the latest width
and says how many rows it left out.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema
from channelflow.tables.rows import narrow
from channelflow.volume.bins import BinBlock

logger = logging.getLogger(__name__)

TABLE_NAME = "volume_bins"

SCHEMA = Schema(
    columns=(
        Column(name="close_time_ns", type="timestamp_ns"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="block_open_time_ns", type="int64"),
        Column(name="block_ns", type="int64"),
        Column(name="bin_width", type="decimal"),
        Column(name="bin_index", type="int64"),
        Column(name="buy_base", type="decimal"),
        Column(name="sell_base", type="decimal"),
        Column(name="unknown_base", type="decimal"),
        Column(name="trades", type="int64"),
    ),
    event_time_column="close_time_ns",
)


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


def to_rows(block: BinBlock) -> list[dict[str, object]]:
    return [
        {
            "close_time_ns": block.close_time_ns,
            "venue": block.venue,
            "symbol": block.symbol,
            "block_open_time_ns": block.block_open_time_ns,
            "block_ns": block.block_ns,
            "bin_width": block.bin_width,
            "bin_index": row.index,
            "buy_base": row.buy,
            "sell_base": row.sell,
            "unknown_base": row.unknown,
            "trades": row.trades,
        }
        for row in block.bins
    ]


@dataclass
class BinSink:
    """Collects closed blocks and writes them in batches; suitable as `PriceBinBuilder.on_final`.

    It buffers because every append is a commit, and a commit per block would make the snapshot
    chain as long as the series.
    The caller flushes, with the bars (the daemon's own cadence).
    """

    table: IcebergTable
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, block: BinBlock) -> None:
        self._buffer.extend(to_rows(block))

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def flush(self) -> str | None:
        """Commit what is buffered; return the snapshot's content hash, or `None` for nothing."""
        if not self._buffer:
            return None
        snapshot = self.table.append(self._buffer)
        self._buffer.clear()
        return snapshot.content_hash


@dataclass(frozen=True)
class StoredBin:
    block_open_time_ns: int
    block_ns: int
    bin_width: Decimal
    bin_index: int
    buy: Decimal
    sell: Decimal
    unknown: Decimal
    trades: int

    @property
    def close_time_ns(self) -> int:
        return self.block_open_time_ns + self.block_ns


@dataclass(frozen=True)
class BinsRead:
    """The rows of one width, how many rows of other widths were left out, and the instant they are
    as of."""

    rows: list[StoredBin]
    left_out_rows: int
    #: The close of the latest block read: the instant the rows are as of. `None` with no rows.
    as_of_ns: int | None = None


def select_bins(
    raw: list[dict[str, object]],
    *,
    venue: str,
    symbol: str,
    as_of_ns: int | None = None,
    window_ns: int | None = None,
    since_ns: int | None = None,
) -> BinsRead:
    """The blocks of one series closed in `(since, as_of]`, at the latest bin width among them.

    `as_of_ns` keeps only blocks closed at or before it (a block that had not closed is not knowable
    then). The effective instant is the close of the latest such block; with `window_ns` the window
    is `(effective - window, effective]`, which is how a profile as of an instant inside a block is
    a profile of the whole blocks before it. `since_ns` is exclusive: a block that closed exactly
    then belongs to the window before it. One function, so the table and the in-memory repository
    cannot disagree about it.
    """
    series = [
        row
        for row in raw
        if row["venue"] == venue
        and row["symbol"] == symbol
        and (as_of_ns is None or int(row["close_time_ns"]) <= as_of_ns)  # type: ignore[call-overload]
    ]
    if not series:
        return BinsRead(rows=[], left_out_rows=0)
    effective = max(int(row["close_time_ns"]) for row in series)  # type: ignore[call-overload]
    floor = effective - window_ns if window_ns is not None else since_ns
    matched = [row for row in series if floor is None or int(row["close_time_ns"]) > floor]  # type: ignore[call-overload]
    latest = max(matched, key=lambda r: (int(r["close_time_ns"]), int(r["bin_index"])))["bin_width"]  # type: ignore[call-overload]
    kept = [r for r in matched if r["bin_width"] == latest]
    stored = [
        StoredBin(
            block_open_time_ns=int(r["block_open_time_ns"]),  # type: ignore[call-overload]
            block_ns=int(r["block_ns"]),  # type: ignore[call-overload]
            bin_width=Decimal(r["bin_width"]),  # type: ignore[arg-type]
            bin_index=int(r["bin_index"]),  # type: ignore[call-overload]
            buy=Decimal(r["buy_base"]),  # type: ignore[arg-type]
            sell=Decimal(r["sell_base"]),  # type: ignore[arg-type]
            unknown=Decimal(r["unknown_base"]),  # type: ignore[arg-type]
            trades=int(r["trades"]),  # type: ignore[call-overload]
        )
        for r in kept
    ]
    stored.sort(key=lambda b: (b.block_open_time_ns, b.bin_index))
    return BinsRead(rows=stored, left_out_rows=len(matched) - len(kept), as_of_ns=effective)


def read_bins(
    table: IcebergTable,
    *,
    venue: str,
    symbol: str,
    as_of_ns: int | None = None,
    window_ns: int | None = None,
    since_ns: int | None = None,
) -> BinsRead:
    """`select_bins` over the table, with the storage layer's point-in-time read on the block's
    close."""
    # Narrowed on the columns before any row becomes a dict ([[REQ-WP-104]]): every series' bins
    # are in this table, and one profile is one series' window.
    return select_bins(
        narrow(table.read(as_of_ns=as_of_ns), venue=venue, symbol=symbol).to_pylist(),
        venue=venue,
        symbol=symbol,
        as_of_ns=as_of_ns,
        window_ns=window_ns,
        since_ns=since_ns,
    )
