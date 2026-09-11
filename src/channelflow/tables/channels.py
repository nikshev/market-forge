"""PRD §29.6's `channel_snapshots`, as a canonical table.

# @trace: REQ-STORE-002

    ## 29.6. `channel_snapshots`
    Immutable append-only.
    Important columns: as_of; model/version; lookback; lower/center/upper;
    slope; width; quality components; forecast arrays; source_max_event_time.

"Immutable append-only" is the plane's own property, so this table gets it for
free. The two §29.6 names that shaped the schema are **quality components** and
**forecast arrays**: both are containers, and a table that could only hold
scalars would need two child tables joined back on every read. The plane learned
`float_map`, `string_list` and `float_list` for exactly this.

`ChannelQuality.contributing` and `.unavailable` are stored as they are, not
collapsed into the submetric map. [[ADR-007]] carries them so a six-part score is
never silently compared against a later nine-part one, and dropping them here
would lose the distinction at the storage boundary.
"""

from __future__ import annotations

from channelflow.channels import ChannelQuality, ChannelSnapshot
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema
from channelflow.tables.rows import (
    as_float,
    as_float_map,
    as_float_tuple,
    as_int,
    as_str,
    as_str_tuple,
)

TABLE_NAME = "channel_snapshots"

#: The event-time column is `as_of_ns`: a snapshot is knowable at the instant it
#: describes, and `source_max_event_time_ns <= as_of_ns` is the model's own
#: invariant. Filtering on the source time would return a snapshot computed
#: later from data that was old, which is a different question.
SCHEMA = Schema(
    columns=(
        Column(name="as_of_ns", type="timestamp_ns"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="model_name", type="string"),
        Column(name="model_version", type="string"),
        Column(name="lookback", type="int64"),
        Column(name="center_now", type="float64"),
        Column(name="upper_now", type="float64"),
        Column(name="lower_now", type="float64"),
        Column(name="slope_normalized", type="float64"),
        Column(name="slope_log_per_bar", type="float64"),
        Column(name="width_pct", type="float64"),
        Column(name="forecast_horizons", type="float_list"),
        Column(name="quality_score", type="float64"),
        Column(name="quality_submetrics", type="float_map"),
        Column(name="quality_contributing", type="string_list"),
        Column(name="quality_unavailable", type="string_list"),
        Column(name="source_max_event_time_ns", type="int64"),
    ),
    event_time_column="as_of_ns",
)

ORDER = ("venue", "symbol", "timeframe_ns", "as_of_ns")


def to_row(
    snapshot: ChannelSnapshot, *, venue: str, symbol: str, timeframe_ns: int
) -> dict[str, object]:
    """One snapshot as a row.

    The series it belongs to is supplied: `ChannelSnapshot` does not carry
    venue, symbol or timeframe, because a fitter is handed a series and does not
    need to know which. The table does, so the caller says.
    """
    return {
        "as_of_ns": snapshot.as_of_ns,
        "venue": venue,
        "symbol": symbol,
        "timeframe_ns": timeframe_ns,
        "model_name": snapshot.model_name,
        "model_version": snapshot.model_version,
        "lookback": snapshot.lookback,
        "center_now": snapshot.center_now,
        "upper_now": snapshot.upper_now,
        "lower_now": snapshot.lower_now,
        "slope_normalized": snapshot.slope_normalized,
        "slope_log_per_bar": snapshot.slope_log_per_bar,
        "width_pct": snapshot.width_pct,
        "forecast_horizons": list(snapshot.forecast_horizons),
        "quality_score": snapshot.quality.score,
        "quality_submetrics": dict(snapshot.quality.submetrics),
        "quality_contributing": list(snapshot.quality.contributing),
        "quality_unavailable": list(snapshot.quality.unavailable),
        "source_max_event_time_ns": snapshot.source_max_event_time_ns,
    }


def from_row(row: dict[str, object]) -> ChannelSnapshot:
    return ChannelSnapshot(
        as_of_ns=as_int(row, "as_of_ns"),
        model_name=as_str(row, "model_name"),
        model_version=as_str(row, "model_version"),
        lookback=as_int(row, "lookback"),
        center_now=as_float(row, "center_now"),
        upper_now=as_float(row, "upper_now"),
        lower_now=as_float(row, "lower_now"),
        slope_normalized=as_float(row, "slope_normalized"),
        slope_log_per_bar=as_float(row, "slope_log_per_bar"),
        width_pct=as_float(row, "width_pct"),
        forecast_horizons=as_float_tuple(row, "forecast_horizons"),
        quality=ChannelQuality(
            score=as_float(row, "quality_score"),
            submetrics=as_float_map(row, "quality_submetrics"),
            contributing=as_str_tuple(row, "quality_contributing"),
            unavailable=as_str_tuple(row, "quality_unavailable"),
        ),
        source_max_event_time_ns=as_int(row, "source_max_event_time_ns"),
    )


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


def latest_at(
    table: IcebergTable, *, venue: str, symbol: str, timeframe_ns: int, at_ns: int
) -> ChannelSnapshot | None:
    """The newest snapshot at or before `at_ns` -- never a later one.

    The API's FR-017 lives here now as well as in the in-memory repository. A
    snapshot taken after the requested instant is exactly the hindsight PRD
    §27.5 exists to keep out of the view, and the storage read is the last place
    it could get in.
    """
    rows = [
        row
        for row in table.read(as_of_ns=at_ns).to_pylist()
        if row["venue"] == venue and row["symbol"] == symbol and row["timeframe_ns"] == timeframe_ns
    ]
    if not rows:
        return None
    return from_row(max(rows, key=lambda row: as_int(row, "as_of_ns")))
