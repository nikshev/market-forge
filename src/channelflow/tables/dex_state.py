"""PRD §18.12.2's `LiquidityState`, as a canonical table.

# @trace: REQ-WP-060
# @trace: REQ-WP-063

    venue / protocol / pool_id / reference_price / state_time / available_at /
    model_type / active_liquidity nullable / reserve_state nullable /
    invariant_state nullable / fee_state / finality_status /
    reconstruction_quality

**Two of §18.12.2's fields are absent rather than null**, for the reason
[[REQ-WP-053]] gave for the same two on `NormalizedSwap`: `available_at` and
`finality_status` live on [[REQ-WP-014]]'s `ChainRecord` and are joined to a
state rather than carried by one. A column null on every row is a promise
nothing keeps.

`reserve_state` and `invariant_state` are genuinely nullable and null here:
they belong to reserve-based and invariant-based models, and a concentrated-
liquidity pool has neither. `model_type` is what says which of the three a
reader should expect to find.

**Three columns §18.12.2 does not list are here, and carry their reason.** The
replayed range (`from_block`, `to_block`) and `implied_active_liquidity` are the
evidence for `reconstruction_quality`: the quality is derived from whether the
tick map accounts for the liquidity the pool reported, and a row that stated the
verdict without the two numbers behind it would have to be taken on trust. With
them, a reader can recompute it. A state with no block cannot be reconciled
against a contract at all, because §18.7.2's comparison only means anything at
the state's own block ([[REQ-WP-060]]).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.dex.pool import PoolState
from channelflow.dex.reconstruction import (
    Provenance,
    ReconstructionQuality,
    implied_active_liquidity,
)
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "dex_state"

#: Concentrated liquidity. §18.12.2's `model_type` distinguishes the three
#: families whose state shapes differ; the others reach this table with their
#: own value and their own populated column.
CONCENTRATED_LIQUIDITY = "concentrated_liquidity"

#: Liquidity is a `uint128` and exceeds `int64`, so it is stored as a string,
#: as [[REQ-WP-053]] stores swap amounts. The sign is kept: `implied` can be
#: negative on a map missing its lower ticks, and clamping it would erase the
#: evidence the column exists for.
SCHEMA = Schema(
    columns=(
        Column(name="state_time_ns", type="timestamp_ns"),
        Column(name="chain_id", type="int64"),
        Column(name="venue", type="string"),
        Column(name="protocol", type="string"),
        Column(name="pool", type="string"),
        Column(name="reference_price", type="decimal"),
        Column(name="model_type", type="string"),
        Column(name="active_liquidity", type="string"),
        Column(name="reserve_state", type="string"),
        Column(name="invariant_state", type="string"),
        Column(name="fee_state", type="int64"),
        Column(name="reconstruction_quality", type="string"),
        Column(name="implied_active_liquidity", type="string"),
        Column(name="initialized_ticks", type="int64"),
        Column(name="from_block", type="int64"),
        Column(name="to_block", type="int64"),
    ),
    event_time_column="state_time_ns",
)

ORDER = ("chain_id", "pool", "state_time_ns")

_DECIMALS = SCHEMA.decimal_columns


def to_row(
    state: PoolState,
    *,
    chain_id: int,
    venue: str,
    protocol: str,
    reference_price: Decimal,
    state_time_ns: int,
    quality: ReconstructionQuality,
    provenance: Provenance,
    model_type: str = CONCENTRATED_LIQUIDITY,
) -> dict[str, object]:
    """One reconstructed state as its row.

    `quality` is passed in rather than computed here: it depends on a
    reconciliation this table has no business performing, and a table that
    derived half of it would produce rows disagreeing with the adapter's own
    `quality()` on the same state.
    """
    return {
        "state_time_ns": state_time_ns,
        "chain_id": chain_id,
        "venue": venue,
        "protocol": protocol,
        "pool": state.address,
        "reference_price": reference_price,
        "model_type": model_type,
        "active_liquidity": str(int(state.active_liquidity)),
        # Null, not zero or an empty string: a concentrated-liquidity pool has
        # no reserves and no invariant, and §18.12.2 marks both nullable for
        # exactly that reason.
        "reserve_state": None,
        "invariant_state": None,
        "fee_state": state.fee_tier,
        "reconstruction_quality": str(quality),
        "implied_active_liquidity": str(int(implied_active_liquidity(state))),
        "initialized_ticks": len(state.initialized_ticks),
        "from_block": provenance.from_block,
        "to_block": provenance.to_block,
    }


def from_row(row: dict[str, object]) -> dict[str, object]:
    """A row with its decimals restored."""
    return {
        name: (
            None
            if row[name] is None
            else Decimal(str(row[name]))
            if name in _DECIMALS
            else row[name]
        )
        for name in SCHEMA.names
    }


@dataclass
class DexStateSink:
    """Collects reconstructed states and writes them in batches."""

    table: IcebergTable
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, row: dict[str, object]) -> None:
        self._buffer.append(row)

    def extend(self, rows: Sequence[dict[str, object]]) -> None:
        self._buffer.extend(rows)

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


@dataclass(frozen=True)
class PoolStateReading:
    """One stored state, as a reader gets it back.

    A read model rather than a `PoolState`: the row carries the pool, the
    instant and the grade that a rebuilt state does not, and those are what a
    reader came for. The two big integers come back as `int` -- they are stored
    as strings because a `uint128` does not fit an `int64`, and returning the
    string would push that decision onto every caller.
    """

    state_time_ns: int
    chain_id: int
    venue: str
    protocol: str
    pool: str
    reference_price: Decimal
    model_type: str
    active_liquidity: int
    reserve_state: str | None
    invariant_state: str | None
    fee_state: int
    reconstruction_quality: str
    implied_active_liquidity: int
    initialized_ticks: int
    from_block: int
    to_block: int


def read_states(
    table: IcebergTable,
    *,
    chain_id: int | None = None,
    pool: str | None = None,
    as_of_ns: int | None = None,
    snapshot_id: int | None = None,
) -> list[PoolStateReading]:
    """States in this table's order, optionally filtered and as of an instant.

    `as_of_ns` is the storage layer's point-in-time read on `state_time_ns`, for
    the reason `dex_depth.read_bands` gives: a pane on a historical chart that
    fetched the newest state would be the look-ahead Principle I forbids,
    arriving through the one door nobody guards.
    """
    rows = table.read(snapshot_id=snapshot_id, as_of_ns=as_of_ns).to_pylist()
    matched = [
        from_row(row)
        for row in rows
        if (chain_id is None or row["chain_id"] == chain_id)
        and (pool is None or row["pool"] == pool)
    ]
    matched.sort(key=lambda row: tuple(str(row[name]) for name in ORDER))
    return [
        PoolStateReading(
            **{
                **row,  # type: ignore[arg-type]
                "active_liquidity": int(str(row["active_liquidity"])),
                "implied_active_liquidity": int(str(row["implied_active_liquidity"])),
            }
        )
        for row in matched
    ]
