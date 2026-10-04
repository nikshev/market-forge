"""A background pass that fails is reported and tried again (REQ-INFRA-012).

The `worker` and `resample` run as loops. A series that fails inside a pass was already survivable;
the first
read of a pass was not, and an exception there left `main`, ended the process and relied on compose
to start
it again. That happened twice on 2026-10-03, for two unrelated causes: a `NoSuchSnapshot` race
(`resample`,
01:02) and an HTTP 503 from the object store under load (`worker`, 16:38). A transient fault in a
dependency should cost one pass, not a process.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from channelflow.pipeline import channel_main, resample_main
from channelflow.pipeline.passes import run_passes


class _Stop(BaseException):
    """Ends a loop that would otherwise run for ever. A BaseException, so nothing swallows it."""


class _Sleeper:
    def __init__(self, *, stop_after: int | None = None) -> None:
        self.slept: list[float] = []
        self._stop_after = stop_after

    def __call__(self, seconds: float) -> None:
        self.slept.append(seconds)
        if self._stop_after is not None and len(self.slept) >= self._stop_after:
            raise _Stop


def _flaky(*outcomes: Exception | None) -> tuple[Callable[[], None], list[int]]:
    """A pass that raises, or not, in the order given; and the record of its calls."""
    calls: list[int] = []
    queue = list(outcomes)

    def one_pass() -> None:
        calls.append(1)
        if len(calls) > 40:
            # A loop that never sleeps never reaches the sleeper's stop. Ending it here makes a
            # broken loop a failed test and not a hung one.
            raise _Stop
        outcome = queue.pop(0) if queue else None
        if outcome is not None:
            raise outcome

    return one_pass, calls


# --- survived and reported ----------------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-012")
def test_a_failing_pass_is_reported_and_the_next_pass_runs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    one_pass, calls = _flaky(OSError("HTTP 503 during HeadObject"), None)
    sleeper = _Sleeper(stop_after=2)

    with pytest.raises(_Stop):
        run_passes("worker", one_pass, interval_seconds=300, sleep=sleeper)

    out = capsys.readouterr().out
    assert len(calls) == 2, "the loop went on to a second pass"
    assert "worker" in out and "OSError" in out and "HTTP 503 during HeadObject" in out
    assert sleeper.slept == [300, 300], (
        "it waited its interval after the failure as after a success"
    )


@pytest.mark.trace("REQ-INFRA-012")
def test_the_traceback_is_printed_once_per_run_of_failures(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A repeated condition does not repeat its full report: a storage outage of an hour would
    otherwise print twelve tracebacks."""
    one_pass, _ = _flaky(OSError("down"), OSError("still down"), OSError("still down"), None)

    with pytest.raises(_Stop):
        run_passes("resample", one_pass, interval_seconds=60, sleep=_Sleeper(stop_after=4))

    out = capsys.readouterr().out
    assert out.count("Traceback (most recent call last)") == 1
    assert out.count("pass failed") == 3, "one line for every failure"
    assert "3 in a row" in out


@pytest.mark.trace("REQ-INFRA-012")
def test_recovery_is_reported_with_how_many_passes_failed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    one_pass, _ = _flaky(OSError("a"), OSError("b"), None)

    with pytest.raises(_Stop):
        run_passes("worker", one_pass, interval_seconds=5, sleep=_Sleeper(stop_after=3))

    assert "recovered after 2 failed pass(es)" in capsys.readouterr().out


@pytest.mark.trace("REQ-INFRA-012")
def test_a_new_run_of_failures_prints_its_traceback_again(
    capsys: pytest.CaptureFixture[str],
) -> None:
    one_pass, _ = _flaky(OSError("first"), None, OSError("second"), None)

    with pytest.raises(_Stop):
        run_passes("worker", one_pass, interval_seconds=5, sleep=_Sleeper(stop_after=4))

    assert capsys.readouterr().out.count("Traceback (most recent call last)") == 2


