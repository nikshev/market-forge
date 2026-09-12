"""PRD §18.12.4's `LiquidityChange`, as a canonical table.

# @trace: REQ-WP-053

The companion to `dex_swaps.py`: what entered and left a pool, rather than what
traded against it. Same reasons for living here, same reasons for its column
types.

**`liquidity_delta` keeps its sign and is stored as a string.** It is `int128`
on chain and a burn is negative, so neither `int64` nor an unsigned magnitude
describes it — the first overflows on the largest positions and the second
loses the only thing that distinguishes a mint from a burn.

**`event_type` is stored rather than derived from the sign.** A `collect` moves
no liquidity at all and would be indistinguishable from a zero-delta modify;
PRD §18.12.4's `kind` is its own field for that reason.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.domain import DexLiquidityEvent
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "dex_liquidity"

SCHEMA = Schema(
    columns=(
        Column(name="event_time_ns", type="timestamp_ns"),
        Column(name="chain_id", type="int64"),
        Column(name="block_number", type="int64"),
        Column(name="tx_hash", type="string"),
        Column(name="log_index", type="int64"),
        Column(name="venue", type="string"),
        Column(name="dex", type="string"),
        Column(name="pool", type="string"),
        Column(name="event_type", type="string"),
        Column(name="tick_lower", type="int64"),
        Column(name="tick_upper", type="int64"),
        Column(name="liquidity_delta", type="string"),
        Column(name="amount0", type="decimal"),
        Column(name="amount1", type="decimal"),
    ),
    event_time_column="event_time_ns",
)

ORDER = ("chain_id", "block_number", "tx_hash", "log_index")

_DECIMALS = SCHEMA.decimal_columns
_BIG_INTEGERS = ("liquidity_delta",)


def to_row(event: DexLiquidityEvent) -> dict[str, object]:
    return {
        "event_time_ns": event.meta.event_time_ns,
        "chain_id": event.chain.chain_id,
        "block_number": event.chain.block_number,
        "tx_hash": event.chain.tx_hash,
        "log_index": event.chain.log_index,
        "venue": event.meta.venue,
        "dex": event.dex,
        "pool": event.pool,
        "event_type": event.event_type,
        "tick_lower": event.tick_lower,
        "tick_upper": event.tick_upper,
        "liquidity_delta": str(event.liquidity_delta),
        "amount0": event.amount0,
        "amount1": event.amount1,
    }


def from_row(row: dict[str, object]) -> dict[str, object]:
    """A row with its decimals and its signed big integer restored."""
    restored: dict[str, object] = {}
    for name in SCHEMA.names:
        value = row[name]
        if value is None:
            restored[name] = None
        elif name in _DECIMALS:
            restored[name] = Decimal(str(value))
        elif name in _BIG_INTEGERS:
            restored[name] = int(str(value))
        else:
            restored[name] = value
    return restored


@dataclass
class DexLiquiditySink:
    """Collects liquidity changes and writes them in batches."""

    table: IcebergTable
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, event: DexLiquidityEvent) -> None:
        self._buffer.append(to_row(event))

    def extend(self, events: Sequence[DexLiquidityEvent]) -> None:
        for event in events:
            self(event)

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def flush(self) -> str | None:
        if not self._buffer:
            return None
        snapshot = self.table.append(self._buffer)
        self._buffer.clear()
        return snapshot.content_hash


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)
