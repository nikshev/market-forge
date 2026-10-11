"""The worker pass writes the order-flow features beside the other two families (REQ-WP-095)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.context.minute_book import MinuteSummary
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.pipeline import context_pass as write
from channelflow.tables import book_minutes as book_table
from channelflow.tables import features as features_table
from channelflow.tables import quotes as quotes_table
from tests.unit.pipeline.test_context_pass import (
    HOUR,
    MINUTE,
    T0,
    binance_states,
    features_for,
    make_bar,
    store,
)

START = T0 + 1 * HOUR


def minute_summary(
    minute: int,
    *,
    venue: str = "binance",
    symbol: str = "BTCUSDT",
    ofi: str | None = "3",
    di: float | None = 0.25,
    frames: int = 100,
) -> MinuteSummary:
    return MinuteSummary(
        venue=venue,
        symbol=symbol,
        minute_close_ns=START + minute * MINUTE,
        frames=frames,
        observations=58 if frames else 0,
        ofi=None if ofi is None else Decimal(ofi),
        depth_imbalance_10=di,
        bid=Decimal(100),
        ask=Decimal(101),
        mid=Decimal("100.5"),
        quote_time_ns=START + minute * MINUTE - 1,
    )


def store_minutes(
    catalog: Catalog, summaries: list[MinuteSummary], market_type: str = "spot"
) -> None:
    sink = book_table.BookMinuteSink(book_table.table_for(catalog), quotes_table.table_for(catalog))
    for item in summaries:
        sink(item, ingest_time_ns=item.minute_close_ns + 1, market_type=market_type)
    sink.flush()


@pytest.mark.trace("REQ-WP-095")
def test_the_pass_writes_ofi_and_depth_imbalance_at_a_bars_close(catalog: Catalog) -> None:
    store_minutes(catalog, [minute_summary(m, ofi=str(m)) for m in range(25, 35)])

    written = write.write_context_features(catalog, [make_bar(30)])

    close = make_bar(
        30
    ).close_time_ns  # START + 31 min: the minute ending at 31 is the latest known
    got = features_for(catalog, "binance", "BTCUSDT", MINUTE)[close]
    assert got == {"ofi_1m": 31.0, "depth_imbalance_10": 0.25}
    assert written == 2


@pytest.mark.trace("REQ-WP-095")
def test_the_value_is_the_minute_that_ended_at_or_before_the_close_and_no_later_one(
    catalog: Catalog,
) -> None:
    close = make_bar(30).close_time_ns
    store_minutes(
        catalog,
        [
            minute_summary(29, ofi="29"),
            minute_summary(30, ofi="30"),
            minute_summary(31, ofi="31"),
            minute_summary(32, ofi="999"),
            minute_summary(33, ofi="888"),
        ],
    )
    assert close == START + 31 * MINUTE

    write.write_context_features(catalog, [make_bar(30)])

    assert features_for(catalog, "binance", "BTCUSDT", MINUTE)[close]["ofi_1m"] == 31.0


@pytest.mark.trace("REQ-WP-095")
def test_a_bar_with_no_book_minute_gets_no_book_feature(catalog: Catalog) -> None:
    store_minutes(catalog, [minute_summary(5)])
    assert write.write_context_features(catalog, [make_bar(30)]) == 0


@pytest.mark.trace("REQ-WP-095")
def test_a_zero_count_minute_writes_nothing(catalog: Catalog) -> None:
    store_minutes(catalog, [minute_summary(31, frames=0, ofi=None, di=None)])
    assert write.write_context_features(catalog, [make_bar(30)]) == 0


@pytest.mark.trace("REQ-WP-095")
def test_a_second_pass_writes_nothing_more(catalog: Catalog) -> None:
    store_minutes(catalog, [minute_summary(m) for m in range(25, 40)])
    bars = [make_bar(i) for i in range(28, 34)]
    write.write_context_features(catalog, bars)

    assert write.write_context_features(catalog, bars) == 0


@pytest.mark.trace("REQ-WP-095")
def test_a_series_is_given_its_own_markets_book_not_a_perpetuals(catalog: Catalog) -> None:
    """A Binance series is spot; the book stored under its own (venue, symbol) is the spot book."""
    store_minutes(catalog, [minute_summary(m) for m in range(25, 40)], market_type="spot")
    store_minutes(
        catalog,
        [minute_summary(m, venue="binance", symbol="BTCUSDT-PERP", ofi="7") for m in range(25, 40)],
    )

    write.write_context_features(catalog, [make_bar(30)])

    got = features_for(catalog, "binance", "BTCUSDT", MINUTE)[make_bar(30).close_time_ns]
    assert got["ofi_1m"] != 7.0


@pytest.mark.trace("REQ-WP-095")
def test_all_three_families_are_one_commit(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    store(catalog, binance_states())
    store_minutes(catalog, [minute_summary(m) for m in range(25, 40)])
    commits: list[int] = []
    original = IcebergTable.append

    def counting(self: IcebergTable, rows: object) -> object:
        if self.name == features_table.features_table_for(catalog).name:
            commits.append(len(rows))  # type: ignore[arg-type]
        return original(self, rows)  # type: ignore[arg-type]

    monkeypatch.setattr(IcebergTable, "append", counting)

    written = write.write_context_features(catalog, [make_bar(i) for i in range(30, 36)])

    assert commits == [written]
    got = features_for(catalog, "binance", "BTCUSDT", MINUTE)[make_bar(30).close_time_ns]
    assert {"open_interest_usd", "ofi_1m"} <= set(got)


@pytest.mark.trace("REQ-WP-095")
def test_one_series_failing_in_the_book_step_is_reported_and_the_others_go_on(
    catalog: Catalog, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from channelflow.features import book_values

    store_minutes(catalog, [minute_summary(m) for m in range(25, 40)])
    store_minutes(catalog, [minute_summary(m, symbol="ETHUSDT") for m in range(25, 40)])
    original = book_values.book_values

    def explode(minutes: list, *, close_ns: int, **kwargs: object) -> dict[str, float]:  # type: ignore[type-arg]
        if kwargs.get("symbol") == "ETHUSDT":
            raise RuntimeError("boom")
        return original(minutes, close_ns=close_ns, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(write, "book_values", explode)

    write.write_context_features(catalog, [make_bar(30, symbol="ETHUSDT"), make_bar(30)])

    assert features_for(catalog, "binance", "BTCUSDT", MINUTE)
    assert "ETHUSDT" in capsys.readouterr().out
