# @trace: REQ-WP-077
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from channelflow.bars.models import Bar
from channelflow.pipeline import channel_main
from channelflow.settings import MissingConfiguration
from channelflow.timeframes import TIMEFRAMES

MINUTE_NS = 60_000_000_000
BASE_NS = 1_789_344_000_000_000_000  # 2026-09-14T00:00:00Z, a Monday


def minute(open_time_ns: int, *, venue: str = "binance", symbol: str = "BTCUSDT") -> Bar:
    price = Decimal("100")
    return Bar(
        venue=venue,
        symbol=symbol,
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_time_ns,
        close_time_ns=open_time_ns + MINUTE_NS,
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
        high_time_ns=open_time_ns,
        low_time_ns=open_time_ns,
        first_trade_id="1",
        last_trade_id="1",
        is_final=True,
    )


class TestIntervalSeconds:
    @pytest.mark.trace("REQ-WP-077")
    def test_seconds(self):
        assert channel_main._interval_seconds("30") == 30.0

    @pytest.mark.trace("REQ-WP-077")
    def test_minutes(self):
        assert channel_main._interval_seconds("5m") == 300.0

    @pytest.mark.trace("REQ-WP-077")
    def test_hours(self):
        assert channel_main._interval_seconds("1h") == 3600.0

    @pytest.mark.trace("REQ-WP-077")
    def test_days(self):
        assert channel_main._interval_seconds("1d") == 86400.0

    @pytest.mark.trace("REQ-WP-077")
    def test_plain_number(self):
        assert channel_main._interval_seconds("60") == 60.0


class TestRunSeries:
    @pytest.mark.trace("REQ-WP-077")
    def test_returns_none_when_no_bars(self):
        mock_table = MagicMock()
        mock_table.catalog = MagicMock()
        bars_table = MagicMock()
        bars_table.read_bars.return_value = []

        target = TIMEFRAMES["1h"]
        result = channel_main.run_series(
            mock_table, venue="binance", symbol="BTCUSDT", target=target
        )
        assert result is None

    @pytest.mark.trace("REQ-WP-077")
    def test_calls_record_replay_with_bars(self):
        mock_table = MagicMock()
        mock_table.catalog = MagicMock()
        mock_table.catalog.current.return_value = None

        record_replay = MagicMock(return_value=(
            MagicMock(channel_snapshots=1, signals=2, confirmed_extrema=0, extremum_candidates=0),
            MagicMock(),
        ))
        channel_main.record_replay = record_replay

        bars = [minute(BASE_NS)]
        bars_table_mock = MagicMock()
        bars_table_mock.read_bars.return_value = bars
        channel_main.bars_table = bars_table_mock

        target = TIMEFRAMES["1h"]
        result = channel_main.run_series(
            mock_table, venue="binance", symbol="BTCUSDT", target=target
        )
        assert result is not None
        assert record_replay.called
        call_kwargs = record_replay.call_args
        assert call_kwargs.kwargs["venue"] == "binance"
        assert call_kwargs.kwargs["symbol"] == "BTCUSDT"
        assert call_kwargs.kwargs["timeframe_ns"] == target.ns


class TestRunPass:
    @pytest.mark.trace("REQ-WP-077")
    def test_discovers_series_from_bars_table(self, catalog: MagicMock, tmp_path: Path):
        table = MagicMock()
        table.catalog = catalog
        bars_table_mock = MagicMock()
        bars = [
            minute(BASE_NS, venue="binance", symbol="BTCUSDT"),
            minute(BASE_NS + MINUTE_NS, venue="binance", symbol="ETHUSDT"),
        ]
        bars_table_mock.read_bars.return_value = bars
        channel_main.bars_table = bars_table_mock

        target = TIMEFRAMES["1h"]
        record_replay = MagicMock(return_value=(
            MagicMock(channel_snapshots=0, signals=0, confirmed_extrema=0, extremum_candidates=0),
            MagicMock(),
        ))
        channel_main.record_replay = record_replay

        results = channel_main.run_pass(catalog, targets=(target,))
        assert len(results) == 2
        venues = {(r[0], r[1]) for r in results}
        assert ("binance", "BTCUSDT") in venues
        assert ("binance", "ETHUSDT") in venues

    @pytest.mark.trace("REQ-WP-077")
    def test_skips_timeframe_with_no_bars(self, catalog: MagicMock):
        table = MagicMock()
        table.catalog = catalog
        bars_table_mock = MagicMock()
        bars_table_mock.read_bars.return_value = [
            minute(BASE_NS, venue="binance", symbol="BTCUSDT"),
        ]
        channel_main.bars_table = bars_table_mock

        target_1h = TIMEFRAMES["1h"]
        target_4h = TIMEFRAMES["4h"]

        record_replay = MagicMock(return_value=(
            MagicMock(channel_snapshots=0, signals=0, confirmed_extrema=0, extremum_candidates=0),
            MagicMock(),
        ))
        channel_main.record_replay = record_replay

        # When read_bars is called with timeframe_ns=4h, return empty
        def read_bars_side_effect(*args, **kwargs):
            if kwargs.get("timeframe_ns") == target_4h.ns:
                return []
            return [minute(BASE_NS, venue="binance", symbol="BTCUSDT")]

        bars_table_mock.read_bars.side_effect = read_bars_side_effect

        results = channel_main.run_pass(catalog, targets=(target_1h, target_4h))
        # Only 1h results, 4h skipped
        assert len(results) == 1
        assert results[0][2] == "1h"

    @pytest.mark.trace("REQ-WP-077")
    def test_failure_does_not_stop_pass(self, catalog: MagicMock):
        table = MagicMock()
        table.catalog = catalog
        bars_table_mock = MagicMock()
        bars = [minute(BASE_NS, venue="binance", symbol="BTCUSDT")]
        bars_table_mock.read_bars.return_value = bars
        channel_main.bars_table = bars_table_mock

        target_1h = TIMEFRAMES["1h"]

        def record_replay_raises(*args, **kwargs):
            if kwargs.get("symbol") == "BTCUSDT":
                raise ValueError("test error")
            return (
                MagicMock(channel_snapshots=0, signals=0,
                          confirmed_extrema=0, extremum_candidates=0),
                MagicMock(),
            )

        channel_main.record_replay = MagicMock(side_effect=record_replay_raises)

        results = channel_main.run_pass(catalog, targets=(target_1h,))
        assert len(results) == 0


class TestMain:
    @pytest.mark.trace("REQ-WP-077")
    def test_once_exits_zero(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("CHANNELFLOW_TIMEFRAMES", "1h")
        monkeypatch.setenv("CHANNELFLOW_CATALOG_URI", f"sqlite:///{tmp_path}/catalog.db")
        monkeypatch.setenv("CHANNELFLOW_WAREHOUSE", str(tmp_path))

        result = channel_main.main(["--once"])
        assert result == 0

    @pytest.mark.trace("REQ-WP-077")
    def test_missing_timeframes_raises(self, monkeypatch):
        monkeypatch.delenv("CHANNELFLOW_TIMEFRAMES", raising=False)
        monkeypatch.setenv("CHANNELFLOW_CATALOG_URI", "sqlite:///test")
        monkeypatch.setenv("CHANNELFLOW_WAREHOUSE", "/tmp")

        with pytest.raises(MissingConfiguration):
            channel_main.main(["--once"])