"""§36's targets under concurrent traffic (REQ-WP-067).

Phase 8's acceptance: "load tests demonstrate §36's targets, and a target that
is not met is reported rather than omitted."
"""

from __future__ import annotations

import threading
import time

import pytest

from channelflow.perf.load import (
    AllRequestsFailed,
    LoadResult,
    TargetReport,
    Verdict,
    drive,
    passed,
    report,
)
from channelflow.perf.targets import TARGETS, Measurement, Target

FAST = Target(name="chart_historical_load", stated="p95 < 2s", budget_ns=2_000_000_000)
TIGHT = Target(name="feature_update", stated="<= 1s", budget_ns=1)


def _result(
    name: str, *, samples: tuple[int, ...] = (1000,), concurrency: int = 1, errors: int = 0
) -> LoadResult:
    return LoadResult(
        name=name,
        concurrency=concurrency,
        measurement=Measurement(name=name, samples_ns=samples),
        errors=errors,
    )


# --------------------------------------------------------------------------
# Driving the load
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-067")
def test_every_request_is_timed_separately() -> None:
    """A batch duration divided by its count is a mean, and §36 states a p95
    because a mean hides the slow ones."""
    result = drive(lambda: time.sleep(0.001), name="x", concurrency=2, requests=8)

    assert len(result.measurement.samples_ns) == 8
    assert result.requests == 8
    assert result.clean


@pytest.mark.trace("REQ-WP-067")
def test_the_workers_actually_run_together() -> None:
    """Concurrency reported but not exercised would make every number a
    sequential one under a different name."""
    seen: set[int] = set()
    lock = threading.Lock()
    live = 0
    peak = 0

    def work() -> None:
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
            seen.add(threading.get_ident())
        time.sleep(0.02)
        with lock:
            live -= 1

    drive(work, name="x", concurrency=4, requests=12)

    assert peak > 1, "no two requests were ever in flight together"
    assert len(seen) > 1


@pytest.mark.trace("REQ-WP-067")
def test_a_failed_request_is_not_a_fast_one() -> None:
    """An error returns sooner than work does. Folded into the samples it lowers
    the percentile, and a failing system measures as a quick one."""
    calls = {"n": 0}

    def flaky() -> None:
        calls["n"] += 1
        if calls["n"] % 2:
            raise ConnectionError("refused")
        time.sleep(0.005)

    result = drive(flaky, name="x", concurrency=2, requests=8)

    assert result.errors == 4
    assert len(result.measurement.samples_ns) == 4
    assert not result.clean
    assert result.first_error is not None and "refused" in result.first_error


@pytest.mark.trace("REQ-WP-067")
def test_a_run_where_everything_failed_has_no_latency_to_report() -> None:
    """Reporting zero would make it the fastest result in the file."""

    def broken() -> None:
        raise TimeoutError("gone")

    with pytest.raises(AllRequestsFailed, match="all 4 request"):
        drive(broken, name="x", concurrency=2, requests=4)


@pytest.mark.trace("REQ-WP-067")
def test_fewer_requests_than_workers_is_refused() -> None:
    """The concurrency measured would not be the concurrency asked for."""
    with pytest.raises(ValueError, match="leaves a worker idle"):
        drive(lambda: None, name="x", concurrency=4, requests=2)


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-067")
def test_a_target_nobody_measured_is_reported_as_such() -> None:
    """The assertion this whole requirement turns on. A report of two targets
    that passes is indistinguishable from one that measured all three."""
    reports = report([_result("chart_historical_load")], targets=TARGETS)

    assert len(reports) == len(TARGETS)
    verdicts = {item.target.name: item.verdict for item in reports}
    assert verdicts["chart_historical_load"] is Verdict.MET
    assert verdicts["feature_update"] is Verdict.NOT_MEASURED
    assert verdicts["signal_after_bar_close"] is Verdict.NOT_MEASURED


@pytest.mark.trace("REQ-WP-067")
def test_an_unmeasured_target_is_not_a_pass() -> None:
    reports = report([_result("chart_historical_load")], targets=TARGETS)

    assert not passed(reports)


@pytest.mark.trace("REQ-WP-067")
def test_an_empty_report_is_not_a_pass() -> None:
    """Nothing measured is not everything met."""
    assert not passed([])


@pytest.mark.trace("REQ-WP-067")
def test_a_missed_target_is_reported_with_its_numbers() -> None:
    reports = report([_result("feature_update", samples=(5_000,))], targets=(TIGHT,))

    assert reports[0].verdict is Verdict.NOT_MET
    assert reports[0].p95_ns == 5_000
    assert "not met" in reports[0].line
    assert "5000ns against 1ns" in reports[0].line


@pytest.mark.trace("REQ-WP-067")
def test_a_run_with_errors_is_not_a_pass_however_fast() -> None:
    """Latency well inside the budget, and one request failed."""
    reports = report([_result("chart_historical_load", samples=(10,), errors=1)], targets=(FAST,))

    assert reports[0].verdict is Verdict.NOT_MET
    assert reports[0].errors == 1
    assert "1 error(s)" in reports[0].line


@pytest.mark.trace("REQ-WP-067")
def test_the_worst_concurrency_decides() -> None:
    """A target met at one client and missed at ten is not met, and reporting
    the best run would say it was."""
    reports = report(
        [
            _result("chart_historical_load", samples=(10,), concurrency=1),
            _result("chart_historical_load", samples=(9_000_000_000,), concurrency=10),
        ],
        targets=(FAST,),
    )

    assert reports[0].verdict is Verdict.NOT_MET
    assert reports[0].concurrency == 10


@pytest.mark.trace("REQ-WP-067")
def test_every_line_carries_what_reproduces_it() -> None:
    reports = report(
        [_result("chart_historical_load", concurrency=8, samples=(7, 9))], targets=(FAST,)
    )

    line = reports[0].line
    assert "concurrency 8" in line
    assert "2 request(s)" in line
    assert "headroom" in line


@pytest.mark.trace("REQ-WP-067")
def test_an_unmeasured_line_still_states_the_promise() -> None:
    line = TargetReport(target=FAST, verdict=Verdict.NOT_MEASURED).line

    assert "not measured" in line
    assert FAST.stated in line
