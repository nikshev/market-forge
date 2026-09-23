"""Produce bars at every configured timeframe from the one-minute series.

# @trace: REQ-WP-073

The process half of `resample`: it reads the source series and what each target
already holds, calls the pure resampler, and appends through `BarSink`. This is
the only file in the feature that knows a loop and a catalog exist.

**One series failing does not end the pass.** The rule `maintenance_main`
already follows: the failure is printed, named, and the remaining series are
done. A pass that stopped at the first refusal would leave every later timeframe
unproduced for a reason that has nothing to do with them.
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Sequence

from channelflow.bars.models import Bar
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.lakehouse import catalog as open_catalog
from channelflow.pipeline.resample import ResampleReport, report_for, resample
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import bars as bars_table
from channelflow.timeframes import SOURCE_TOKEN, TIMEFRAMES, Timeframe, parse_list

#: The timeframes this deployment produces, comma-separated. `1m` is the source
#: the ingest daemon writes; listing it here is harmless but pointless, and the
#: `.env.example` comment says so.
TIMEFRAMES_ENV = "CHANNELFLOW_TIMEFRAMES"


def _interval_seconds(text: str) -> float:
    """`30m`, `6h`, `1d`, or a plain number of seconds.

    The same grammar `maintenance_main` gives `--loop`, deliberately: an
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
    source_timeframe: Timeframe,
    source_bars: Sequence[Bar],
    now_ns: int,
) -> ResampleReport:
    """One `(venue, symbol, timeframe)`: read what exists, resample, append."""
    existing = bars_table.read_bars(table, venue=venue, symbol=symbol, timeframe_ns=target.ns)
    result = resample(
        source_bars,
        target=target,
        source_timeframe=source_timeframe,
        already_present=frozenset(bar.open_time_ns for bar in existing),
        now_ns=now_ns,
    )
    sink = bars_table.BarSink(table=table)
    for bar in result.bars:
        sink(bar)
    written = sink.pending
    sink.flush()
    # `written` is what was buffered for the append that just happened, so a
    # report never counts a bar the commit refused.
    return report_for(result, venue=venue, symbol=symbol, timeframe=target, written=written)


def run_pass(
    catalog: Catalog,
    *,
    targets: Sequence[Timeframe],
    source: Timeframe,
    now_ns: int,
) -> list[ResampleReport]:
    """One pass over every series the source has, for every configured target.

    The `(venue, symbol)` pairs are discovered from the source rows rather than
    configured a second time: a symbol list that could disagree with the bars
    table would eventually do so, and the series to produce are exactly the
    series that exist.
    """
    table = bars_table.table_for(catalog)
    source_bars = bars_table.read_bars(table, timeframe_ns=source.ns)
    series = sorted({(bar.venue, bar.symbol) for bar in source_bars})

    reports: list[ResampleReport] = []
    for venue, symbol in series:
        owned = [bar for bar in source_bars if bar.venue == venue and bar.symbol == symbol]
        for target in targets:
            try:
                report = run_series(
                    table,
                    venue=venue,
                    symbol=symbol,
                    target=target,
                    source_timeframe=source,
                    source_bars=owned,
                    now_ns=now_ns,
                )
            except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
                print(
                    f"  {venue} {symbol} {target.token}: FAILED — {type(cause).__name__}: {cause}",
                    flush=True,
                )
                continue
            reports.append(report)
            print(f"  {report.line}", flush=True)
            for refusal in report.refusals:
                print(f"    refused: {refusal.reason}", flush=True)
    return reports


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
    source = TIMEFRAMES[SOURCE_TOKEN]

    settings = settings_from_env()
    catalog = open_catalog(
        uri=settings.catalog_uri, warehouse=settings.warehouse, **dict(settings.storage)
    )
    interval = _interval_seconds(arguments.loop) if arguments.loop else None

    while True:
        run_pass(catalog, targets=targets, source=source, now_ns=time.time_ns())
        if interval is None:
            return 0
        print(f"-- next pass in {interval:.0f}s", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
