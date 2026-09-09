"""A replay that writes what it produced to the canonical plane.

# @trace: REQ-PIPE-001

[[REQ-STORE-001]] built the plane, [[REQ-TBL-001]] and [[REQ-STORE-002]] put
seven tables on it, and every one of them was empty. Each of those requirements
recorded the same open question in its own words -- nothing fills the tables --
and everything downstream waits on it: the durable repository has nothing to
serve, and a research run has no dataset to be reproducible from.

This is that missing half, and it is deliberately not a daemon. PRD §25.1's two
modes are live and replay; a replay over recorded input is the one that can be
tested, repeated, and pointed at a fixture. A live process attaching the same
sinks to a running connector is deployment work and adds nothing this cannot
already show.

**A signal is written once, in its final state.** `SignalMachine.on_bar` returns
the live candidate on every bar it is alive for, each time a more complete
version of the same frozen object. Writing each one would put a row per bar in
the table, every one of them a partial history of the same signal, and a reader
counting signals would count bars. The recorder keeps the latest per
`opened_at_ns` and writes at the end.

**The result names its own dataset.** What a replay wrote is exactly what a
research run over it should cite, so the recording carries the reference
[[REQ-REPRO-001]] wants -- which is the loop those two requirements left open at
both ends.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from channelflow.backtest import BacktestReport, BacktestRunner
from channelflow.bars import Bar, BarBuilder
from channelflow.channels import ChannelSnapshot
from channelflow.domain import TradeEvent
from channelflow.experiments import dataset_reference
from channelflow.lakehouse import ObjectStore, Table
from channelflow.signals import Candidate
from channelflow.tables import bars as bars_table
from channelflow.tables import channels as channels_table
from channelflow.tables import signals as signals_table


@dataclass(frozen=True)
class Recording:
    """What one replay wrote, and the name of what it wrote.

    `dataset` is the reference [[REQ-REPRO-001]] takes as the first of PRD §0
    item 13's four hashes. A research run that reads these tables cites it, and
    the citation stays true because the plane's snapshots are immutable.
    """

    bars: int
    channel_snapshots: int
    signals: int
    #: Table name to the snapshot it was left at and that snapshot's content
    #: hash. Only the tables this replay actually wrote to: a table it did not
    #: touch is not part of what it produced, and naming it would put a stranger
    #: in the dataset.
    tables: dict[str, tuple[int, str]]

    @property
    def dataset(self) -> str:
        """The dataset identity of everything this replay wrote."""
        return dataset_reference(self.tables)

    @property
    def wrote_anything(self) -> bool:
        return bool(self.tables)


@dataclass
class ChannelRecorder:
    """Collects fitted snapshots and writes them in one batch.

    Suitable as `BacktestRunner.on_snapshot`. It buffers for the reason
    [[REQ-TBL-001]]'s bar sink does: every append is a commit, and a commit per
    bar would make the snapshot chain as long as the series.
    """

    table: Table
    venue: str
    symbol: str
    timeframe_ns: int
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, bar: Bar, snapshot: ChannelSnapshot) -> None:
        del bar  # the snapshot carries its own `as_of_ns`
        self._buffer.append(
            channels_table.to_row(
                snapshot,
                venue=self.venue,
                symbol=self.symbol,
                timeframe_ns=self.timeframe_ns,
            )
        )

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def flush(self) -> str | None:
        if not self._buffer:
            return None
        snapshot = self.table.append(self._buffer)
        self._buffer.clear()
        return snapshot.content_hash


@dataclass
class SignalRecorder:
    """Keeps the latest state of every candidate, and writes each once.

    Suitable as `BacktestRunner.on_candidate`. Keyed by `opened_at_ns`, which is
    a sound identity because a candidate cannot reopen on the bar that closed one
    (REQ-WP-007's FR-018) -- and because the machine replaces a terminal
    candidate rather than extending it, so two candidates at one instant would
    be the same candidate.
    """

    core_table: Table
    transitions_table: Table
    _latest: dict[int, Candidate] = field(default_factory=dict)

    def __call__(self, candidate: Candidate) -> None:
        # Overwrites deliberately: each call carries a more complete version of
        # the same signal, and the last one is the whole of it.
        self._latest[candidate.opened_at_ns] = candidate

    @property
    def pending(self) -> int:
        return len(self._latest)

    def flush(self) -> str | None:
        if not self._latest:
            return None
        ordered = [self._latest[key] for key in sorted(self._latest)]
        signals_table.write_signals(self.core_table, self.transitions_table, ordered)
        current = self.core_table.current()
        self._latest.clear()
        return None if current is None else current.content_hash


def record_bars(
    trades: Sequence[TradeEvent], *, store: ObjectStore, timeframe_ns: int
) -> Recording:
    """Aggregate trades into bars and write the finalized ones.

    The builder's own `on_final` hook is the sink, so a recorded stream fills the
    table by the same path a live one would -- Principle VII, without a second
    aggregation.

    Only bars the builder finalized are written. One that is still open at the
    end of the input is not a bar yet, and a table holding it would hold a row
    that is going to change.
    """
    table = bars_table.table_for(store)
    sink = bars_table.BarSink(table=table)
    builder = BarBuilder(timeframe_ns=timeframe_ns, on_final=sink)
    for trade in trades:
        builder.add(trade)
    # The watermark is the last trade's event time, so whatever the grace period
    # still holds open stays open. Forcing it closed here would publish a bar
    # from a window that may still receive trades.
    written = sink.pending
    sink.flush()
    return _recording(bars=written, snapshots=0, signals=0, tables={"bars": table})


def record_replay(
    bars: Sequence[Bar],
    *,
    store: ObjectStore,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    runner: BacktestRunner | None = None,
) -> tuple[Recording, BacktestReport]:
    """Replay `bars` and write the channel snapshots and signals it produced.

    Returns the recording and the report, because they answer different
    questions: the report is what the run found, and the recording is what a
    later run can read. A caller that only wanted one of them would still want
    the other to exist.

    The bars are **not** written here. They are the input; writing them would
    make a replay over a table's own contents duplicate them, and `record_bars`
    is where they come from.
    """
    channels = channels_table.table_for(store)
    signal_cores = signals_table.table_for(store)
    signal_transitions = signals_table.transitions_table_for(store)

    channel_recorder = ChannelRecorder(
        table=channels, venue=venue, symbol=symbol, timeframe_ns=timeframe_ns
    )
    signal_recorder = SignalRecorder(core_table=signal_cores, transitions_table=signal_transitions)

    base = runner or BacktestRunner()
    # A copy with the observers attached: the caller's runner is theirs, and a
    # runner that came back carrying sinks would write again on its next use.
    observed = BacktestRunner(
        channel=base.channel,
        machine=base.machine,
        family=base.family,
        on_snapshot=channel_recorder,
        on_candidate=signal_recorder,
    )
    report = observed.run(list(bars))

    snapshots_written = channel_recorder.pending
    signals_written = signal_recorder.pending
    channel_recorder.flush()
    signal_recorder.flush()

    # Every table this replay could have touched, the bars it read from and
    # never writes included. `_recording` keeps the ones that actually hold
    # something, so the decision is made once against the store rather than
    # twice against a counter -- a counter and a table can disagree, and the
    # table is the one a reader will open.
    return (
        _recording(
            bars=0,
            snapshots=snapshots_written,
            signals=signals_written,
            tables={
                bars_table.TABLE_NAME: bars_table.table_for(store),
                channels_table.TABLE_NAME: channels,
                signals_table.TABLE_NAME: signal_cores,
                signals_table.TRANSITIONS_TABLE_NAME: signal_transitions,
            },
        ),
        report,
    )


def _recording(*, bars: int, snapshots: int, signals: int, tables: dict[str, Table]) -> Recording:
    """Name each table this replay left something in.

    A table with no snapshot is left out rather than referenced at zero: a
    dataset naming a table nobody wrote to would claim the run read it.
    """
    referenced: dict[str, tuple[int, str]] = {}
    for name, table in tables.items():
        current = table.current()
        if current is not None:
            referenced[name] = (current.snapshot_id, current.content_hash)
    return Recording(bars=bars, channel_snapshots=snapshots, signals=signals, tables=referenced)
