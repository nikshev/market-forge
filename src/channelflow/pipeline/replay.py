"""A replay that writes what it produced to the canonical plane.

# @trace: REQ-PIPE-001
# @trace: REQ-WP-029

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
from channelflow.bus import EventBus
from channelflow.domain import TradeEvent
from channelflow.events import (
    BarFinalized,
    CandidateUpdated,
    ChannelFitted,
    ExtremumConfirmed,
    ExtremumObserved,
)
from channelflow.experiments import dataset_reference
from channelflow.extrema import DirectionalChangeDetector
from channelflow.extrema.models import ConfirmedExtremum, ExtremumCandidate
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.signals import Candidate
from channelflow.tables import bars as bars_table
from channelflow.tables import channels as channels_table
from channelflow.tables import extrema as extrema_table
from channelflow.tables import signals as signals_table


class MixedSeries(ValueError):
    """One recording was handed trades from more than one series."""


def watermark(table: IcebergTable, column: str, **scope: object) -> int | None:
    """The latest event this table already holds for one series, or nothing.

    Scoped, because a table holds many series and a watermark over all of them
    would refuse a symbol's first bar on the strength of another symbol's
    hundredth.

    `None` for a series the table has never seen, which is a different fact from
    a watermark of zero: zero is a real instant, and a table that reported it
    for an empty series would refuse everything at or before the epoch.
    """
    latest: int | None = None
    for row in table.read().to_pylist():
        if any(row.get(key) != value for key, value in scope.items()):
            continue
        at = int(row[column])
        latest = at if latest is None else max(latest, at)
    return latest


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
    #: Turns detected over the replayed bars and written. [[REQ-WP-029]].
    confirmed_extrema: int = 0
    extremum_candidates: int = 0
    #: Rows the tables already covered, and which this replay therefore did not
    #: write. Counted rather than silent, for the reason `BarBuilder` counts its
    #: late trades: a re-run over overlapping input is a no-op and should look
    #: like one, and a number that stays at zero is a run that added something.
    skipped: int = 0
    #: IcebergTable name to the snapshot it was left at and that snapshot's content
    #: hash. Only the tables this run is answerable for -- wrote to, or skipped
    #: rows destined for. A table it neither wrote nor skipped is not part of
    #: what it produced, and naming it would put a stranger in the dataset.
    tables: dict[str, tuple[int, str]] = field(default_factory=dict)

    @property
    def dataset(self) -> str:
        """The dataset identity of everything this replay is answerable for."""
        return dataset_reference(self.tables)

    @property
    def has_dataset(self) -> bool:
        """Whether there is anything to cite.

        Not the same as "wrote something": a re-run that skipped every row is
        answerable for the rows already there, and citing them is the point of
        being able to re-run at all.
        """
        return bool(self.tables)


@dataclass
class ChannelRecorder:
    """Collects fitted snapshots and writes them in one batch.

    Suitable as `BacktestRunner.on_snapshot`. It buffers for the reason
    [[REQ-TBL-001]]'s bar sink does: every append is a commit, and a commit per
    bar would make the snapshot chain as long as the series.
    """

    table: IcebergTable
    venue: str
    symbol: str
    timeframe_ns: int
    #: The latest snapshot this series already has, read once. A snapshot at or
    #: before it is a duplicate: the plane is append-only, and writing one twice
    #: gives the series two snapshots for one instant.
    after_ns: int | None = None
    skipped: int = 0
    _buffer: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, event: ChannelFitted) -> None:
        snapshot = event.snapshot  # the bar is on the event; the snapshot carries `as_of_ns`
        if self.after_ns is not None and snapshot.as_of_ns <= self.after_ns:
            self.skipped += 1
            return
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

    core_table: IcebergTable
    transitions_table: IcebergTable
    #: The latest signal already on record for this series. One that opened at
    #: or before it is a duplicate -- and a duplicate signal is worse than a
    #: duplicate bar, because its transitions land in the child table too and
    #: the join then gives one signal two histories.
    after_ns: int | None = None
    skipped: int = 0
    _latest: dict[int, Candidate] = field(default_factory=dict)
    _skipped_ids: set[int] = field(default_factory=set)

    def __call__(self, event: CandidateUpdated) -> None:
        candidate = event.candidate
        if self.after_ns is not None and candidate.opened_at_ns <= self.after_ns:
            # Counted once per candidate, not once per bar it is alive for: the
            # skip is about the signal, and a per-bar count would report the
            # length of the series.
            if candidate.opened_at_ns not in self._skipped_ids:
                self._skipped_ids.add(candidate.opened_at_ns)
                self.skipped += 1
            return
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


@dataclass
class ExtremumRecorder:
    """Collects what the detector emitted and writes each kind in one batch.

    Suitable as a subscriber to `ExtremumConfirmed` and `ExtremumObserved`. It
    buffers for the reason every other recorder here does: every append is a
    commit, and a commit per turn would make the chain as long as the series.

    The watermarks are on **knowledge** -- `known_at_ns` and `observed_at_ns` --
    because that is what the tables are keyed by ([[REQ-WP-028]]) and what
    [[ADR-056]] asks a writer on an append-only plane to read before it writes.
    """

    confirmed_table: IcebergTable
    candidates_table: IcebergTable
    after_confirmed_ns: int | None = None
    after_observed_ns: int | None = None
    skipped: int = 0
    _confirmed: list[ConfirmedExtremum] = field(default_factory=list)
    _candidates: list[ExtremumCandidate] = field(default_factory=list)

    def on_confirmed(self, event: ExtremumConfirmed) -> None:
        if (
            self.after_confirmed_ns is not None
            and event.extremum.known_at_ns <= self.after_confirmed_ns
        ):
            self.skipped += 1
            return
        self._confirmed.append(event.extremum)

    def on_observed(self, event: ExtremumObserved) -> None:
        if (
            self.after_observed_ns is not None
            and event.candidate.observed_at_ns <= self.after_observed_ns
        ):
            self.skipped += 1
            return
        self._candidates.append(event.candidate)

    @property
    def pending_confirmed(self) -> int:
        return len(self._confirmed)

    @property
    def pending_candidates(self) -> int:
        return len(self._candidates)

    def flush(self) -> None:
        extrema_table.write_confirmed(self.confirmed_table, self._confirmed)
        extrema_table.write_candidates(self.candidates_table, self._candidates)
        self._confirmed.clear()
        self._candidates.clear()


def record_bars(
    trades: Sequence[TradeEvent],
    *,
    catalog: Catalog,
    timeframe_ns: int,
    bus: EventBus | None = None,
) -> Recording:
    """Aggregate trades into bars and write the ones the table does not have.

    The builder's own `on_final` hook is the sink, so a recorded stream fills the
    table by the same path a live one would -- Principle VII, without a second
    aggregation.

    Two kinds of bar are not written. One the builder has not finalized is not a
    bar yet, and a table holding it would hold a row that is going to change. One
    the table already covers would be a duplicate: the plane is append-only, so
    writing it again puts the same bar in the series twice and every reader
    counts it twice.
    """
    if not trades:
        return Recording(bars=0, channel_snapshots=0, signals=0)

    venues = {trade.meta.venue for trade in trades}
    symbols = {trade.meta.symbol for trade in trades}
    if len(venues) > 1 or len(symbols) > 1:
        raise MixedSeries(
            f"these trades span {len(venues)} venue(s) and {len(symbols)} symbol(s); "
            "a bar builder aggregates one series, and mixing two would produce bars "
            "that belong to neither"
        )
    venue, symbol = venues.pop(), symbols.pop()

    table = bars_table.table_for(catalog)
    already = watermark(
        table, "close_time_ns", venue=venue, symbol=symbol, timeframe_ns=timeframe_ns
    )

    # The builder is handed one publishing hook rather than the collector, so a
    # second consumer of finalized bars -- a metric, a live publisher -- is a
    # subscription instead of a change here.
    #
    # The bus is a parameter for the same reason. A bus this function kept to
    # itself would move the coupling rather than remove it: the caller still
    # could not observe a bar without editing this file, which is the cost the
    # abstraction exists to remove.
    bus = bus if bus is not None else EventBus()
    finalized: list[Bar] = []
    bus.subscribe(BarFinalized, lambda event: finalized.append(event.bar))

    builder = BarBuilder(
        timeframe_ns=timeframe_ns,
        on_final=lambda bar: bus.publish(BarFinalized(bar)),
    )
    for trade in trades:
        builder.add(trade)

    fresh = [bar for bar in finalized if already is None or bar.close_time_ns > already]
    if fresh:
        bars_table.write_bars(table, fresh)
    return _recording(
        bars=len(fresh),
        snapshots=0,
        signals=0,
        skipped=len(finalized) - len(fresh),
        accounted={bars_table.TABLE_NAME: (table, len(finalized))},
    )


def record_replay(
    bars: Sequence[Bar],
    *,
    catalog: Catalog,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    runner: BacktestRunner | None = None,
    bus: EventBus | None = None,
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
    channels = channels_table.table_for(catalog)
    signal_cores = signals_table.table_for(catalog)
    signal_transitions = signals_table.transitions_table_for(catalog)

    channel_recorder = ChannelRecorder(
        table=channels,
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        after_ns=watermark(
            channels, "as_of_ns", venue=venue, symbol=symbol, timeframe_ns=timeframe_ns
        ),
    )
    signal_recorder = SignalRecorder(
        core_table=signal_cores,
        transitions_table=signal_transitions,
        after_ns=watermark(
            signal_cores,
            "opened_at_ns",
            venue=venue,
            symbol=symbol,
            timeframe_ns=timeframe_ns,
        ),
    )

    # A caller's bus if there is one, so a consumer of channel snapshots or
    # signals subscribes rather than editing this function.
    bus = bus if bus is not None else EventBus()
    bus.subscribe(ChannelFitted, channel_recorder)
    bus.subscribe(CandidateUpdated, signal_recorder)

    instrument_id = f"{venue}:{symbol}"
    confirmed_table = extrema_table.confirmed_table_for(catalog)
    candidates_table = extrema_table.candidates_table_for(catalog)
    extremum_recorder = ExtremumRecorder(
        confirmed_table=confirmed_table,
        candidates_table=candidates_table,
        after_confirmed_ns=watermark(
            confirmed_table,
            "known_at_ns",
            instrument_id=instrument_id,
            timeframe_ns=timeframe_ns,
        ),
        after_observed_ns=watermark(
            candidates_table,
            "observed_at_ns",
            instrument_id=instrument_id,
            timeframe_ns=timeframe_ns,
        ),
    )
    bus.subscribe(ExtremumConfirmed, extremum_recorder.on_confirmed)
    bus.subscribe(ExtremumObserved, extremum_recorder.on_observed)

    base = runner or BacktestRunner()
    # A copy with the observers attached: the caller's runner is theirs, and a
    # runner that came back carrying sinks would write again on its next use.
    observed = BacktestRunner(
        channel=base.channel,
        machine=base.machine,
        family=base.family,
        on_snapshot=lambda bar, snapshot: bus.publish(ChannelFitted(bar, snapshot)),
        on_candidate=lambda candidate: bus.publish(CandidateUpdated(candidate)),
    )
    report = observed.run(list(bars))

    # The detector's own pass over the same bars. The runner owns its loop and
    # offers no per-bar hook, and adding one to feed a detector would change a
    # component with nothing to do with extrema. Principle VII is satisfied by
    # the *events* being identical to a live process's, not by the iteration
    # being shared.
    _detect(bars, bus=bus, instrument_id=instrument_id, venue=venue, timeframe_ns=timeframe_ns)

    snapshots_written = channel_recorder.pending
    signals_written = signal_recorder.pending
    confirmed_written = extremum_recorder.pending_confirmed
    candidates_written = extremum_recorder.pending_candidates
    channel_recorder.flush()
    signal_recorder.flush()
    extremum_recorder.flush()

    # Rows this replay is answerable for, written and skipped together. The
    # bars table is not among them at any count: this function reads it and
    # never writes it, and a dataset naming it would say the replay produced
    # its input.
    channel_rows = snapshots_written + channel_recorder.skipped
    signal_rows = signals_written + signal_recorder.skipped
    return (
        _recording(
            bars=0,
            snapshots=snapshots_written,
            signals=signals_written,
            confirmed_extrema=confirmed_written,
            extremum_candidates=candidates_written,
            skipped=channel_recorder.skipped + signal_recorder.skipped + extremum_recorder.skipped,
            accounted={
                channels_table.TABLE_NAME: (channels, channel_rows),
                signals_table.TABLE_NAME: (signal_cores, signal_rows),
                signals_table.TRANSITIONS_TABLE_NAME: (signal_transitions, signal_rows),
                extrema_table.CONFIRMED_TABLE_NAME: (
                    confirmed_table,
                    confirmed_written + extremum_recorder.skipped,
                ),
                extrema_table.CANDIDATES_TABLE_NAME: (
                    candidates_table,
                    candidates_written + extremum_recorder.skipped,
                ),
            },
        ),
        report,
    )


def _detect(
    bars: Sequence[Bar],
    *,
    bus: EventBus,
    instrument_id: str,
    venue: str,
    timeframe_ns: int,
) -> None:
    """Run the detector and publish what it emits, bar by bar.

    Per bar rather than in a batch at the end: a live process attaching the same
    subscribers has to see the same order, and a burst would be a second path
    that only a replay takes.

    The detector accumulates its candidates on a list of its own rather than
    calling back, so the new ones are noticed by their count. That reads a little
    awkwardly and is the honest shape: changing the detector to emit them is
    [[REQ-WP-019]]'s decision to make, not this caller's.
    """
    del timeframe_ns  # the detector reads it from the bars it is given
    detector = DirectionalChangeDetector(instrument_id=instrument_id, venue_scope=venue)
    published = 0
    for bar in bars:
        confirmation = detector.on_bar(bar)
        while published < len(detector.candidates):
            bus.publish(ExtremumObserved(detector.candidates[published]))
            published += 1
        if confirmation is not None:
            bus.publish(ExtremumConfirmed(confirmation))


def _recording(
    *,
    bars: int,
    snapshots: int,
    signals: int,
    confirmed_extrema: int = 0,
    extremum_candidates: int = 0,
    accounted: dict[str, tuple[IcebergTable, int]],
    skipped: int = 0,
) -> Recording:
    """Name each table this run is answerable for, and where it stands.

    Answerable for, not merely non-empty. A store is reused across runs -- that
    is what the watermarks above are for -- so "the table holds something" stops
    being the same question as "this run put something there" the moment a
    second run happens. A table left out of `accounted` at a count of zero is a
    table this run neither wrote nor skipped, and naming it would put another
    run's rows in this one's dataset.

    A run that skipped everything still names its tables. What it would have
    written is already there, so those snapshots are exactly the dataset its
    input corresponds to -- which is what makes a re-run worth doing to recover
    a citation.

    The `current is None` arm is unreachable from both callers here: a non-zero
    count means the run either appended to that table or skipped rows the table
    already held, and both leave it with a snapshot. It stays because it is what
    keeps the alternative from being a fabricated `(snapshot_id, hash)` pair --
    a dataset reference that looks checked -- if a third caller ever counts rows
    for a table it did not write. A mutation of it survives the suite, and
    should: it changes no behaviour any caller can reach.
    """
    referenced: dict[str, tuple[int, str]] = {}
    for name, (table, rows) in accounted.items():
        if rows == 0:
            continue
        current = table.current()
        if current is not None:
            referenced[name] = (current.snapshot_id, current.content_hash)
    return Recording(
        bars=bars,
        channel_snapshots=snapshots,
        signals=signals,
        confirmed_extrema=confirmed_extrema,
        extremum_candidates=extremum_candidates,
        skipped=skipped,
        tables=referenced,
    )
