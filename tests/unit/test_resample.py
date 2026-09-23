# @trace: REQ-WP-073
from decimal import Decimal

import pytest

from channelflow.bars.models import Bar
from channelflow.pipeline.resample import fold, resample
from channelflow.timeframes import TIMEFRAMES


def make_bar(
    open_time_ns: int,
    *,
    venue: str = "binance",
    symbol: str = "BTCUSDT",
    timeframe_ns: int = 60_000_000_000,
    open_: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    volume_base: str = "1",
    volume_quote: str = "100",
    trade_count: int = 10,
    aggressive_buy_base: str = "0.6",
    aggressive_sell_base: str = "0.4",
    vwap: str | None = None,
    high_time_ns: int | None = None,
    low_time_ns: int | None = None,
    first_trade_id: str = "1",
    last_trade_id: str = "10",
    is_final: bool = True,
) -> Bar:
    if vwap is None:
        vwap = str(
            (Decimal(volume_quote) / Decimal(volume_base))
            if Decimal(volume_base) > 0
            else Decimal(close)
        )
    if high_time_ns is None:
        high_time_ns = open_time_ns + 30_000_000_000
    if low_time_ns is None:
        low_time_ns = open_time_ns + 30_000_000_000
    return Bar(
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        open_time_ns=open_time_ns,
        close_time_ns=open_time_ns + timeframe_ns,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume_base=Decimal(volume_base),
        volume_quote=Decimal(volume_quote),
        trade_count=trade_count,
        aggressive_buy_base=Decimal(aggressive_buy_base),
        aggressive_sell_base=Decimal(aggressive_sell_base),
        delta_base=Decimal(aggressive_buy_base) - Decimal(aggressive_sell_base),
        vwap=Decimal(vwap),
        high_time_ns=high_time_ns,
        low_time_ns=low_time_ns,
        first_trade_id=first_trade_id,
        last_trade_id=last_trade_id,
        is_final=is_final,
    )


