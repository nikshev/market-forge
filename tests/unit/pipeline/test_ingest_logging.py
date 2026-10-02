"""An ingest service logs events, not traffic (REQ-WP-078).

# @trace: REQ-WP-078

Five services logged 300 to 3,216 lines a minute -- 57 to 577 KB -- because every trade
wrote two or three lines at INFO: `BarBuilder.add called for trade ...`, `_finalize_ready:
...`, `Normalized 1 trade(s)`, and a flush line on every step even with nothing to flush.
Bybit's log was 6.6 GB after six days. The volume was code, not configuration, and raising
a level in compose would have hidden the one line that matters along with them.

The records are counted from the loggers these tests are about. `caplog` collects every
logger, and other tests in the suite leave threads that log on their own schedule.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import pytest

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import BINANCE, FakeClock, StreamSession
from channelflow.connectors.websocket import ReplayTransport
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore
from channelflow.pipeline.ingest import IngestDaemon, streams_for
from channelflow.pipeline.ingest_main import log_level_from_env
from channelflow.settings import MissingConfiguration

from .test_ingest import RECORDED, FakeReplayConnector

SECOND_NS = 1_000_000_000
BASE_NS = 1_789_000_000_000_000_000

TRAFFIC_LOGGERS = ("channelflow.bars", "channelflow.pipeline.ingest")


def _daemon(tmp_path: Path) -> IngestDaemon:
    transport = ReplayTransport(recorded=RECORDED)
    clock = FakeClock(BASE_NS)
    connector = FakeReplayConnector(transport)
    return IngestDaemon(
        session=StreamSession(
            streams=streams_for(["BTCUSDT"]), policy=BINANCE, connector=connector, clock=clock
        ),
        connector=connector,
        archive=FrameArchive(
            store=LocalObjectStore(root=tmp_path), venue="binance", symbol="BTCUSDT"
        ),
        builder=BarBuilder(
            timeframe_ns=SECOND_NS, grace_ns=5 * SECOND_NS, on_final=lambda bar: None
        ),
        venue="binance",
        now_ns=clock.now_ns,
    )


@pytest.mark.trace("REQ-WP-078")
def test_the_trade_frame_and_step_path_writes_nothing_at_info(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    daemon = _daemon(tmp_path)
    daemon.start()

    for _ in range(50):
        daemon.step()
    daemon.stop()

    traffic = [
        f"{r.name}: {r.getMessage()}"
        for r in caplog.records
        if r.name.startswith(TRAFFIC_LOGGERS) and r.levelno >= logging.INFO
    ]
    assert traffic == [], traffic[:3]


@pytest.mark.trace("REQ-WP-078")
def test_the_archive_says_one_line_per_object_it_writes_and_none_for_a_step(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    daemon = _daemon(tmp_path)
    daemon.start()

    for _ in range(50):
        daemon.step()
    daemon.stop()

    written = len(list(tmp_path.rglob("*.jsonl.gz")))
    lines = [
        r
        for r in caplog.records
        if r.name == "channelflow.pipeline.archive" and r.levelno >= logging.INFO
    ]
    assert written >= 1
    assert len(lines) <= written, (len(lines), written)


@pytest.mark.trace("REQ-WP-078")
def test_the_trade_lines_still_exist_at_debug_for_the_day_someone_needs_them(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Demoted, not deleted: a debugger who asks for DEBUG gets the old output."""
    caplog.set_level(logging.DEBUG)
    daemon = _daemon(tmp_path)
    daemon.start()
    daemon.step()
    daemon.stop()

    assert any(
        r.name.startswith(TRAFFIC_LOGGERS) and r.levelno == logging.DEBUG for r in caplog.records
    )


# --- configuration ---------------------------------------------------------------


def _python(code: str, **env: str) -> str:
    import os

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, **env},
        check=True,
    )
    return result.stdout.strip()


@pytest.mark.trace("REQ-WP-078")
def test_importing_the_daemons_module_does_not_reconfigure_the_root_logger() -> None:
    """`logging.basicConfig` ran at import, so every test that imported the module
    inherited a side effect and the root logger had a handler before `main()` began."""
    out = _python(
        "import logging; import channelflow.pipeline.ingest_main as m; "
        "r = logging.getLogger(); print(len(r.handlers), r.level)"
    )

    assert out == f"0 {logging.WARNING}"


@pytest.mark.trace("REQ-WP-078")
def test_configure_logging_honours_the_level_in_the_environment() -> None:
    out = _python(
        "import logging; from channelflow.pipeline.ingest_main import configure_logging; "
        "configure_logging(); print(logging.getLogger().level)",
        CHANNELFLOW_LOG_LEVEL="DEBUG",
    )

    assert out == str(logging.DEBUG)


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize(
    ("value", "level"),
    [
        (None, logging.INFO),
        ("", logging.INFO),
        ("debug", logging.DEBUG),
        ("WARNING", logging.WARNING),
    ],
)
def test_the_level_defaults_to_info_and_is_not_case_sensitive(value, level) -> None:  # type: ignore[no-untyped-def]
    environ = {} if value is None else {"CHANNELFLOW_LOG_LEVEL": value}

    assert log_level_from_env(environ) == level


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize("value", ["LOUD", "10", "trace"])
def test_an_unknown_level_is_refused_naming_the_variable(value: str) -> None:
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_LOG_LEVEL"):
        log_level_from_env({"CHANNELFLOW_LOG_LEVEL": value})


@pytest.mark.trace("REQ-WP-078")
def test_main_configures_logging_before_it_reads_anything_else(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Moving `basicConfig` out of import time is only a fix if `main()` still calls it. With
    nothing set `settings_from_env` refuses, so the refusal is the earliest point at which
    `main()` can be asked what it had already done."""
    from channelflow.pipeline import ingest_main

    calls: list[int] = []
    monkeypatch.setattr(ingest_main, "configure_logging", lambda: calls.append(1))
    for name in ("CHANNELFLOW_CATALOG_URI", "CHANNELFLOW_WAREHOUSE"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(MissingConfiguration):
        ingest_main.main([])

    assert calls == [1]
