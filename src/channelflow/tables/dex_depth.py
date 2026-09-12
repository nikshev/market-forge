"""PRD §18.12.3's `ExecutableDepthCurve`, as a canonical table.

# @trace: REQ-WP-053

A depth curve is a curve, and a table holds rows -- so one row per pool, per
side, per basis-point band. §18.12.3's required bands are 5, 10, 25, 50, 100 and
200, "configurable by liquidity regime", so the band is a column rather than a
set of columns: a schema with one column per band would need a migration the
first time a regime wanted a different grid.

**`reachable` is a column and the most important one here.** [[ADR-036]]'s
distinction: when it is false the amounts describe *exhausting the known
liquidity*, not reaching the target. Both rows carry a notional and a band, and
without that flag the two are indistinguishable -- a pool too thin to move 100
bps would read as a pool where 100 bps is cheap, which is the more dangerous
direction of the two.

`reached_bps` is stored alongside `target_bps` for the same reason: on an
unreachable row it says how far the book actually went, and on a reachable one
the two agree.

**Both sides' costs stay in their own tokens.** `amount0` and `amount1` are what
the walk consumed; converting them to one currency at write time would bake in
the reference price and make the row unreadable at any other. The conversion is
`DepthCurve.cost_in_token1`'s job at read time, and it is where this project
already got it wrong once -- the first version compared token0 against token1
directly and reported every pool as asymmetric.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.dex.depth import DepthCurve
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "dex_depth"

SCHEMA = Schema(
    columns=(
        Column(name="state_time_ns", type="timestamp_ns"),
        Column(name="chain_id", type="int64"),
        Column(name="pool", type="string"),
        Column(name="side", type="string"),
        Column(name="target_bps", type="decimal"),
        Column(name="reachable", type="bool"),
        Column(name="reached_bps", type="decimal"),
        Column(name="amount0", type="decimal"),
        Column(name="amount1", type="decimal"),
        Column(name="reference_price", type="decimal"),
        Column(name="ticks_crossed", type="int64"),
        Column(name="reason", type="string"),
    ),
    event_time_column="state_time_ns",
)

#: A curve is read back band by band, and a reader wants both sides of one band
#: together rather than one side of every band.
ORDER = ("chain_id", "pool", "state_time_ns", "target_bps", "side")

_DECIMALS = SCHEMA.decimal_columns

UP = "up"
DOWN = "down"


def to_rows(
    curve: DepthCurve, *, chain_id: int, pool: str, state_time_ns: int
) -> list[dict[str, object]]:
    """One curve as its rows, both sides, one per band.

    The pool's identity and the state's time are arguments: a `DepthCurve` is
    the arithmetic's answer and does not know which pool it was asked about, and
    a table that inferred either would be inventing provenance.
    """
    rows: list[dict[str, object]] = []
    for side, quotes in ((UP, curve.up), (DOWN, curve.down)):
        for quote in quotes.values():
            rows.append(
                {
                    "state_time_ns": state_time_ns,
                    "chain_id": chain_id,
                    "pool": pool,
                    "side": side,
                    "target_bps": quote.target_bps,
                    "reachable": quote.reachable,
                    "reached_bps": quote.reached_bps,
                    "amount0": quote.amount0,
                    "amount1": quote.amount1,
                    "reference_price": curve.price,
                    "ticks_crossed": quote.ticks_crossed,
                    "reason": quote.reason,
                }
            )
    return rows


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
class DexDepthSink:
    """Collects depth curves and writes them in batches."""

    table: IcebergTable
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, curve: DepthCurve, *, chain_id: int, pool: str, state_time_ns: int) -> None:
        self._buffer.extend(
            to_rows(curve, chain_id=chain_id, pool=pool, state_time_ns=state_time_ns)
        )

    def extend(self, curves: Sequence[tuple[DepthCurve, int, str, int]]) -> None:
        for curve, chain_id, pool, state_time_ns in curves:
            self(curve, chain_id=chain_id, pool=pool, state_time_ns=state_time_ns)

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
