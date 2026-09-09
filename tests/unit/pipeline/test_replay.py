"""A replay fills the canonical plane (REQ-PIPE-001)."""

from __future__ import annotations

import math
import uuid
from decimal import Decimal

import pytest

from channelflow.api import LakehouseRepository
from channelflow.backtest import BacktestRunner
from channelflow.bars import Bar
from channelflow.domain import EventMeta, TradeEvent
from channelflow.experiments import dataset_reference
from channelflow.lakehouse import InMemoryObjectStore
from channelflow.pipeline import Recording, record_bars, record_replay
from channelflow.tables import bars as bars_table
from channelflow.tables import channels as channels_table
from channelflow.tables import signals as signals_table

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS
BASE_NS = 1_788_838_800_000_000_000


def trade(index: int, *, price: str = "100.0", size: str = "1.0") -> TradeEvent:
    at = BASE_NS + index * SECOND_NS
    return TradeEvent(
        meta=EventMeta(
            source="binance-ws",
            venue="binance",
            market_type="spot",
            symbol="BTCUSDT",
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


@pytest.fixture
def store() -> InMemoryObjectStore:
    return InMemoryObjectStore()


@pytest.mark.trace("REQ-PIPE-001")
def test_trades_become_bars_in_the_table(store: InMemoryObjectStore) -> None:
    """The builder's own hook is the sink, so a recorded stream fills the table
    by the same path a live one would."""
    trades = [trade(index) for index in range(180)]

    recording = record_bars(trades, store=store, timeframe_ns=MINUTE_NS)

    assert recording.bars > 0
    stored = bars_table.read_bars(bars_table.table_for(store))
    assert len(stored) == recording.bars
    assert all(b.is_final for b in stored)


@pytest.mark.trace("REQ-PIPE-001")
def test_a_window_still_open_at_the_end_is_not_written(store: InMemoryObjectStore) -> None:
    """It is not a bar yet, and a table holding it would hold a row that is
    going to change."""
    trades = [trade(index) for index in range(180)]

    record_bars(trades, store=store, timeframe_ns=MINUTE_NS)

    stored = bars_table.read_bars(bars_table.table_for(store))
    last_trade_ns = trades[-1].meta.event_time_ns
    assert all(b.close_time_ns <= last_trade_ns for b in stored)


@pytest.mark.trace("REQ-PIPE-001")
def test_a_replay_writes_the_snapshots_it_fitted(store: InMemoryObjectStore) -> None:
    """The report is a summary; the snapshots themselves are what a later reader
    needs, and recomputing them outside the loop would be a second fitting path
    that could disagree with it."""
    recording, report = record_replay(
        rising_with_rejections(),
        store=store,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert recording.channel_snapshots > 0
    assert recording.channel_snapshots == report.bars_replayed - report.bars_skipped_no_channel
    stored = channels_table.table_for(store).read().num_rows
    assert stored == recording.channel_snapshots


@pytest.mark.trace("REQ-PIPE-001")
def test_a_signal_is_written_once_in_its_final_state(store: InMemoryObjectStore) -> None:
    """`on_bar` returns the live candidate on every bar it is alive for, each a
    more complete version of the same signal.

    Writing each would put a row per bar in the table, every one a partial
    history of one signal -- and a reader counting signals would count bars.
    """
    recording, report = record_replay(
        rising_with_rejections(),
        store=store,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert recording.signals == report.candidates_opened
    assert recording.signals > 0

    cores = signals_table.table_for(store)
    transitions = signals_table.transitions_table_for(store)
    stored = signals_table.read_signals(cores, transitions)
    assert len(stored) == recording.signals
    # Each signal's *whole* history, not a prefix of it. The report counts every
    # transition the run made, so the stored histories have to add up to it --
    # keeping the first state of each candidate instead of the last would store
    # one transition per signal and still look like a working recorder.
    assert sum(len(c.history) for c in stored) == len(report.transitions)
    assert max(len(c.history) for c in stored) > 1
    assert sum(len(c.history) for c in stored) == transitions.read().num_rows


@pytest.mark.trace("REQ-PIPE-001")
def test_the_observers_do_not_change_what_the_run_reports(
    store: InMemoryObjectStore,
) -> None:
    """They observe and cannot steer. A recorder that changed the report would
    make a recorded run a different run from an unrecorded one."""
    bars = rising_with_rejections()

    plain = BacktestRunner().run(bars)
    _, recorded = record_replay(
        bars, store=store, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )

    assert recorded == plain


@pytest.mark.trace("REQ-PIPE-001")
def test_the_caller_s_runner_comes_back_without_sinks(store: InMemoryObjectStore) -> None:
    """A runner that came back carrying recorders would write again on its next
    use, into whatever store the first run happened to use."""
    runner = BacktestRunner()

    record_replay(
        rising_with_rejections()[:30],
        store=store,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        runner=runner,
    )

    assert runner.on_snapshot is None
    assert runner.on_candidate is None


@pytest.mark.trace("REQ-PIPE-001")
def test_a_replay_does_not_rewrite_its_own_input(store: InMemoryObjectStore) -> None:
    """Bars are the input. Writing them here would duplicate them for a replay
    over a table's own contents."""
    record_replay(
        rising_with_rejections()[:30],
        store=store,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert bars_table.table_for(store).current() is None


@pytest.mark.trace("REQ-PIPE-001")
def test_the_recording_names_only_the_tables_it_wrote(store: InMemoryObjectStore) -> None:
    """A dataset naming a table nobody wrote to would claim the run read it."""
    recording, _ = record_replay(
        rising_with_rejections(),
        store=store,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert "bars" not in recording.tables
    assert channels_table.TABLE_NAME in recording.tables
    assert recording.dataset == dataset_reference(recording.tables)


@pytest.mark.trace("REQ-PIPE-001")
def test_a_replay_that_produced_nothing_names_nothing(store: InMemoryObjectStore) -> None:
    """An empty input is not a dataset, and a reference over one would say a run
    could be reproduced from nothing."""
    recording, _ = record_replay(
        [], store=store, venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS
    )

    assert recording.channel_snapshots == 0
    assert recording.signals == 0
    assert not recording.wrote_anything
    with pytest.raises(ValueError, match="no tables"):
        _ = recording.dataset


@pytest.mark.trace("REQ-PIPE-001")
def test_two_replays_of_one_series_write_the_same_dataset() -> None:
    """Principle XI at the end of the pipeline. Two runs over the same bars
    produce the same rows, so they produce the same dataset identity -- which is
    what makes the identity worth citing."""
    bars = rising_with_rejections()
    first, _ = record_replay(
        bars,
        store=InMemoryObjectStore(),
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )
    second, _ = record_replay(
        bars,
        store=InMemoryObjectStore(),
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    assert first.dataset == second.dataset


@pytest.mark.trace("REQ-PIPE-001")
def test_the_api_serves_what_a_replay_recorded(store: InMemoryObjectStore) -> None:
    """The loop the storage requirements left open at both ends.

    Trades in, a replay over the bars they made, and the durable repository
    answering from what it wrote -- with nothing in memory between them.
    """
    record_bars([trade(index) for index in range(600)], store=store, timeframe_ns=MINUTE_NS)
    written = bars_table.read_bars(bars_table.table_for(store))
    record_replay(
        rising_with_rejections(),
        store=store,
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
    )

    repo = LakehouseRepository(store=store)

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

    assert recording.wrote_anything
    assert recording.dataset == dataset_reference({"bars": (1, "abc")})
