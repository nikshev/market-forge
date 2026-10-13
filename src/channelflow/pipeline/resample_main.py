"""Produce bars at every configured timeframe from the one-minute series.

# @trace: REQ-WP-073
# @trace: REQ-INFRA-012
# @trace: REQ-WP-104

The process half of `resample`: it reads the bars table once, calls the pure resampler for each
series and target, and appends what they produced as one commit through `BarSink`. This is
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
from collections import defaultdict
from collections.abc import Sequence

from channelflow.bars.models import Bar
from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog
from channelflow.pipeline.passes import run_passes
from channelflow.pipeline.resample import ResampleReport, ResampleResult, report_for, resample
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

    **One read and one commit, however many series there are** ([[REQ-WP-104]]).
    The pass used to read the whole table for every `(series, timeframe)` --
    seventeen series at seven timeframes is over a hundred reads of a table of
    hundreds of thousands of rows -- and to commit a snapshot for each series with
    something to write. On 2026-10-13 that held the host at 345 % CPU and the
    object store at 250 % while the API took 54 s to answer a bars request. What
    each series resamples to is unchanged; the table is read once, what each
    target already holds is taken from that one read, and everything computed is
    appended as one commit. If that commit fails nothing was written, every report
    says so, and the next pass finds the same windows absent and writes them.
    """
    table = bars_table.table_for(catalog)
    everything = bars_table.read_bars(table)

    sources: dict[tuple[str, str], list[Bar]] = defaultdict(list)
    held: dict[tuple[str, str, int], set[int]] = defaultdict(set)
    for bar in everything:
        held[(bar.venue, bar.symbol, bar.timeframe_ns)].add(bar.open_time_ns)
        if bar.timeframe_ns == source.ns:
            sources[(bar.venue, bar.symbol)].append(bar)

    computed: list[tuple[ResampleResult, str, str, Timeframe]] = []
    for (venue, symbol), owned in sorted(sources.items()):
        for target in targets:
            try:
                result = resample(
                    owned,
                    target=target,
                    source_timeframe=source,
                    already_present=frozenset(held[(venue, symbol, target.ns)]),
                    now_ns=now_ns,
                )
            except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
                print(
                    f"  {venue} {symbol} {target.token}: FAILED — {type(cause).__name__}: {cause}",
                    flush=True,
                )
                continue
            computed.append((result, venue, symbol, target))

    sink = bars_table.BarSink(table=table)
    for result, _, _, _ in computed:
        for bar in result.bars:
            sink(bar)
    committed = True
    if sink.pending:
        try:
            sink.flush()
        except Exception as cause:  # noqa: BLE001 -- the next pass computes the same windows again
            committed = False
            print(
                f"  FAILED to commit {sink.pending} bar(s) -- {type(cause).__name__}: {cause}",
                flush=True,
            )

    reports: list[ResampleReport] = []
    for result, venue, symbol, target in computed:
        # What the commit took, never what was computed: a report that counted a bar the commit
        # refused would claim a row that does not exist.
        report = report_for(
            result,
            venue=venue,
            symbol=symbol,
            timeframe=target,
            written=len(result.bars) if committed else 0,
        )
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

    return run_passes(
        "resample",
        lambda: run_pass(catalog, targets=targets, source=source, now_ns=time.time_ns()),
        interval_seconds=interval,
    )


if __name__ == "__main__":
    raise SystemExit(main())
