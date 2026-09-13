"""PRD §18.12.1's `NormalizedSwap`, as a canonical table.

# @trace: REQ-WP-053

PRD §18.12 asks protocol adapters to emit "common **economic primitives**, not a
fake common state model", and §6.4 makes Iceberg the canonical analytical
history. The DeFi adapters have produced those primitives since [[REQ-WP-015]]
and nothing has stored them: the plane has been Iceberg since [[REQ-WP-039]] and
carried no DeFi table.

This lives here rather than in either package it joins, for the reason
`bars.py` gives: the lakehouse must not import domain code and the adapters must
not import a storage backend.

**Three of §18.12.1's fields are absent rather than null.** `available_at`,
`finality_status` and `fee_usd` have no producer today -- the first two live on
[[REQ-WP-014]]'s `ChainRecord` and are joined to a swap rather than carried by
one, and nothing computes the third. A column that is null on every row is a
promise nothing keeps, and a reader who found one would reasonably assume
somebody intended to fill it.

**`price_before` and `price_after` are likewise absent.** §18.12.1 marks both
nullable, and the v3 reducer emits the price the swap left behind rather than
the pair. Storing one of them under a name that implies both is worse than
storing neither.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.domain import DexSwapEvent
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "dex_swaps"

#: Amounts and prices are `decimal`, not `float64`, for the reason every other
#: canonical table in this project gives: a swap is money, and float64 cannot
#: hold 0.1.
#:
#: `amount0` and `amount1` keep their signs. §18.12.1 asks for `signed_flow`,
#: and the sign *is* the direction: negative is out of the pool. Storing
#: magnitudes and a side would be the same information in a shape that invites
#: somebody to sum it.
SCHEMA = Schema(
    columns=(
        Column(name="event_time_ns", type="timestamp_ns"),
        Column(name="chain_id", type="int64"),
        Column(name="block_number", type="int64"),
        Column(name="tx_hash", type="string"),
        # §18.7's canonical ordering is (block_number, transaction_index,
        # log_index). `ChainMeta` has carried it since [[REQ-WP-014]] and this
        # table did not, so the canonical order was not expressible from a
        # stored row ([[REQ-WP-062]]).
        Column(name="transaction_index", type="int64"),
        Column(name="log_index", type="int64"),
        Column(name="venue", type="string"),
        Column(name="dex", type="string"),
        Column(name="pool", type="string"),
        Column(name="token0", type="string"),
        Column(name="token1", type="string"),
        Column(name="amount0", type="decimal"),
        Column(name="amount1", type="decimal"),
        Column(name="price_token1_per_token0", type="decimal"),
        Column(name="notional_usd", type="decimal"),
        Column(name="sqrt_price_x96", type="string"),
        Column(name="tick", type="int64"),
        Column(name="liquidity", type="string"),
    ),
    event_time_column="event_time_ns",
)

#: PRD §11.2's identity for a DEX log, which is also the order two readers of
#: one snapshot see.
ORDER = ("chain_id", "pool", "block_number", "transaction_index", "log_index")

_DECIMALS = SCHEMA.decimal_columns

#: `sqrt_price_x96` and `liquidity` are stored as strings. Both are uint160 and
#: uint128 on chain and routinely exceed what int64 holds; a column that
#: overflowed silently would corrupt exactly the pools with the most liquidity.
_BIG_INTEGERS = ("sqrt_price_x96", "liquidity")


def to_row(swap: DexSwapEvent) -> dict[str, object]:
    """One swap as a row."""
    return {
        "event_time_ns": swap.meta.event_time_ns,
        "chain_id": swap.chain.chain_id,
        "block_number": swap.chain.block_number,
        "tx_hash": swap.chain.tx_hash,
        "transaction_index": swap.chain.tx_index,
        "log_index": swap.chain.log_index,
        "venue": swap.meta.venue,
        "dex": swap.dex,
        "pool": swap.pool,
        "token0": swap.token0,
        "token1": swap.token1,
        "amount0": swap.amount0,
        "amount1": swap.amount1,
        "price_token1_per_token0": swap.price_token1_per_token0,
        "notional_usd": swap.notional_usd,
        "sqrt_price_x96": None if swap.sqrt_price_x96 is None else str(swap.sqrt_price_x96),
        "tick": swap.tick,
        "liquidity": None if swap.liquidity is None else str(swap.liquidity),
    }


def from_row(row: dict[str, object]) -> dict[str, object]:
    """A row with its decimals and its big integers restored.

    Returns a mapping rather than a `DexSwapEvent`: rebuilding one needs an
    `EventMeta` and a `ChainMeta` whose other fields this table does not hold,
    and inventing them would be this module claiming to know where the swap came
    from.
    """
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
class DexSwapSink:
    """Collects swaps and writes them to the table in batches.

    Buffered rather than appending per swap, for `BarSink`'s reason: every
    append is a commit, and a commit per swap would make the snapshot chain as
    long as the series.

    Nothing here flushes on a timer, because nothing here reads a clock.
    """

    table: IcebergTable
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, swap: DexSwapEvent) -> None:
        self._buffer.append(to_row(swap))

    def extend(self, swaps: Sequence[DexSwapEvent]) -> None:
        for swap in swaps:
            self(swap)

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


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)
