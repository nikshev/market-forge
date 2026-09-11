"""A replay fills the canonical plane (REQ-PIPE-001)."""

from __future__ import annotations

import math
import uuid
from decimal import Decimal

import pytest

from channelflow.api import LakehouseRepository
from channelflow.backtest import BacktestRunner
from channelflow.bars import Bar
from channelflow.bus import EventBus
from channelflow.domain import EventMeta, TradeEvent
from channelflow.events import BarFinalized, CandidateUpdated, ChannelFitted
from channelflow.experiments import dataset_reference
from channelflow.lakehouse import Catalog
from channelflow.pipeline import (
    MixedSeries,
    Recording,
    record_bars,
    record_replay,
    watermark,
)
from channelflow.tables import bars as bars_table
from channelflow.tables import channels as channels_table
from channelflow.tables import signals as signals_table

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS
BASE_NS = 1_788_838_800_000_000_000


def trade(
    index: int, *, price: str = "100.0", size: str = "1.0", symbol: str = "BTCUSDT"
) -> TradeEvent:
    at = BASE_NS + index * SECOND_NS
    return TradeEvent(
        meta=EventMeta(
            source="binance-ws",
            venue="binance",
            market_type="spot",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=at,
            sequence=index,
        ),
        trade_id=f"t{index}",
        price=Decimal(price),
        qty_base=Decimal(size),
        notional_quote=Decimal(price) * Decimal(size),
        aggressor_side="buy" if index % 2 else "sell",
    )


def bar(index: int, close: float) -> Bar:
    open_ns = BASE_NS + index * MINUTE_NS
    price = Decimal(str(round(close, 8)))
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_ns,
        close_time_ns=open_ns + MINUTE_NS,
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price,
        volume_base=Decimal("1"),
        volume_quote=price,
        trade_count=1,
        aggressive_buy_base=Decimal("0.5"),
        aggressive_sell_base=Decimal("0.5"),
        delta_base=Decimal(0),
        vwap=price,
        high_time_ns=open_ns,
        low_time_ns=open_ns,
        first_trade_id=f"t{index}",
        last_trade_id=f"t{index}",
        is_final=True,
    )


def rising_with_rejections(n: int = 120) -> list[Bar]:
    """A series with enough shape to open candidates.

    A straight line fits a channel with no width and nothing ever touches a
    boundary, so a replay over one would write snapshots and no signals -- and a
    test asserting signals were written would be asserting about the fixture.
    """
    return [bar(index, 100.0 + 0.05 * index + 1.2 * math.sin(index / 5.0)) for index in range(n)]


@pytest.mark.trace("REQ-PIPE-001")
def test_trades_become_bars_in_the_table(catalog: Catalog) -> None:
    """The builder's own hook is the sink, so a recorded stream fills the table
    by the same path a live one would."""
    trades = [trade(index) for index in range(180)]

    recording = record_bars(trades, catalog=catalog, timeframe_ns=MINUTE_NS)

    assert recording.bars > 0
    stored = bars_table.read_bars(bars_table.table_for(catalog))
    assert len(stored) == recording.bars
    assert all(b.is_final for b in stored)


@pytest.mark.trace("REQ-PIPE-001")
def test_a_window_still_open_at_the_end_is_not_written(catalog: Catalog) -> None:
    """It is not a bar yet, and a table holding it would hold a row that is
    going to change."""
    trades = [trade(index) for index in range(180)]

    record_bars(trades, catalog=catalog, timeframe_ns=MINUTE_NS)

    stored = bars_table.read_bars(bars_table.table_for(catalog))
    last_trade_ns = trades[-1].meta.event_time_ns
    assert all(b.close_time_ns <= last_trade_ns for b in stored)


