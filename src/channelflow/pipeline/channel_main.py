"""Periodic pass that produces channels, signals and extrema from bars.

# @trace: REQ-WP-077
# @trace: REQ-INFRA-012
# @trace: REQ-WP-088
# @trace: REQ-INFRA-007

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
from collections import defaultdict
from collections.abc import Sequence

from channelflow.backtest import BacktestRunner
from channelflow.bars.models import Bar
from channelflow.bus import EventBus
from channelflow.connectors.venue import VENUE_REGISTRY
from channelflow.events import CandidateUpdated, ChannelFitted
from channelflow.features.flow_bars import flow_rows
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.lakehouse import catalog as open_catalog
from channelflow.notary import tables as notary_tables
from channelflow.notary.config import WorkerNotary, worker_notary_from_env
from channelflow.notary.context import build_context
from channelflow.notary.registrar import Registrar
from channelflow.pipeline.passes import run_passes
from channelflow.pipeline.replay import record_replay
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import bars as bars_table
from channelflow.tables import features as features_table
from channelflow.tables.features import latest_flow_times, write_flow
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


def make_runner() -> BacktestRunner:
    """The runner a series is replayed with.

    One function for the pass and for the config hash the notary binds records to
    ([[REQ-INFRA-007]]), so the configuration a record is bound to is the configuration that
    produced it. A fresh runner per series: the signal machine inside it holds state.
    """
    return BacktestRunner()


def run_series(
    table: IcebergTable,
    *,
    venue: str,
    symbol: str,
    target: Timeframe,
    registrar: Registrar | None = None,
    snapshot_id: int | None = None,
) -> tuple[int, int, int, int] | None:
    """One `(venue, symbol, timeframe)`: read bars, run record_replay.

    Returns tuple of (channel_snapshots, signals, confirmed_extrema, extremum_candidates)
    or None if no bars exist for this timeframe (logged and skipped).

    `snapshot_id` pins the bars read when the notary is attached: the dataset a record is bound to
    must be the dataset it was computed from, and the bars table gains a snapshot every few seconds.
    `registrar` subscribes to the events the replay already publishes; it changes nothing the replay
    writes.
    """
    bars = bars_table.read_bars(
        table, venue=venue, symbol=symbol, timeframe_ns=target.ns, snapshot_id=snapshot_id
    )
    if not bars:
        return None

    bus = EventBus() if registrar is not None else None
    runner: BacktestRunner | None = None
    if registrar is not None and bus is not None:
        bus.subscribe(ChannelFitted, registrar.snapshot_handler(venue, symbol, target.ns))
        bus.subscribe(CandidateUpdated, registrar.decision_handler())
        runner = make_runner()

    recording, _ = record_replay(
        bars=bars,
        catalog=table.catalog,
        venue=venue,
        symbol=symbol,
        timeframe_ns=target.ns,
        runner=runner,
        bus=bus,
    )
    return (
        recording.channel_snapshots,
        recording.signals,
        recording.confirmed_extrema,
        recording.extremum_candidates,
    )


def write_flow_features(catalog: Catalog, all_bars: Sequence[Bar]) -> int:
    """CVD and the trade-imbalance features, from the bars this pass already read ([[REQ-WP-088]]).

    Every `(venue, symbol, timeframe)` the bars table has, including the timeframes `resample`
    builds. The bars carry the aggressor split, so nothing is read twice and no trade is touched.
    One series failing is reported and does not stop the others, and none of it can stop the
    channel step that follows. Returns how many bars' worth of rows were written.
    """
    grouped: dict[tuple[str, str, int], list[Bar]] = defaultdict(list)
    for bar in all_bars:
        grouped[(bar.venue, bar.symbol, bar.timeframe_ns)].append(bar)

    try:
        table = features_table.features_table_for(catalog)
        latest = latest_flow_times(table)
    except Exception as cause:  # noqa: BLE001 -- the channel step must still run
        print(
            f"  flow: could not read the features table -- {type(cause).__name__}: {cause}",
            flush=True,
        )
        return 0

    written = 0
    for (venue, symbol, timeframe_ns), series_bars in sorted(grouped.items()):
        config = VENUE_REGISTRY.get(venue)
        try:
            written += write_flow(
                table,
                venue=venue,
                symbol=symbol,
                timeframe_ns=timeframe_ns,
                rows=flow_rows(
                    series_bars,
                    sequential_ids=config.sequential_trade_ids if config is not None else False,
                ),
                latest=latest,
            )
        except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
            print(
                f"  {venue} {symbol} {timeframe_ns // 60_000_000_000}m: flow step failed -- "
                f"{type(cause).__name__}: {cause}",
                flush=True,
            )
    print(f"  flow rows written for {written} bar(s)", flush=True)
    return written


def _attach_notary(
    catalog: Catalog, table: IcebergTable, notary: WorkerNotary, *, gap_threshold: int
) -> tuple[Registrar, int]:
    """Pin the bars snapshot and build the registrar for this pass.

    Returns the registrar and the pinned snapshot id. The context -- config hash, dataset reference,
    commit -- is built once, here, from the runner the pass will use.
    """
    pinned = table.current()
    if pinned is None:
        raise RuntimeError("the bars table has no snapshot to pin; there is nothing to notarize")
    context = build_context(
        make_runner(),
        gap_threshold=gap_threshold,
        dataset=(pinned.snapshot_id, pinned.content_hash),
        code_commit=notary.code_commit,
        code_dirty=notary.code_dirty,
    )
    records = notary_tables.records_table(catalog)
    registrar = Registrar(
        records_table=records,
        context=context,
        from_ns=notary.from_ns,
        registered=notary_tables.registered_ids(records),
    )
    return registrar, pinned.snapshot_id


def _flush_notary(registrar: Registrar, *, where: str) -> None:
    """Register what the last series produced; a failure is reported and never stops the pass."""
    try:
        registrar.flush()
    except Exception as cause:  # noqa: BLE001 -- the notary is never a reason a pass stops
        print(
            f"  notary: could not register {where} -- {type(cause).__name__}: {cause}", flush=True
        )


def run_pass(
    catalog: Catalog,
    *,
    targets: Sequence[Timeframe],
    notary: WorkerNotary | None = None,
    gap_threshold: int = 1,
) -> list[tuple[str, str, str, int, int, int, int]]:
    """One pass over every series the bars table has, for every configured target.

    The `(venue, symbol)` pairs are discovered from the bars table rather than
    configured a second time: a symbol list that could disagree with the bars
    table would eventually do so, and the series to produce are exactly the
    series that exist.

    With `notary` the pass reads one pinned bars snapshot throughout and registers each record it
    computes ([[REQ-INFRA-007]]); without it the pass is exactly what it was.

    Returns list of tuples:
    (venue, symbol, timeframe_token, snapshots, signals,
     confirmed_extrema, extremum_candidates)
    """
    table = bars_table.table_for(catalog)
    registrar: Registrar | None = None
    snapshot_id: int | None = None
    if notary is not None:
        try:
            registrar, snapshot_id = _attach_notary(
                catalog, table, notary, gap_threshold=gap_threshold
            )
        except Exception as cause:  # noqa: BLE001 -- the pass runs without the notary
            print(
                f"  notary: not attached this pass -- {type(cause).__name__}: {cause}", flush=True
            )
    # Discover all series from the bars table (any timeframe)
    all_bars = bars_table.read_bars(table, snapshot_id=snapshot_id)
    series = sorted({(bar.venue, bar.symbol) for bar in all_bars})

    write_flow_features(catalog, all_bars)

    results: list[tuple[str, str, str, int, int, int, int]] = []
    for venue, symbol in series:
        for target in targets:
            try:
                counts = run_series(
                    table,
                    venue=venue,
                    symbol=symbol,
                    target=target,
                    registrar=registrar,
                    snapshot_id=snapshot_id,
                )
            except Exception as cause:  # noqa: BLE001 -- one series must not end the pass
                print(
                    f"  {venue} {symbol} {target.token}: FAILED — {type(cause).__name__}: {cause}",
                    flush=True,
                )
                continue
            finally:
                if registrar is not None:
                    _flush_notary(registrar, where=f"{venue} {symbol} {target.token}")
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
    if registrar is not None and registrar.refused:
        print(
            f"  notary: refused {registrar.refused} record(s) that were not final: "
            f"{registrar.last_refusal}",
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
    notary = worker_notary_from_env(os.environ)

    return run_passes(
        "worker",
        lambda: run_pass(
            catalog, targets=targets, notary=notary, gap_threshold=settings.gap_threshold
        ),
        interval_seconds=interval,
    )


if __name__ == "__main__":
    raise SystemExit(main())