@pytest.mark.trace("REQ-INFRA-012")
def test_a_healthy_loop_says_nothing_extra(capsys: pytest.CaptureFixture[str]) -> None:
    one_pass, calls = _flaky(None, None, None)

    with pytest.raises(_Stop):
        run_passes("worker", one_pass, interval_seconds=5, sleep=_Sleeper(stop_after=3))

    out = capsys.readouterr().out
    assert len(calls) == 3
    assert "failed" not in out and "recovered" not in out
    # FR-006: exactly what the loops printed before, and nothing else.
    assert out == "-- next pass in 5s\n" * 3


# --- what must still stop the process ------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-012")
def test_in_once_mode_a_failing_pass_still_ends_the_process() -> None:
    """There is no next pass to try, so surviving would turn a failure into a silent success."""
    one_pass, _ = _flaky(OSError("down"))

    with pytest.raises(OSError, match="down"):
        run_passes("worker", one_pass, interval_seconds=None)


@pytest.mark.trace("REQ-INFRA-012")
def test_in_once_mode_a_successful_pass_returns_zero() -> None:
    one_pass, calls = _flaky(None)

    assert run_passes("worker", one_pass, interval_seconds=None) == 0
    assert len(calls) == 1


@pytest.mark.trace("REQ-INFRA-012")
@pytest.mark.parametrize("stop", [KeyboardInterrupt(), SystemExit(3)])
def test_an_interrupt_or_an_exit_is_not_swallowed(stop: BaseException) -> None:
    def one_pass() -> None:
        raise stop

    with pytest.raises(type(stop)):
        # If the interrupt were swallowed the loop would sleep; the sleeper ends it as a failure
        # of this test (a `_Stop` where a `KeyboardInterrupt` was expected) and not as a hang.
        run_passes("worker", one_pass, interval_seconds=5, sleep=_Sleeper(stop_after=3))


# --- the two jobs use it
# ---------------------------------------------------------------------------


def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHANNELFLOW_TIMEFRAMES", "5m,15m")
    monkeypatch.setenv("CHANNELFLOW_CATALOG_URI", "sqlite:///unused.db")
    monkeypatch.setenv("CHANNELFLOW_WAREHOUSE", "/tmp/unused")


def _drive(
    monkeypatch: pytest.MonkeyPatch, module: Any, *, name: str, capsys: pytest.CaptureFixture[str]
) -> list[int]:
    """Run `module.main(["--loop", ...])` with a pass that fails once, then succeeds."""
    _env(monkeypatch)
    calls: list[int] = []

    def run_pass(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            raise OSError("HTTP 503 during HeadObject")
        return []

    monkeypatch.setattr(module, "run_pass", run_pass)
    monkeypatch.setattr(module, "open_catalog", lambda **_: object())
    monkeypatch.setattr("time.sleep", _Sleeper(stop_after=2))

    with pytest.raises(_Stop):
        module.main(["--loop", "1m"])
    out = capsys.readouterr().out
    assert name in out and "HTTP 503" in out, out
    return calls


@pytest.mark.trace("REQ-INFRA-012")
def test_the_worker_survives_a_failed_pass_through_main(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert len(_drive(monkeypatch, channel_main, name="worker", capsys=capsys)) == 2


@pytest.mark.trace("REQ-INFRA-012")
def test_resample_survives_a_failed_pass_through_main(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert len(_drive(monkeypatch, resample_main, name="resample", capsys=capsys)) == 2


@pytest.mark.trace("REQ-INFRA-012")
@pytest.mark.parametrize("module", [channel_main, resample_main])
def test_main_in_once_mode_still_fails_loudly(monkeypatch: pytest.MonkeyPatch, module: Any) -> None:
    _env(monkeypatch)

    def failing(*args: Any, **kwargs: Any) -> Any:
        raise OSError("down")

    monkeypatch.setattr(module, "run_pass", failing)
    monkeypatch.setattr(module, "open_catalog", lambda **_: object())

    with pytest.raises(OSError, match="down"):
        module.main(["--once"])