class TestFold:
    @pytest.mark.trace("REQ-WP-073")
    def test_fold_is_field_by_field_aggregation(self):
        # Five minutes that differ in every field. The high is in the third
        # minute, the low in the fourth -- an implementation reading only the
        # ends passes a lazier fixture and fails this one.
        base = 1_789_344_000_000_000_000
        minutes = [
            make_bar(
                base + 0,
                open_="100",
                high="101",
                low="99",
                close="100.5",
                volume_base="1",
                volume_quote="100",
                trade_count=10,
                aggressive_buy_base="0.6",
                aggressive_sell_base="0.4",
                first_trade_id="a",
                last_trade_id="j",
            ),
            make_bar(
                base + 60_000_000_000,
                open_="100.5",
                high="102",
                low="100",
                close="101",
                volume_base="2",
                volume_quote="201",
                trade_count=20,
                aggressive_buy_base="1.2",
                aggressive_sell_base="0.8",
                first_trade_id="k",
                last_trade_id="z",
            ),
            make_bar(
                base + 120_000_000_000,
                open_="101",
                high="110",
                low="100.5",
                close="109",
                volume_base="3",
                volume_quote="310",
                trade_count=30,
                aggressive_buy_base="2.0",
                aggressive_sell_base="1.0",
                first_trade_id="aa",
                last_trade_id="bb",
            ),
            make_bar(
                base + 180_000_000_000,
                open_="109",
                high="109.5",
                low="85",
                close="90",
                volume_base="4",
                volume_quote="400",
                trade_count=40,
                aggressive_buy_base="1.5",
                aggressive_sell_base="2.5",
                first_trade_id="cc",
                last_trade_id="dd",
            ),
            make_bar(
                base + 240_000_000_000,
                open_="90",
                high="95",
                low="89",
                close="94",
                volume_base="5",
                volume_quote="470",
                trade_count=50,
                aggressive_buy_base="3.0",
                aggressive_sell_base="2.0",
                first_trade_id="ee",
                last_trade_id="ff",
            ),
        ]
        target = TIMEFRAMES["5m"]
        result = fold(minutes, venue="binance", symbol="BTCUSDT", target=target)

        assert result.open == Decimal("100")  # first minute's open
        assert result.high == Decimal("110")  # from the third minute
        assert result.low == Decimal("85")  # from the fourth minute
        assert result.close == Decimal("94")  # last minute's close
        assert result.volume_base == Decimal("15")
        assert result.volume_quote == Decimal("1481")
        assert result.trade_count == 150
        assert result.aggressive_buy_base == Decimal("8.3")
        assert result.aggressive_sell_base == Decimal("6.7")

    @pytest.mark.trace("REQ-WP-073")
    def test_vwap_of_unequal_volumes_is_quote_over_base_not_mean_of_vwaps(self):
        base = 1_789_344_000_000_000_000
        minutes = [
            make_bar(base + 0, volume_base="1", volume_quote="100", vwap="100"),
            make_bar(base + 60_000_000_000, volume_base="1", volume_quote="100", vwap="100"),
            make_bar(base + 120_000_000_000, volume_base="10", volume_quote="2000", vwap="200"),
        ]
        target = TIMEFRAMES["5m"]
        result = fold(minutes, venue="binance", symbol="BTCUSDT", target=target)

        expected = Decimal("2200") / Decimal("12")
        mean_of_vwaps = (Decimal("100") + Decimal("100") + Decimal("200")) / Decimal("3")
        assert result.vwap == expected
        assert result.vwap != mean_of_vwaps  # so the test cannot pass by coincidence

    @pytest.mark.trace("REQ-WP-073")
    def test_vwap_falls_back_to_close_when_volume_base_is_zero(self):
        base = 1_789_344_000_000_000_000
        minutes = [
            make_bar(base + 0, volume_base="0", volume_quote="0", close="105", vwap="105"),
            make_bar(
                base + 60_000_000_000, volume_base="0", volume_quote="0", close="107", vwap="107"
            ),
        ]
        target = TIMEFRAMES["5m"]
        result = fold(minutes, venue="binance", symbol="BTCUSDT", target=target)

        assert result.vwap == Decimal("107")  # last minute's close

    @pytest.mark.trace("REQ-WP-073")
    def test_delta_base_is_summed_sides(self):
        base = 1_789_344_000_000_000_000
        minutes = [
            make_bar(base + 0, aggressive_buy_base="2", aggressive_sell_base="1"),
            make_bar(base + 60_000_000_000, aggressive_buy_base="3", aggressive_sell_base="5"),
        ]
        target = TIMEFRAMES["5m"]
        result = fold(minutes, venue="binance", symbol="BTCUSDT", target=target)

        assert result.delta_base == Decimal("5") - Decimal("6")

    @pytest.mark.trace("REQ-WP-073")
    def test_extreme_times_come_from_minutes_holding_them(self):
        base = 1_789_344_000_000_000_000
        high_time = base + 120_000_000_000 + 17_000_000_000
        low_time = base + 180_000_000_000 + 42_000_000_000
        minutes = [
            make_bar(base + 0, high="101", low="99"),
            make_bar(base + 60_000_000_000, high="102", low="100"),
            make_bar(base + 120_000_000_000, high="110", low="100.5", high_time_ns=high_time),
            make_bar(base + 180_000_000_000, high="109.5", low="85", low_time_ns=low_time),
            make_bar(base + 240_000_000_000, high="95", low="89"),
        ]
        target = TIMEFRAMES["5m"]
        result = fold(minutes, venue="binance", symbol="BTCUSDT", target=target)

        assert result.high_time_ns == high_time
        assert result.low_time_ns == low_time

    @pytest.mark.trace("REQ-WP-073")
    def test_folded_bar_carries_window_bounds_and_is_final(self):
        base = 1_789_344_000_000_000_000
        minutes = [make_bar(base + i * 60_000_000_000) for i in range(5)]
        target = TIMEFRAMES["5m"]
        result = fold(minutes, venue="binance", symbol="BTCUSDT", target=target)

        assert result.open_time_ns == base
        assert result.close_time_ns == base + target.ns
        assert result.timeframe_ns == target.ns
        assert result.is_final is True
        assert result.venue == "binance"
        assert result.symbol == "BTCUSDT"


