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


@dataclass(frozen=True)
class DepthBand:
    """One band of one side, as stored.

    A read model rather than a `DepthQuote`: the stored row carries the pool and
    the instant a quote does not, and rebuilding a quote would drop exactly the
    provenance a reader came for.
    """

    state_time_ns: int
    chain_id: int
    pool: str
    side: str
    target_bps: Decimal
    reachable: bool
    reached_bps: Decimal
    amount0: Decimal
    amount1: Decimal
    reference_price: Decimal
    ticks_crossed: int
    reason: str


def read_bands(
    table: IcebergTable,
    *,
    chain_id: int | None = None,
    pool: str | None = None,
    as_of_ns: int | None = None,
    snapshot_id: int | None = None,
) -> list[DepthBand]:
    """Bands in this table's order, optionally filtered and as of an instant.

    `as_of_ns` is the storage layer's point-in-time read on `state_time_ns`, so a
    curve computed after that instant is not returned. A depth overlay on a
    historical chart that fetched the latest curve would be the look-ahead
    Principle I forbids, arriving through the one door nobody guards.
    """
    rows = table.read(snapshot_id=snapshot_id, as_of_ns=as_of_ns).to_pylist()
    matched = [
        from_row(row)
        for row in rows
        if (chain_id is None or row["chain_id"] == chain_id)
        and (pool is None or row["pool"] == pool)
    ]
    matched.sort(key=lambda row: tuple(str(row[name]) for name in ORDER))
    return [DepthBand(**row) for row in matched]  # type: ignore[arg-type]


def latest_curve_at(
    table: IcebergTable, *, chain_id: int, pool: str, at_ns: int
) -> list[DepthBand]:
    """The most recent curve for a pool at or before an instant.

    One curve, not every curve: an overlay draws the state as it stood, and
    handing it the whole history would make the caller pick -- which is where a
    caller picks the newest and reintroduces the look-ahead this read exists to
    prevent.
    """
    bands = read_bands(table, chain_id=chain_id, pool=pool, as_of_ns=at_ns)
    if not bands:
        return []
    newest = max(band.state_time_ns for band in bands)
    return [band for band in bands if band.state_time_ns == newest]
