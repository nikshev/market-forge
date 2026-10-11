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

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Sequence

import pyarrow as pa
import pyarrow.compute as pc

from channelflow.bars.models import Bar
from channelflow.context import sources
from channelflow.features.book_values import BOOK_FEATURES, book_values
from channelflow.features.context_values import CONTEXT_FEATURES, StateIndex, context_values
from channelflow.features.liquidation_values import (
    LIQUIDATION_FEATURES,
    WINDOW_NS,
    liquidation_values,
)
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.tables import book_minutes as book_table
from channelflow.tables import derivatives_state as state_table
from channelflow.tables import features as features_table
from channelflow.tables import liquidations as liquidation_table


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
    return pa.array(CONTEXT_FEATURES + LIQUIDATION_FEATURES + BOOK_FEATURES)


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
        events, heartbeats = liquidation_table.read(liquidation_table.table_for(catalog))
        minutes = book_table.read_minutes(book_table.table_for(catalog))
        table = features_table.features_table_for(catalog)
        latest = latest_context_times(table)
    except Exception as cause:  # noqa: BLE001 -- the channel step must still run
        print(
            f"  context: could not read the tables -- {type(cause).__name__}: {cause}", flush=True
        )
        return 0

    indexes: dict[tuple[str, str], StateIndex] = {}
    event_times: dict[tuple[str, str], list[int]] = {}
    pending: list[dict[str, object]] = []
    book_times: dict[tuple[str, str], list[int]] = {}
    for (venue, symbol, timeframe_ns), series_bars in sorted(grouped.items()):
        ordered = sorted(series_bars, key=lambda b: b.close_time_ns)
        tf_minutes = timeframe_ns // 60_000_000_000

        # A book is of the series' OWN market -- Binance's series is spot, and its book is the
        # spot book -- so it is looked up by the series' own venue and symbol, never through the
        # perpetual the derivatives are shown from.
        series_minutes = minutes.get((venue, symbol))
        if series_minutes:
            try:
                times = book_times.setdefault(
                    (venue, symbol), [m.minute_close_ns for m in series_minutes]
                )
                for bar in ordered:
                    values = book_values(
                        series_minutes, close_ns=bar.close_time_ns, times=times, symbol=symbol
                    )
                    pending.extend(
                        _fresh_rows(latest, venue, symbol, timeframe_ns, bar.close_time_ns, values)
                    )
            except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
                _report(venue, symbol, tf_minutes, "book", cause)

        perpetual = sources.perpetual_for(venue, symbol)
        if perpetual is None:
            continue
        series_states = states.get((venue, perpetual))
        if series_states:
            try:
                index = indexes.setdefault((venue, symbol), StateIndex.of(series_states))
                for bar in ordered:
                    values = context_values(series_states, close_ns=bar.close_time_ns, index=index)
                    pending.extend(
                        _fresh_rows(latest, venue, symbol, timeframe_ns, bar.close_time_ns, values)
                    )
            except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
                _report(venue, symbol, tf_minutes, "context", cause)

        series_beats = heartbeats.get((venue, perpetual))
        if series_beats:
            try:
                series_events = events.get((venue, perpetual), [])
                times = event_times.setdefault(
                    (venue, symbol), [e.meta.event_time_ns for e in series_events]
                )
                for bar in ordered:
                    close = bar.close_time_ns
                    # Only the events that can be in the window: sorted by event time, so a slice.
                    lo, hi = bisect_right(times, close - WINDOW_NS), bisect_right(times, close)
                    values = liquidation_values(
                        series_events[lo:hi], series_beats, close_ns=close, symbol=symbol
                    )
                    pending.extend(_fresh_rows(latest, venue, symbol, timeframe_ns, close, values))
            except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
                _report(venue, symbol, tf_minutes, "liquidation", cause)
    # One commit for the whole pass, not one per series: every append is a snapshot, and thirty-five
    # of them to a table of millions of rows is minutes of commits for rows that were computed in
    # seconds (the first backfill found this out). The rows are recomputed from the watermark on
    # the next pass if the commit fails, so nothing is lost by it being one.
    written = 0
    if pending:
        try:
            table.append(pending)
            written = len(pending)
        except Exception as cause:  # noqa: BLE001 -- the channel step must still run
            print(
                f"  context: could not write {len(pending)} row(s) -- "
                f"{type(cause).__name__}: {cause}",
                flush=True,
            )
    print(f"  context rows written: {written}", flush=True)
    return written


def _fresh_rows(
    latest: dict[tuple[str, str, int, str], int],
    venue: str,
    symbol: str,
    timeframe_ns: int,
    close_ns: int,
    values: dict[str, float],
) -> list[dict[str, object]]:
    """The rows for a close that are past the watermark of their own feature."""
    fresh = {
        name: value
        for name, value in values.items()
        if close_ns > latest.get((venue, symbol, timeframe_ns, name), -1)
    }
    if not fresh:
        return []
    return features_table.feature_rows(
        venue=venue, symbol=symbol, timeframe_ns=timeframe_ns, at_ns=close_ns, values=fresh
    )


def _report(venue: str, symbol: str, minutes: int, step: str, cause: Exception) -> None:
    print(
        f"  {venue} {symbol} {minutes}m: {step} step failed -- {type(cause).__name__}: {cause}",
        flush=True,
    )
