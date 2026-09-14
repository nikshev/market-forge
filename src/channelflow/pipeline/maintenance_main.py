"""Maintain the canonical plane: prune metadata, compact, and expire.

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
    .venv/bin/python -m tools.lakehouse.compact --keep-days 90 --loop 6h

**Expiring is opt-in.** It is the one operation that destroys ([[ADR-062]]), and
an operator who wants a faster read is not necessarily asking to forget
anything. Without `--keep-days` this compacts and leaves every old file in
place, which is safe and costs storage.
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable

from channelflow.lakehouse import Catalog, maintenance
from channelflow.lakehouse import catalog as open_catalog
from channelflow.lakehouse.iceberg import IcebergTable
from channelflow.lakehouse.retention import RetentionPolicy
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


DAY_NS = 24 * 60 * 60 * 1_000_000_000


def _interval_seconds(text: str) -> float:
    """`30m`, `6h`, `1d`, or a plain number of seconds."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if text and text[-1] in units:
        return float(text[:-1]) * units[text[-1]]
    return float(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", action="append", dest="tables", default=None)
    parser.add_argument(
        "--keep-days",
        type=float,
        default=None,
        help="expire snapshots older than this. Omitted, nothing is expired.",
    )
    parser.add_argument(
        "--loop",
        default=None,
        help="repeat every interval (30m, 6h, 1d). Omitted, one pass and exit.",
    )
    arguments = parser.parse_args(argv)

    unknown = [name for name in (arguments.tables or []) if name not in TABLES]
    if unknown:
        raise SystemExit(f"unknown table(s): {', '.join(unknown)}; known: {', '.join(TABLES)}")

    settings = settings_from_env(os.environ)
    catalog = open_catalog(
        uri=settings.catalog_uri, warehouse=settings.warehouse, **dict(settings.storage)
    )

    chosen = arguments.tables or list(TABLES)
    policy = (
        RetentionPolicy(keep_ns=int(arguments.keep_days * DAY_NS))
        if arguments.keep_days is not None
        else None
    )
    interval = _interval_seconds(arguments.loop) if arguments.loop else None

    while True:
        for name in chosen:
            try:
                report = maintenance.run(TABLES[name](catalog), policy=policy)
            except Exception as cause:  # noqa: BLE001 -- one table must not end the pass
                print(f"  {name}: FAILED — {type(cause).__name__}: {cause}", flush=True)
                continue
            print(f"  {report.line}", flush=True)
        if interval is None:
            return 0
        print(f"-- next pass in {interval:.0f}s", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
