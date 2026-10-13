"""A resample pass reads the bars table once and commits once (REQ-WP-104).

The pass used to read the whole table for every `(series, timeframe)` -- seventeen series at seven
timeframes is over a hundred reads of a table of hundreds of thousands of rows -- and commit a
snapshot for each series that had something to write. On 2026-10-13 that was the process holding
the host at 345 % CPU and the object store at 250 %, while a bars request from the API took 54 s.
What the pass computes is unchanged and is pinned here; what changes is how often it asks.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars.models import Bar
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.pipeline import resample_main
from channelflow.tables import bars as bars_table
from channelflow.timeframes import SOURCE_TOKEN, TIMEFRAMES

pytestmark = pytest.mark.trace("REQ-WP-104")

MINUTE_NS = 60_000_000_000
BASE_NS = 1_789_344_000_000_000_000  # 2026-09-14T00:00:00Z, a Monday
SOURCE = TIMEFRAMES[SOURCE_TOKEN]
NOW = BASE_NS + 10 * 24 * 60 * MINUTE_NS
TARGETS = [TIMEFRAMES["5m"], TIMEFRAMES["15m"]]


def minute(i: int, *, venue: str, symbol: str) -> Bar:
    start = BASE_NS + i * MINUTE_NS
    price = Decimal("100")
    return Bar(
        venue=venue,
        symbol=symbol,
        timeframe_ns=MINUTE_NS,
        open_time_ns=start,
        close_time_ns=start + MINUTE_NS,
        open=price,
        high=price,
        low=price,
        close=price,
        volume_base=Decimal("1"),
        volume_quote=Decimal("100"),
        trade_count=1,
        aggressive_buy_base=Decimal("1"),
        aggressive_sell_base=Decimal("0"),
        delta_base=Decimal("1"),
        vwap=price,
        high_time_ns=start,
        low_time_ns=start,
        first_trade_id="1",
        last_trade_id="1",
        is_final=True,
    )


SERIES = [("binance", "BTCUSDT"), ("bybit", "BTCUSDT"), ("okx", "BTC-USDT-SWAP")]


def seed(catalog: Catalog, count: int = 30) -> IcebergTable:
    table = bars_table.table_for(catalog)
    bars_table.write_bars(
        table, [minute(i, venue=v, symbol=s) for v, s in SERIES for i in range(count)]
    )
    return table


class Counting:
    """Counts reads and appends made against any table while it is installed."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.reads = 0
        self.appends = 0
        read, append = IcebergTable.read, IcebergTable.append

        def counted_read(table, *a, **k):  # type: ignore[no-untyped-def]
            self.reads += 1
            return read(table, *a, **k)

        def counted_append(table, *a, **k):  # type: ignore[no-untyped-def]
            self.appends += 1
            return append(table, *a, **k)

        monkeypatch.setattr(IcebergTable, "read", counted_read)
        monkeypatch.setattr(IcebergTable, "append", counted_append)


def run(catalog: Catalog):  # type: ignore[no-untyped-def]
    return resample_main.run_pass(catalog, targets=TARGETS, source=SOURCE, now_ns=NOW)


