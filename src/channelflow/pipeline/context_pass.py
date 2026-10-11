"""The worker's context-feature pass: open interest, funding (z) and basis at each bar's close.

# @trace: REQ-WP-093

Reads the collector's `derivatives_state` rows once and, for every series with bars, writes the
context features at every final bar's close ([[ADR-070]]: the worker is the only writer of
`feature_snapshots`). What each value is made of -- and what was knowable at the close -- lives in
`channelflow.features.context_values`; this is the table side of it.

**Each feature keeps its own watermark** (the latest close with a row for the series, timeframe and
feature) and the pass writes only after it: a second pass writes nothing, a feature that was absent
for a bar is looked at again next time, and the six flow features are never touched.

It lives in `pipeline/` and not in `features/`, with `write_flow_features`: `features/` is domain
code and may not reach for a storage backend (PRD §29.0, `tests/unit/lakehouse/test_isolation.py`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

import pyarrow as pa
import pyarrow.compute as pc

from channelflow.bars.models import Bar
from channelflow.context import sources
from channelflow.features.context_values import CONTEXT_FEATURES, StateIndex, context_values
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.tables import derivatives_state as state_table
from channelflow.tables import features as features_table


def latest_context_times(table: IcebergTable) -> dict[tuple[str, str, int, str], int]:
    """The close of the latest row on record for each series, timeframe and context feature.

    One read of the table, aggregated by arrow (ADR-056: a writer reads before it writes).
    """
    rows = table.read()
    if rows.num_rows == 0:
        return {}
    mine = rows.filter(pc.is_in(rows["feature_name"], value_set=_names_array()))
    if mine.num_rows == 0:
        return {}
    grouped = mine.group_by(["venue", "symbol", "timeframe_ns", "feature_name"]).aggregate(
        [("at_ns", "max")]
    )
    keys = zip(
        grouped["venue"].to_pylist(),
        grouped["symbol"].to_pylist(),
        grouped["timeframe_ns"].to_pylist(),
        grouped["feature_name"].to_pylist(),
        strict=True,
    )
    return {k: int(v) for k, v in zip(keys, grouped["at_ns_max"].to_pylist(), strict=True)}


def _names_array() -> pa.Array:
    return pa.array(CONTEXT_FEATURES)


def write_context_features(catalog: Catalog, all_bars: Sequence[Bar]) -> int:
    """Open interest, funding (z) and basis at every final bar's close; returns rows written.

    Every `(venue, symbol, timeframe)` the bars table has whose series is given a perpetual
    (`sources.perpetual_for`) and for which the collector has stored states. One series failing is
    reported and does not stop the others, and none of it can stop the channel step that follows.
    """
    grouped: dict[tuple[str, str, int], list[Bar]] = defaultdict(list)
    for bar in all_bars:
        if bar.is_final:
            grouped[(bar.venue, bar.symbol, bar.timeframe_ns)].append(bar)

    try:
        states = state_table.read_states(state_table.table_for(catalog))
        table = features_table.features_table_for(catalog)
        latest = latest_context_times(table)
    except Exception as cause:  # noqa: BLE001 -- the channel step must still run
        print(
            f"  context: could not read the tables -- {type(cause).__name__}: {cause}", flush=True
        )
        return 0

    indexes: dict[tuple[str, str], StateIndex] = {}
    written = 0
    for (venue, symbol, timeframe_ns), series_bars in sorted(grouped.items()):
        perpetual = sources.perpetual_for(venue, symbol)
        series_states = states.get((venue, perpetual)) if perpetual is not None else None
        if not series_states:
            continue
        try:
            index = indexes.setdefault((venue, symbol), StateIndex.of(series_states))
            rows: list[dict[str, object]] = []
            for bar in sorted(series_bars, key=lambda b: b.close_time_ns):
                close = bar.close_time_ns
                values = context_values(series_states, close_ns=close, index=index)
                fresh = {
                    name: value
                    for name, value in values.items()
                    if close > latest.get((venue, symbol, timeframe_ns, name), -1)
                }
                if fresh:
                    rows.extend(
                        features_table.feature_rows(
                            venue=venue,
                            symbol=symbol,
                            timeframe_ns=timeframe_ns,
                            at_ns=close,
                            values=fresh,
                        )
                    )
            if rows:
                table.append(rows)
                written += len(rows)
        except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
            print(
                f"  {venue} {symbol} {timeframe_ns // 60_000_000_000}m: context step failed -- "
                f"{type(cause).__name__}: {cause}",
                flush=True,
            )
    print(f"  context rows written: {written}", flush=True)
    return written
