"""PRD §45 Phase 8's load tests: §36's targets under concurrent traffic.

# @trace: REQ-WP-067

[[REQ-WP-057]] measured the same targets one call at a time and found fifty to
several thousand times of headroom. That answers what one user waits for and
says nothing about twenty waiting together, which is the question a load test
exists for: a system can hold a target at one client and miss it at ten with
nothing in the code changing.

**§36 states no concurrency**, so asserting one would be a research default
wearing a decision's clothes. What is reported is the shape -- the percentile at
each concurrency and where a target stops being met -- which is the choice
[[REQ-WP-057]] made when it asserted a scaling ratio rather than an absolute
duration.

**A failed request is not a fast one.** An error returns sooner than work does,
so folding errors into the samples lowers the percentile and a failing system
measures as a quick one. They are counted apart and a run with any error is not
a pass, however good the latencies look.

**A target nobody measured is reported, not omitted.** Phase 8's acceptance asks
for an unmet target to be reported; the sharper form is that a target with no
measurement must appear too. A report of two targets that passes is
indistinguishable from one that measured all three, and the missing one is
exactly where the trouble would be.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum

from channelflow.perf.targets import TARGETS, Measurement, Target, headroom


@dataclass(frozen=True)
class LoadResult:
    """What one run at one concurrency cost, and what went wrong in it."""

    name: str
    concurrency: int
    measurement: Measurement
    errors: int
    #: The first error's text, so a failing run is diagnosable from the report
    #: rather than from a log nobody kept.
    first_error: str | None = None

    @property
    def requests(self) -> int:
        return len(self.measurement.samples_ns) + self.errors

    @property
    def clean(self) -> bool:
        return self.errors == 0


class Verdict(StrEnum):
    """What a report says about one target.

    Three, not two. `NOT_MEASURED` is the value that keeps a report honest: a
    target silently absent looks exactly like a target that passed.
    """

    MET = "met"
    NOT_MET = "not met"
    NOT_MEASURED = "not measured"


@dataclass(frozen=True)
class TargetReport:
    """One of §36's promises, against what was measured."""

    target: Target
    verdict: Verdict
    concurrency: int | None = None
    p95_ns: int | None = None
    headroom: float | None = None
    errors: int = 0
    requests: int = 0

    @property
    def line(self) -> str:
        """One line a reader can act on, carrying what reproduces it."""
        if self.verdict is Verdict.NOT_MEASURED:
            return f"{self.target.name}: not measured — {self.target.stated}"
        return (
            f"{self.target.name}: {self.verdict} at concurrency {self.concurrency} "
            f"over {self.requests} request(s) — p95 {self.p95_ns}ns against "
            f"{self.target.budget_ns}ns"
            + (f", {self.errors} error(s)" if self.errors else "")
            + (f", headroom {self.headroom:.1f}x" if self.headroom is not None else "")
        )


def drive(
    operation: Callable[[], object],
    *,
    name: str,
    concurrency: int,
    requests: int,
) -> LoadResult:
    """Issue `requests` through `concurrency` workers, timing each one.

    Every request is timed individually rather than the batch as a whole: a
    batch duration divided by its count is a mean, and §36 states a p95 for the
    reason a mean hides the slow ones.
    """
    if concurrency < 1:
        raise ValueError("a load run needs at least one worker")
    if requests < concurrency:
        raise ValueError(
            f"{requests} request(s) across {concurrency} worker(s) leaves a worker idle; "
            "the concurrency measured would not be the concurrency asked for"
        )

    samples: list[int] = []
    errors: list[str] = []

    def once() -> None:
        started = time.perf_counter_ns()
        try:
            operation()
        except Exception as cause:  # noqa: BLE001 -- an error is a result, not a stop
            errors.append(f"{type(cause).__name__}: {cause}")
            return
        samples.append(time.perf_counter_ns() - started)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(lambda _: once(), range(requests)))

    if not samples:
        # A run where everything failed has no latency to report, and reporting
        # zero would be the fastest result in the file.
        raise AllRequestsFailed(
            f"{name}: all {requests} request(s) failed at concurrency {concurrency}; "
            f"first: {errors[0] if errors else 'unknown'}"
        )
    return LoadResult(
        name=name,
        concurrency=concurrency,
        measurement=Measurement(name=name, samples_ns=tuple(samples)),
        errors=len(errors),
        first_error=errors[0] if errors else None,
    )


class AllRequestsFailed(RuntimeError):
    """Every request in a run errored, so there is no latency to report."""


def report(
    results: Sequence[LoadResult],
    *,
    targets: Sequence[Target] = TARGETS,
    measures: dict[str, str] | None = None,
) -> tuple[TargetReport, ...]:
    """Every target, against the run that measured it.

    `measures` maps a result's name to a target's; a target with no result
    reports `NOT_MEASURED` rather than being left out.
    """
    mapping = measures or {result.name: result.name for result in results}
    by_target: dict[str, LoadResult] = {}
    for result in results:
        target_name = mapping.get(result.name)
        if target_name is None:
            continue
        # The slowest concurrency decides: a target met at one client and missed
        # at ten is not met, and reporting the best run would say it was.
        current: LoadResult | None = by_target.get(target_name)
        if current is None or result.measurement.p95_ns > current.measurement.p95_ns:
            by_target[target_name] = result

    reports = []
    for target in targets:
        measured = by_target.get(target.name)
        if measured is None:
            reports.append(TargetReport(target=target, verdict=Verdict.NOT_MEASURED))
            continue
        met = measured.clean and measured.measurement.p95_ns <= target.budget_ns
        reports.append(
            TargetReport(
                target=target,
                verdict=Verdict.MET if met else Verdict.NOT_MET,
                concurrency=measured.concurrency,
                p95_ns=measured.measurement.p95_ns,
                headroom=headroom(measured.measurement, target),
                errors=measured.errors,
                requests=measured.requests,
            )
        )
    return tuple(reports)


def passed(reports: Sequence[TargetReport]) -> bool:
    """Every target met. A target not measured is not a pass."""
    return bool(reports) and all(item.verdict is Verdict.MET for item in reports)