class TestResample:
    @pytest.mark.trace("REQ-WP-073")
    def test_window_missing_one_minute_produces_refusal(self):
        base = 1_789_344_000_000_000_000
        minutes = [make_bar(base + i * 60_000_000_000) for i in [0, 1, 3, 4]]
        result = resample(
            minutes,
            target=TIMEFRAMES["5m"],
            source_timeframe=TIMEFRAMES["1m"],
            now_ns=base + 3_600_000_000_000,
        )
        assert result.bars == ()
        assert len(result.refusals) == 1
        refusal = result.refusals[0]
        assert refusal.open_time_ns == base
        assert refusal.expected == 5
        assert refusal.present == 4
        assert str(base) in refusal.reason

    @pytest.mark.trace("REQ-WP-073")
    def test_window_in_progress_produces_neither_bar_nor_refusal(self):
        base = 1_789_344_000_000_000_000
        minutes = [make_bar(base + i * 60_000_000_000) for i in range(5)]
        result = resample(
            minutes,
            target=TIMEFRAMES["5m"],
            source_timeframe=TIMEFRAMES["1m"],
            now_ns=base + 5 * 60_000_000_000 - 1,
        )
        assert result.bars == ()
        assert result.refusals == ()

    @pytest.mark.trace("REQ-WP-073")
    def test_shuffling_source_changes_nothing(self):
        base = 1_789_344_000_000_000_000
        minutes = [make_bar(base + i * 60_000_000_000, volume_base=str(i + 1)) for i in range(25)]
        shuffled = [
            minutes[i]
            for i in [
                24,
                3,
                17,
                0,
                9,
                12,
                5,
                21,
                1,
                19,
                8,
                2,
                15,
                6,
                22,
                11,
                4,
                23,
                13,
                7,
                20,
                10,
                18,
                14,
                16,
            ]
        ]
        now = base + 3_600_000_000_000
        first = resample(
            minutes, target=TIMEFRAMES["5m"], source_timeframe=TIMEFRAMES["1m"], now_ns=now
        )
        second = resample(
            shuffled, target=TIMEFRAMES["5m"], source_timeframe=TIMEFRAMES["1m"], now_ns=now
        )
        assert first.bars == second.bars
        assert first.refusals == second.refusals

    @pytest.mark.trace("REQ-WP-073")
    def test_empty_source_gives_empty_result(self):
        result = resample(
            [],
            target=TIMEFRAMES["5m"],
            source_timeframe=TIMEFRAMES["1m"],
            now_ns=1_789_344_000_000_000_000,
        )
        assert result.bars == ()
        assert result.refusals == ()
        assert result.skipped == 0

    @pytest.mark.trace("REQ-WP-073")
    def test_target_not_whole_multiple_raises(self):
        # 90s is 1.5 minutes, so its windows cannot tile a one-minute series
        from channelflow.timeframes import Timeframe

        ninety = Timeframe("90s", 90_000_000_000, 0)
        with pytest.raises(ValueError, match="whole multiple"):
            resample(
                [make_bar(0)],
                target=ninety,
                source_timeframe=TIMEFRAMES["1m"],
                now_ns=1_789_344_000_000_000_000,
            )

    @pytest.mark.trace("REQ-WP-073")
    def test_one_day_target_over_1440_minutes_opens_utc_midnight(self):
        base = 1_789_344_000_000_000_000  # 2026-09-14T00:00:00Z, UTC midnight
        minutes = [make_bar(base + i * 60_000_000_000) for i in range(1440)]
        result = resample(
            minutes,
            target=TIMEFRAMES["1d"],
            source_timeframe=TIMEFRAMES["1m"],
            now_ns=base + 86_400_000_000_000 + 1,
        )
        assert len(result.bars) == 1
        assert result.bars[0].open_time_ns == base
        assert result.bars[0].close_time_ns == base + 86_400_000_000_000


class TestIdempotence:
    @pytest.mark.trace("REQ-WP-073")
    def test_second_pass_skips_everything_already_present(self):
        base = 1_789_344_000_000_000_000
        minutes = [make_bar(base + i * 60_000_000_000) for i in range(15)]
        now = base + 3_600_000_000_000
        first = resample(
            minutes,
            target=TIMEFRAMES["5m"],
            source_timeframe=TIMEFRAMES["1m"],
            now_ns=now,
        )
        assert len(first.bars) == 3

        present = frozenset(bar.open_time_ns for bar in first.bars)
        second = resample(
            minutes,
            target=TIMEFRAMES["5m"],
            source_timeframe=TIMEFRAMES["1m"],
            already_present=present,
            now_ns=now,
        )
        assert second.bars == ()
        assert second.skipped == 3
        assert second.refusals == ()

    @pytest.mark.trace("REQ-WP-073")
    def test_incomplete_window_already_present_is_not_refused(self):
        base = 1_789_344_000_000_000_000
        minutes = [make_bar(base + i * 60_000_000_000) for i in [0, 1, 3, 4]]
        result = resample(
            minutes,
            target=TIMEFRAMES["5m"],
            source_timeframe=TIMEFRAMES["1m"],
            already_present=frozenset({base}),
            now_ns=base + 3_600_000_000_000,
        )
        assert result.bars == ()
        assert result.refusals == ()
        assert result.skipped == 1
