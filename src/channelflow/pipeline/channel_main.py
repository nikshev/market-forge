"""Periodic pass that produces channels, signals and extrema from bars.

# @trace: REQ-WP-077

The process half of `channel_production`: it reads the bars table for each
configured timeframe, calls `record_replay` (which already exists, is correct,
and is tested), and logs what was written. This is the only file in the feature
that knows a loop and a catalog exist.

**One series failing does not end the pass.** The rule `resample_main` already
follows: the failure is printed, named, and the remaining series are done. A
pass that stopped at the first refusal would leave every later timeframe
unproduced for a reason that has nothing to do with them.
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Sequence

from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.lakehouse import catalog as open_catalog
from channelflow.pipeline.replay import record_replay
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import bars as bars_table
from channelflow.timeframes import Timeframe, parse_list

#: The timeframes this deployment produces, comma-separated. `1m` is the source
#: the ingest daemon writes; listing it here is harmless but pointless, and the
#: `.env.example` comment says so.
TIMEFRAMES_ENV = "CHANNELFLOW_TIMEFRAMES"

#: How often the channel pass repeats. Same grammar as CHANNELFLOW_RESAMPLE_INTERVAL.
CHANNEL_INTERVAL_ENV = "CHANNELFLOW_CHANNEL_INTERVAL"


def _interval_seconds(text: str) -> float:
    """`30m`, `6h`, `1d`, or a plain number of seconds.

    The same grammar `resample_main` gives `--loop`, deliberately: an
    operator learns one spelling for "how often does a loop run".
    """
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if text and text[-1] in units:
        return float(text[:-1]) * units[text[-1]]
    return float(text)


def run_series(
    table: IcebergTable,
    *,
    venue: str,
    symbol: str,
    target: Timeframe,
) -> tuple[int, int, int, int] | None:
    """One `(venue, symbol, timeframe)`: read bars, run record_replay.

    Returns tuple of (channel_snapshots, signals, confirmed_extrema, extremum_candidates)
    or None if no bars exist for this timeframe (logged and skipped).
    """
    bars = bars_table.read_bars(table, venue=venue, symbol=symbol, timeframe_ns=target.ns)
    if not bars:
        return None

    recording, _ = record_replay(
        bars=bars,
        catalog=table.catalog,
        venue=venue,
        symbol=symbol,
        timeframe_ns=target.ns,
    )
    return (
        recording.channel_snapshots,
        recording.signals,
        recording.confirmed_extrema,
        recording.extremum_candidates,
    )


def run_pass(
    catalog: Catalog,
    *,
    targets: Sequence[Timeframe],
) -> list[tuple[str, str, str, int, int, int, int]]:
    """One pass over every series the bars table has, for every configured target.

    The `(venue, symbol)` pairs are discovered from the bars table rather than
    configured a second time: a symbol list that could disagree with the bars
    table would eventually do so, and the series to produce are exactly the
    series that exist.

    Returns list of tuples:
    (venue, symbol, timeframe_token, snapshots, signals,
     confirmed_extrema, extremum_candidates)
    """
    table = bars_table.table_for(catalog)
    # Discover all series from the bars table (any timeframe)
    all_bars = bars_table.read_bars(table)
    series = sorted({(bar.venue, bar.symbol) for bar in all_bars})

    results: list[tuple[str, str, str, int, int, int, int]] = []
    for venue, symbol in series:
        for target in targets:
            try:
                counts = run_series(
                    table,
                    venue=venue,
                    symbol=symbol,
                    target=target,
                )
            except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
                print(
                    f"  {venue} {symbol} {target.token}: FAILED — {type(cause).__name__}: {cause}",
                    flush=True,
                )
                continue
            if counts is None:
                print(
                    f"  {venue} {symbol} {target.token}: no bars — skipped",
                    flush=True,
                )
                continue
            snapshots, signals, confirmed, candidates = counts
            results.append((venue, symbol, target.token, snapshots, signals, confirmed, candidates))
            print(
                f"  {venue} {symbol} {target.token}: "
                f"channel snapshots: {snapshots}, "
                f"signals: {signals}, "
                f"confirmed extrema: {confirmed}, "
                f"extremum candidates: {candidates}",
                flush=True,
            )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="one pass and exit (the default)")
    mode.add_argument("--loop", default=None, metavar="5m", help="repeat every interval")
    arguments = parser.parse_args(argv)

    raw = os.environ.get(TIMEFRAMES_ENV, "").strip()
    if not raw:
        raise MissingConfiguration(
            f"{TIMEFRAMES_ENV} must name the timeframes to produce; a pass "
            "configured to produce nothing looks exactly like a quiet market"
        )
    targets = parse_list(raw)

    settings = settings_from_env()
    catalog = open_catalog(
        uri=settings.catalog_uri, warehouse=settings.warehouse, **dict(settings.storage)
    )
    interval = _interval_seconds(arguments.loop) if arguments.loop else None

    while True:
        run_pass(catalog, targets=targets)
        if interval is None:
            return 0
        print(f"-- next pass in {interval:.0f}s", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
