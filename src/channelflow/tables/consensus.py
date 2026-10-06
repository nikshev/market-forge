"""The cross-venue consensus table: one row per (asset, market_type, bar close).

# @trace: REQ-WP-091

The consensus mid ([[REQ-WP-091]], PRD §17.1) is a median of the fresh top-of-book
mids of the venues that quote one asset, taken **at each bar's close** and stored
here so the chart can draw it as an optional layer. `bar_close_ns` is the event
time for the same reason the bars table keys on the close: a bar's consensus is
knowable only when the bar has closed, and it may be built from quotes whose
`ts_ns` is at or before that close and from no later one (Principle I -- no
look-ahead, even where a later quote would make the line prettier).

**Consensus is per market type.** One row belongs to exactly one `market_type`
(`spot` or `perp`): spot venues are taken together and perpetual venues are taken
together, never blended. A median over a spot mid and two perpetual mids would
fold the spot-perp basis into the thing called "consensus", and §17.1's
"normalized mids" does not ask for that; the viewed venue's basis
(`venue_basis_bps`) is therefore taken against the consensus of *its own* type.
One venue per type today means a type with a single contributor refuses rather
than publishing its own mid under a better name.

The row exists whether or not a consensus was reached, so a gap in the chart's
line carries its reason instead of being inferred from absence: `venue_count`
says how many venues contributed and `refusal_reason` says why there is no line
where fewer than two did. An empty `refusal_reason` means none -- the plane's
convention for an optional string (`tables/extrema.py`), not a null.

`consensus_mid` is `decimal`, not `float64`, for the reason every other price
column here gives: a price is money, and float64 cannot hold 0.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

TABLE_NAME = "consensus"

#: One row per (asset, market_type, bar close).
#:
#: `bar_close_ns` is typed `timestamp_ns` -- the storage vocabulary's name for
#: an event time, physically an int64 nanosecond count (`schema.py` maps it to
#: `pa.int64()`). The schema refuses any other type on the event-time column,
#: because a point-in-time filter compares nanosecond counts.
SCHEMA = Schema(
    columns=(
        Column(name="asset", type="string"),
        Column(name="market_type", type="string"),
        Column(name="bar_close_ns", type="timestamp_ns"),
        Column(name="consensus_mid", type="decimal"),
        Column(name="venue_count", type="int64"),
        Column(name="refusal_reason", type="string"),
    ),
    event_time_column="bar_close_ns",
)


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


@dataclass(frozen=True)
class Consensus:
    """One asset's consensus mid for one market type at one bar's close.

    `consensus_mid` is `None` where the consensus was refused (fewer than two
    venues contributed): the row still exists so its `refusal_reason` can say
    why the line is absent, and no price is written that a reader could mistake
    for one. `refusal_reason` is empty where there is no refusal.
    """

    asset: str
    market_type: Literal["spot", "perp"]
    bar_close_ns: int
    consensus_mid: Decimal | None
    venue_count: int
    refusal_reason: str = ""


def to_row(consensus: Consensus) -> dict[str, object]:
    """One consensus as a row, in the schema's own column order."""
    return {
        "asset": consensus.asset,
        "market_type": consensus.market_type,
        "bar_close_ns": consensus.bar_close_ns,
        "consensus_mid": consensus.consensus_mid,
        "venue_count": consensus.venue_count,
        "refusal_reason": consensus.refusal_reason,
    }
