# @trace: REQ-WP-073
from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.bars.models import Bar
from channelflow.lakehouse import Catalog
from channelflow.pipeline import resample_main
from channelflow.pipeline.resample import Refusal, ResampleResult, report_for
from channelflow.tables import bars as bars_table
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


def seed(table, count: int, *, venue: str = "binance", symbol: str = "BTCUSDT") -> None:
    bars_table.write_bars(
        table, [minute(BASE_NS + i * MINUTE_NS, venue=venue, symbol=symbol) for i in range(count)]
    )


class TestResampleReport:
    @pytest.mark.trace("REQ-WP-073")
    def test_report_carries_what_was_committed_not_what_was_computed(self):
        # The case that justifies the second type: a pass can compute ten bars
        # and fail to append them, and the report must not say ten were written.
        result = ResampleResult(
            bars=(minute(BASE_NS),),
            refusals=(),
            skipped=0,
        )
        report = report_for(
            result,
            venue="binance",
            symbol="BTCUSDT",
            timeframe=TIMEFRAMES["5m"],
            written=0,
        )
        assert report.written == 0
        assert len(result.bars) == 1

    @pytest.mark.trace("REQ-WP-073")
    def test_line_names_written_and_skipped(self):
        result = ResampleResult(bars=(), refusals=(), skipped=3)
        report = report_for(
            result,
            venue="binance",
            symbol="BTCUSDT",
            timeframe=TIMEFRAMES["5m"],
            written=0,
        )
        assert "binance" in report.line
        assert "BTCUSDT" in report.line
        assert "5m" in report.line
        assert "skipped=3" in report.line

    @pytest.mark.trace("REQ-WP-073")
    def test_line_counts_refusals(self):
        result = ResampleResult(
            bars=(),
            refusals=(Refusal(open_time_ns=BASE_NS, expected=5, present=4, reason="missing"),),
            skipped=0,
        )
        report = report_for(
            result,
            venue="binance",
            symbol="BTCUSDT",
            timeframe=TIMEFRAMES["5m"],
            written=0,
        )
        assert "refused=1" in report.line


class TestMain:
    @pytest.mark.trace("REQ-WP-073")
    def test_once_writes_the_configured_timeframe(
        self, catalog: Catalog, tmp_path: Path, monkeypatch
    ):
        table = bars_table.table_for(catalog)
        seed(table, 15)
        monkeypatch.setenv("CHANNELFLOW_CATALOG_URI", f"sqlite:///{tmp_path}/catalog.db")
        monkeypatch.setenv("CHANNELFLOW_WAREHOUSE", str(tmp_path))
        monkeypatch.setenv("CHANNELFLOW_TIMEFRAMES", "5m")

        assert resample_main.main(["--once"]) == 0

        stored = bars_table.read_bars(table, timeframe_ns=TIMEFRAMES["5m"].ns)
        assert len(stored) == 3
        assert all(bar.is_final for bar in stored)

    @pytest.mark.trace("REQ-WP-073")
    def test_once_exits_zero_when_everything_already_existed(
        self, catalog: Catalog, tmp_path: Path, monkeypatch, capsys
    ):
        table = bars_table.table_for(catalog)
        seed(table, 15)
        monkeypatch.setenv("CHANNELFLOW_CATALOG_URI", f"sqlite:///{tmp_path}/catalog.db")
        monkeypatch.setenv("CHANNELFLOW_WAREHOUSE", str(tmp_path))
        monkeypatch.setenv("CHANNELFLOW_TIMEFRAMES", "5m")

        assert resample_main.main(["--once"]) == 0
        first_rows = bars_table.table_for(catalog).read().num_rows

        assert resample_main.main(["--once"]) == 0
        output = capsys.readouterr().out
        assert "written=0" in output
        assert "skipped=3" in output
        assert bars_table.table_for(catalog).read().num_rows == first_rows

    @pytest.mark.trace("REQ-WP-073")
    def test_four_hour_comes_from_configuration_alone(
        self, catalog: Catalog, tmp_path: Path, monkeypatch
    ):
        # 4h is outside §5.1's four, and no source file names it except the
        # vocabulary table -- so its series can only have come from the config.
        table = bars_table.table_for(catalog)
        seed(table, 240)
        monkeypatch.setenv("CHANNELFLOW_CATALOG_URI", f"sqlite:///{tmp_path}/catalog.db")
        monkeypatch.setenv("CHANNELFLOW_WAREHOUSE", str(tmp_path))
        monkeypatch.setenv("CHANNELFLOW_TIMEFRAMES", "4h")

        assert resample_main.main(["--once"]) == 0

        stored = bars_table.read_bars(table, timeframe_ns=TIMEFRAMES["4h"].ns)
        assert len(stored) == 1

        sources = [
            path
            for path in (Path("src") / "channelflow").rglob("*.py")
            if path.name not in {"timeframes.py"} and "__pycache__" not in path.parts
        ]
        offenders = [str(path) for path in sources if "4h" in path.read_text()]
        assert offenders == []