@pytest.mark.trace("REQ-PIPE-001")
def test_a_replay_writes_the_snapshots_it_fitted(catalog: Catalog) -> None:
    """The report is a summary; the snapshots themselves are what a later reader
    needs, and recomputing them outside the loop would be a second fitting path
    that could disagree with it."""
    recording, report = record_replay(
        rising_with_rejections(),
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert recording.channel_snapshots > 0
    assert recording.channel_snapshots == report.bars_replayed - report.bars_skipped_no_channel
    stored = channels_table.table_for(catalog).read().num_rows
    assert stored == recording.channel_snapshots


@pytest.mark.trace("REQ-PIPE-001")
def test_a_signal_is_written_once_in_its_final_state(catalog: Catalog) -> None:
    """`on_bar` returns the live candidate on every bar it is alive for, each a
    more complete version of the same signal.

    Writing each would put a row per bar in the table, every one a partial
    history of one signal -- and a reader counting signals would count bars.
    """
    recording, report = record_replay(
        rising_with_rejections(),
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert recording.signals == report.candidates_opened
    assert recording.signals > 0

    cores = signals_table.table_for(catalog)
    transitions = signals_table.transitions_table_for(catalog)
    stored = signals_table.read_signals(cores, transitions)
    assert len(stored) == recording.signals
    # Each signal's *whole* history, not a prefix of it. The report counts every
    # transition the run made, so the stored histories have to add up to it --
    # keeping the first state of each candidate instead of the last would catalog
    # one transition per signal and still look like a working recorder.
    assert sum(len(c.history) for c in stored) == len(report.transitions)
    assert max(len(c.history) for c in stored) > 1
    assert sum(len(c.history) for c in stored) == transitions.read().num_rows


@pytest.mark.trace("REQ-PIPE-001")
def test_the_observers_do_not_change_what_the_run_reports(
    catalog: Catalog,
) -> None:
    """They observe and cannot steer. A recorder that changed the report would
    make a recorded run a different run from an unrecorded one."""
    bars = rising_with_rejections()

    plain = BacktestRunner().run(bars)
    _, recorded = record_replay(
        bars, catalog=catalog, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )

    assert recorded == plain


@pytest.mark.trace("REQ-PIPE-001")
def test_the_caller_s_runner_comes_back_without_sinks(catalog: Catalog) -> None:
    """A runner that came back carrying recorders would write again on its next
    use, into whatever catalog the first run happened to use."""
    runner = BacktestRunner()

    record_replay(
        rising_with_rejections()[:30],
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        runner=runner,
    )

    assert runner.on_snapshot is None
    assert runner.on_candidate is None


@pytest.mark.trace("REQ-PIPE-001")
def test_a_replay_does_not_rewrite_its_own_input(catalog: Catalog) -> None:
    """Bars are the input. Writing them here would duplicate them for a replay
    over a table's own contents."""
    record_replay(
        rising_with_rejections()[:30],
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert bars_table.table_for(catalog).current() is None


@pytest.mark.trace("REQ-PIPE-001")
def test_the_recording_names_only_the_tables_it_wrote(catalog: Catalog) -> None:
    """A dataset naming a table nobody wrote to would claim the run read it."""
    recording, _ = record_replay(
        rising_with_rejections(),
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert "bars" not in recording.tables
    assert channels_table.TABLE_NAME in recording.tables
    assert recording.dataset == dataset_reference(recording.tables)


@pytest.mark.trace("REQ-PIPE-001")
def test_a_replay_that_produced_nothing_names_nothing(catalog: Catalog) -> None:
    """An empty input is not a dataset, and a reference over one would say a run
    could be reproduced from nothing."""
    recording, _ = record_replay(
        [], catalog=catalog, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )

    assert recording.channel_snapshots == 0
    assert recording.signals == 0
    assert not recording.has_dataset
    with pytest.raises(ValueError, match="no tables"):
        _ = recording.dataset


@pytest.mark.trace("REQ-PIPE-001")
def test_two_replays_of_one_series_write_the_same_dataset(catalog: Catalog) -> None:
    """Principle XI at the end of the pipeline. Two runs over the same bars
    produce the same rows, so they produce the same dataset identity -- which is
    what makes the identity worth citing."""
    bars = rising_with_rejections()
    first, _ = record_replay(
        bars,
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )
    second, _ = record_replay(
        bars,
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert first.dataset == second.dataset


@pytest.mark.trace("REQ-PIPE-001")
def test_the_api_serves_what_a_replay_recorded(catalog: Catalog) -> None:
    """The loop the storage requirements left open at both ends.

    Trades in, a replay over the bars they made, and the durable repository
    answering from what it wrote -- with nothing in memory between them.
    """
    record_bars([trade(index) for index in range(600)], catalog=catalog, timeframe_ns=MINUTE_NS)
    written = bars_table.read_bars(bars_table.table_for(catalog))
    record_replay(
        rising_with_rejections(),
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    repo = LakehouseRepository(catalog=catalog)

    assert repo.bars(venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS) == written
    assert (
        repo.channel_snapshot_at(
            venue="binance",
            symbol="BTCUSDT",
            timeframe_ns=MINUTE_NS,
            at_ns=BASE_NS + 200 * MINUTE_NS,
        )
        is not None
    )
    stored_signals = repo.signals(symbol="BTCUSDT")
    assert stored_signals
    assert repo.signal(uuid.UUID(int=0)) is None


@pytest.mark.trace("REQ-PIPE-001")
def test_a_recording_is_a_value_and_carries_its_counts() -> None:
    recording = Recording(bars=3, channel_snapshots=2, signals=1, tables={"bars": (1, "abc")})

    assert recording.has_dataset
    assert recording.dataset == dataset_reference({"bars": (1, "abc")})


# --- A run over input the tables already cover ------------------------------
#
# The plane is append-only. Nothing rejects a row that is already there, so a
# second run over the same input silently doubles the series and every reader
# -- the API, a dataset hash, a count -- reports the double as fact. These are
# the tests for the watermarks that stop it.


@pytest.mark.trace("REQ-PIPE-001")
def test_a_second_pass_over_the_same_trades_writes_no_bars(catalog: Catalog) -> None:
    """Append-only means nothing rejects the duplicate; the writer has to."""
    trades = [trade(index) for index in range(600)]

    first = record_bars(trades, catalog=catalog, timeframe_ns=MINUTE_NS)
    second = record_bars(trades, catalog=catalog, timeframe_ns=MINUTE_NS)

    assert first.bars > 0
    assert second.bars == 0
    assert second.skipped == first.bars
    assert bars_table.table_for(catalog).read().num_rows == first.bars


@pytest.mark.trace("REQ-PIPE-001")
def test_a_second_replay_over_the_same_bars_writes_nothing(catalog: Catalog) -> None:
    """Including the transitions.

    A duplicated signal is worse than a duplicated bar: its rows land in the
    child table too, and the join then hands one signal two histories -- so a
    reader gets a candidate whose transitions contradict each other rather than
    an obvious double.
    """
    bars = rising_with_rejections()
    cores = signals_table.table_for(catalog)
    transitions = signals_table.transitions_table_for(catalog)

    first, _ = record_replay(
        bars, catalog=catalog, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )
    after_first = (
        channels_table.table_for(catalog).read().num_rows,
        cores.read().num_rows,
        transitions.read().num_rows,
    )
    second, _ = record_replay(
        bars, catalog=catalog, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )

    assert second.channel_snapshots == 0
    assert second.signals == 0
    # Everything the first run wrote, now including the extrema [[REQ-WP-029]]
    # added. Enumerated rather than summed loosely: a term forgotten here would
    # make a run that skipped less than it should look correct.
    assert second.skipped == (
        first.channel_snapshots
        + first.signals
        + first.confirmed_extrema
        + first.extremum_candidates
    )
    assert (
        channels_table.table_for(catalog).read().num_rows,
        cores.read().num_rows,
        transitions.read().num_rows,
    ) == after_first
    stored = signals_table.read_signals(cores, transitions)
    assert len(stored) == first.signals


@pytest.mark.trace("REQ-PIPE-001")
def test_a_run_that_skipped_everything_still_names_its_dataset(
    catalog: Catalog,
) -> None:
    """What it would have written is already there, so those snapshots are
    exactly the dataset its input corresponds to -- and recovering a lost
    citation by re-running is the reason a no-op run is worth allowing at all."""
    bars = rising_with_rejections()

    first, _ = record_replay(
        bars, catalog=catalog, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )
    second, _ = record_replay(
        bars, catalog=catalog, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )

    assert second.has_dataset
    assert second.dataset == first.dataset


@pytest.mark.trace("REQ-PIPE-001")
def test_a_continued_series_writes_only_what_is_new(catalog: Catalog) -> None:
    """A feed resumed from an overlapping window is the ordinary case, and
    refusing the whole batch would lose the tail that is genuinely new."""
    trades = [trade(index) for index in range(600)]

    record_bars(trades[:300], catalog=catalog, timeframe_ns=MINUTE_NS)
    second = record_bars(trades, catalog=catalog, timeframe_ns=MINUTE_NS)

    whole = catalog
    record_bars(trades, catalog=whole, timeframe_ns=MINUTE_NS)

    assert second.bars > 0
    assert second.skipped > 0
    assert bars_table.read_bars(bars_table.table_for(catalog)) == bars_table.read_bars(
        bars_table.table_for(whole)
    )


@pytest.mark.trace("REQ-PIPE-001")
def test_one_symbol_s_history_does_not_hold_back_another(catalog: Catalog) -> None:
    """The watermark is per series. An unscoped one would refuse a symbol's
    first bar on the strength of another symbol's hundredth -- and the second
    symbol would simply never appear, with nothing raised."""
    record_bars([trade(index) for index in range(600)], catalog=catalog, timeframe_ns=MINUTE_NS)

    other = record_bars(
        [trade(index, symbol="ETHUSDT") for index in range(600)],
        catalog=catalog,
        timeframe_ns=MINUTE_NS,
    )

    assert other.bars > 0
    assert other.skipped == 0
    stored = bars_table.read_bars(bars_table.table_for(catalog), venue="binance", symbol="ETHUSDT")
    assert len(stored) == other.bars


@pytest.mark.trace("REQ-PIPE-001")
def test_trades_from_two_series_are_refused(catalog: Catalog) -> None:
    """One builder aggregates one series. Mixing two produces bars that belong
    to neither, and a watermark over the mixture is a watermark over nothing."""
    mixed = [trade(0), trade(1, symbol="ETHUSDT")]

    with pytest.raises(MixedSeries):
        record_bars(mixed, catalog=catalog, timeframe_ns=MINUTE_NS)


@pytest.mark.trace("REQ-PIPE-001")
def test_a_recording_does_not_name_a_table_another_series_filled(
    catalog: Catalog,
) -> None:
    """ "The table holds something" and "this run put something there" are the
    same question only on a fresh catalog.

    One catalog holds every series, so the channels table is full of BTCUSDT the
    moment BTCUSDT has been replayed -- and a recording for ETHUSDT that named
    it would hand a research run a dataset of somebody else's rows, carrying
    the hash of a real snapshot to make it look checked.
    """
    record_bars([trade(index) for index in range(600)], catalog=catalog, timeframe_ns=MINUTE_NS)
    record_replay(
        rising_with_rejections(),
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    recording, _ = record_replay(
        [], catalog=catalog, venue="binance", symbol="ETHUSDT", timeframe_ns=MINUTE_NS
    )

    assert bars_table.table_for(catalog).current() is not None
    assert channels_table.table_for(catalog).current() is not None
    assert not recording.has_dataset


@pytest.mark.trace("REQ-PIPE-001")
def test_a_watermark_for_an_unseen_series_is_absent_not_zero(catalog: Catalog) -> None:
    """Zero is a real instant. A table reporting it for a series it has never
    seen would refuse every event at or before the epoch."""
    table = bars_table.table_for(catalog)
    assert watermark(table, "close_time_ns", venue="binance", symbol="BTCUSDT") is None

    record_bars([trade(index) for index in range(600)], catalog=catalog, timeframe_ns=MINUTE_NS)

    assert watermark(table, "close_time_ns", venue="binance", symbol="ETHUSDT") is None
    seen = watermark(table, "close_time_ns", venue="binance", symbol="BTCUSDT")
    assert seen is not None
    assert seen == max(b.close_time_ns for b in bars_table.read_bars(table))


# --- the bus a caller can reach (REQ-INFRA-003) ------------------------------


@pytest.mark.trace("REQ-INFRA-003")
def test_a_caller_can_observe_a_replay_without_editing_it(
    catalog: Catalog,
) -> None:
    """The claim the abstraction is worth anything for.

    Before the bus, a second consumer of channel snapshots meant changing what
    `record_replay` constructs. It is now a subscription, and the test is that
    the caller writes no line inside this package.
    """
    seen: list[ChannelFitted] = []
    signals: list[CandidateUpdated] = []
    bus = EventBus()
    bus.subscribe(ChannelFitted, seen.append)
    bus.subscribe(CandidateUpdated, signals.append)

    recording, report = record_replay(
        rising_with_rejections(),
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        bus=bus,
    )

    stored = signals_table.read_signals(
        signals_table.table_for(catalog), signals_table.transitions_table_for(catalog)
    )

    assert len(seen) == recording.channel_snapshots
    # Every signal that reached the table was seen as an event first. The
    # subscriber sees more events than there are signals, deliberately: the
    # machine emits one per bar a candidate is alive for, which is why the
    # recorder keeps the latest rather than writing each.
    assert {event.candidate.opened_at_ns for event in signals} == {
        candidate.opened_at_ns for candidate in stored
    }
    assert len(signals) > len(stored)
    assert report.candidates_opened == recording.signals


@pytest.mark.trace("REQ-INFRA-003")
def test_an_observer_does_not_change_what_is_recorded(
    catalog: Catalog,
) -> None:
    """A subscriber is an observer. If adding one changed the recording, the bus
    would have turned a read into a write."""
    bars = rising_with_rejections()
    plain, _ = record_replay(
        bars,
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    bus = EventBus()
    bus.subscribe(ChannelFitted, lambda _: None)
    observed, _ = record_replay(
        bars,
        catalog=catalog,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        bus=bus,
    )

    assert observed.dataset == plain.dataset


@pytest.mark.trace("REQ-INFRA-003")
def test_a_caller_can_observe_finalized_bars(catalog: Catalog) -> None:
    """The same claim on the other producer."""
    seen: list[BarFinalized] = []
    bus = EventBus()
    bus.subscribe(BarFinalized, seen.append)

    recording = record_bars(
        [trade(index) for index in range(600)],
        catalog=catalog,
        timeframe_ns=MINUTE_NS,
        bus=bus,
    )

    assert len(seen) == recording.bars + recording.skipped
    assert all(event.bar.is_final for event in seen)