def test_the_table_is_read_once_whatever_the_number_of_series_and_timeframes(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(catalog)
    counting = Counting(monkeypatch)

    run(catalog)

    assert counting.reads == 1, f"{counting.reads} reads for {len(SERIES) * len(TARGETS)} series"


def test_everything_the_pass_writes_is_one_commit(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(catalog)
    counting = Counting(monkeypatch)

    reports = run(catalog)

    assert sum(r.written for r in reports) > 0
    assert counting.appends == 1


def test_a_pass_with_nothing_to_write_commits_nothing(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(catalog)
    run(catalog)
    counting = Counting(monkeypatch)

    reports = run(catalog)

    assert counting.appends == 0
    assert all(r.written == 0 for r in reports)
    assert counting.reads == 1


def test_it_produces_what_one_series_at_a_time_produced(catalog: Catalog) -> None:
    table = seed(catalog)

    reports = run(catalog)

    for venue, symbol in SERIES:
        five = bars_table.read_bars(
            table, venue=venue, symbol=symbol, timeframe_ns=TIMEFRAMES["5m"].ns
        )
        fifteen = bars_table.read_bars(
            table, venue=venue, symbol=symbol, timeframe_ns=TIMEFRAMES["15m"].ns
        )
        assert (len(five), len(fifteen)) == (6, 2), (venue, symbol)
    assert len(reports) == len(SERIES) * len(TARGETS)
    assert {r.written for r in reports} == {6, 2}


def test_a_second_pass_does_not_write_a_bar_twice(catalog: Catalog) -> None:
    table = seed(catalog)
    run(catalog)
    rows = table.read().num_rows

    run(catalog)

    assert table.read().num_rows == rows


def test_a_bar_that_the_table_already_holds_for_another_series_is_not_taken_for_this_ones(
    catalog: Catalog,
) -> None:
    table = bars_table.table_for(catalog)
    bars_table.write_bars(table, [minute(i, venue="binance", symbol="BTCUSDT") for i in range(15)])
    run(catalog)
    # A second series arrives later with the same minutes: its windows are not "already present".
    bars_table.write_bars(table, [minute(i, venue="bybit", symbol="BTCUSDT") for i in range(15)])

    run(catalog)

    mine = bars_table.read_bars(
        table, venue="bybit", symbol="BTCUSDT", timeframe_ns=TIMEFRAMES["5m"].ns
    )
    assert len(mine) == 3


def test_a_commit_that_fails_writes_nothing_says_so_and_the_next_pass_writes_it(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    table = seed(catalog)
    before = table.read().num_rows
    failing = {"on": True}
    real_flush = bars_table.BarSink.flush

    def flush(self):  # type: ignore[no-untyped-def]
        if failing["on"]:
            raise OSError("the object store said no")
        return real_flush(self)

    monkeypatch.setattr(bars_table.BarSink, "flush", flush)

    reports = run(catalog)

    assert table.read().num_rows == before
    assert all(r.written == 0 for r in reports), "a report must not count a bar the commit refused"
    assert "FAILED" in capsys.readouterr().out

    failing["on"] = False
    run(catalog)
    assert table.read().num_rows > before


def test_one_series_that_cannot_be_resampled_does_not_stop_the_others(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    table = seed(catalog)
    real = resample_main.resample

    def resample(source, **kw):  # type: ignore[no-untyped-def]
        if source and source[0].venue == "bybit":
            raise ValueError("bad window")
        return real(source, **kw)

    monkeypatch.setattr(resample_main, "resample", resample)

    run(catalog)

    assert "bybit BTCUSDT 5m: FAILED" in capsys.readouterr().out
    assert bars_table.read_bars(
        table, venue="binance", symbol="BTCUSDT", timeframe_ns=TIMEFRAMES["5m"].ns
    )
    assert not bars_table.read_bars(
        table, venue="bybit", symbol="BTCUSDT", timeframe_ns=TIMEFRAMES["5m"].ns
    )


def test_an_empty_table_is_a_pass_that_does_nothing(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    counting = Counting(monkeypatch)

    assert run(catalog) == []
    assert counting.appends == 0


def test_a_timeframe_added_later_is_built_from_the_minutes_and_not_from_the_bars_already_resampled(
    catalog: Catalog,
) -> None:
    table = seed(catalog)
    resample_main.run_pass(catalog, targets=[TIMEFRAMES["5m"]], source=SOURCE, now_ns=NOW)

    resample_main.run_pass(catalog, targets=[TIMEFRAMES["15m"]], source=SOURCE, now_ns=NOW)

    for venue, symbol in SERIES:
        fifteen = bars_table.read_bars(
            table, venue=venue, symbol=symbol, timeframe_ns=TIMEFRAMES["15m"].ns
        )
        assert len(fifteen) == 2, (venue, symbol)
