"""Rewrite a table's small files into one, and say what it cost.

# @trace: REQ-WP-068

An append-only plane written a few rows at a time accumulates a file per commit.
[[REQ-WP-066]]'s daemon now commits every fifteen bars rather than every one, so
the rate is fifteen times lower -- and a rate is not a ceiling. A symbol at
one-minute bars still leaves about 96 files a day, and the read cost rises with
the count.

This is the operational half: scheduled maintenance, the way Iceberg deployments
do it. Measured on a live table of 717 files holding 721 rows: compaction took
7.2 seconds and the read that followed took **45ms, against 6478ms before**.

    .venv/bin/python -m tools.lakehouse.compact --table bars
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable

from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog
from channelflow.lakehouse.iceberg import IcebergTable
from channelflow.settings import settings_from_env
from channelflow.tables import (
    bars,
    channels,
    dex_depth,
    dex_liquidity,
    dex_state,
    dex_swaps,
    extrema,
    features,
    signals,
)

#: Every table a running deployment appends to, by its own factory. Named rather
#: than discovered, so compacting something is a decision somebody made -- and
#: spelled out one by one, because three of these modules hold more than one
#: table and a loop over `table_for` would silently skip the others.
TABLES: dict[str, Callable[[Catalog], IcebergTable]] = {
    "bars": bars.table_for,
    "channels": channels.table_for,
    "features": features.features_table_for,
    "markets": features.markets_table_for,
    "scores": features.scores_table_for,
    "contributions": features.contributions_table_for,
    "signals": signals.table_for,
    "transitions": signals.transitions_table_for,
    "confirmed_extrema": extrema.confirmed_table_for,
    "extremum_candidates": extrema.candidates_table_for,
    "dex_swaps": dex_swaps.table_for,
    "dex_liquidity": dex_liquidity.table_for,
    "dex_depth": dex_depth.table_for,
    "dex_state": dex_state.table_for,
}


def compact(table: IcebergTable) -> tuple[int, float]:
    """Compact one table. Returns the file count before, and the seconds taken."""
    started = time.perf_counter()
    before = table.compact()
    return before, time.perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", action="append", dest="tables", default=None)
    arguments = parser.parse_args(argv)

    unknown = [name for name in (arguments.tables or []) if name not in TABLES]
    if unknown:
        raise SystemExit(f"unknown table(s): {', '.join(unknown)}; known: {', '.join(TABLES)}")

    settings = settings_from_env(os.environ)
    catalog = open_catalog(
        uri=settings.catalog_uri, warehouse=settings.warehouse, **dict(settings.storage)
    )

    chosen = arguments.tables or list(TABLES)
    for name in chosen:
        table = TABLES[name](catalog)
        before, seconds = compact(table)
        if before <= 1:
            print(f"  {name}: {before} file(s), nothing to compact")
            continue
        print(f"  {name}: {before} file(s) rewritten in {seconds:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
