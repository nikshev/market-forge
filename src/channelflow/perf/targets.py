"""What PRD §36 promises, and the arithmetic for checking it.

# @trace: REQ-WP-057
# @trace: REQ-INFRA-011

§36 states three latencies a user waits on. Measured against the real code, each
has between fifty and several thousand times of headroom -- which decides what a
test here should actually assert.

**Asserting the target is right and is not enough.** It is the promise made to a
user, so a test that would notice it being broken is worth having; but with
fiftyfold headroom it would keep passing through a fortyfold regression.

**Asserting a tight threshold measures the runner.** Within one run on one
machine the spread between the fastest and slowest read was already 2.27 times.
A threshold close enough to today's number to catch a regression fails on a busy
runner, and a failure nobody can tell from noise is a test people learn to
re-run.

**So the assertion that earns its place is about scaling.** A ratio between two
measurements taken in the same run on the same machine is something a busy
runner cannot move, and a change making a linear read quadratic fails it while a
slow machine does not.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

NS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class Target:
    """One of §36's promises, in the section's own words."""

    name: str
    #: The section's wording, so a reader can find it.
    stated: str
    budget_ns: int


TARGETS: tuple[Target, ...] = (
    Target(
        name="chart_historical_load",
        stated="chart historical load p95 < 2s for 2,000 bars",
        budget_ns=2 * NS_PER_SECOND,
    ),
    Target(
        name="signal_after_bar_close",
        stated="signal after bar close <= 2s",
        budget_ns=2 * NS_PER_SECOND,
    ),
    Target(
        name="feature_update",
        stated="feature update <= 1s",
        budget_ns=NS_PER_SECOND,
    ),
)


@dataclass(frozen=True)
class Measurement:
    """What a run of one operation cost, in order.

    Percentiles rather than a mean: §36 states one of its targets as a p95, and
    a mean over a run containing one slow outlier hides exactly the outlier a
    percentile is for.
    """

    name: str
    samples_ns: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.samples_ns:
            raise ValueError(f"{self.name}: a measurement with no samples measured nothing")

    def percentile_ns(self, fraction: float) -> int:
        """The sample at `fraction` through the sorted run, rounded up.

        Nearest-rank rather than interpolated. An interpolated p95 over twenty
        samples reports a duration that never happened, and the question here is
        what the slow ones cost.
        """
        if not 0.0 < fraction <= 1.0:
            raise ValueError(f"{fraction} is not a fraction of a run")
        ordered = sorted(self.samples_ns)
        rank = max(1, -(-len(ordered) * fraction // 1))
        return ordered[int(rank) - 1]

    @property
    def p50_ns(self) -> int:
        return self.percentile_ns(0.5)

    @property
    def p95_ns(self) -> int:
        return self.percentile_ns(0.95)

    @property
    def spread(self) -> float:
        """Slowest over fastest, which is what a threshold has to survive."""
        ordered = sorted(self.samples_ns)
        return ordered[-1] / max(1, ordered[0])


def timed(
    operation: Callable[[], object],
    *,
    name: str,
    repeats: int,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> Measurement:
    """Run an operation `repeats` times and keep every duration.

    No warm-up is performed here and callers are expected to do one. Folding it
    in would hide the first call's cost, and whether a first call is slow is
    sometimes the question.

    Do not use this to compare sizes of one operation. It measures one thing to
    completion before the next, so whatever the machine was doing while it ran
    belongs to that thing alone: see `timed_interleaved`.
    """
    if repeats < 1:
        raise ValueError("a measurement needs at least one run")
    samples: list[int] = []
    for _ in range(repeats):
        started = clock()
        operation()
        samples.append(clock() - started)
    return Measurement(name=name, samples_ns=tuple(samples))


def timed_interleaved(
    operations: Mapping[str, Callable[[], object]],
    *,
    repeats: int,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> tuple[Measurement, ...]:
    """Measure several operations in rounds, so each of them sees the same conditions.

    One run of every operation per round, `repeats` rounds, the starting operation
    rotating each round. The measurements come back in the order the operations were
    given, because `scaling_ratio` pairs neighbours.

    **Why this exists** ([[REQ-INFRA-011]]). A scaling guard compares the cost of a size
    with the cost of twice that size, and its premise was that the ratio "divides the
    machine out". It does only if both are measured under the same conditions. Measured
    one after the other -- all the small runs, then all the next size -- a burst of
    load a few seconds long lands on one size, and the ratio is wrong by the size of the
    burst. On a host with a load average of four that failed six gates or full runs in one
    session, on two tests that were each green when run alone. In rounds, a burst
    reaches every size in proportion, and the ratio between them survives it.

    The start rotates because the operation that always runs last always runs on what
    the others left behind: a warm cache, a heated core, a collected heap.
    """
    if not operations:
        raise ValueError("there is nothing to measure")
    if repeats < 1:
        raise ValueError("a measurement needs at least one run")
    names = list(operations)
    samples: dict[str, list[int]] = {name: [] for name in names}
    for round_number in range(repeats):
        for offset in range(len(names)):
            name = names[(round_number + offset) % len(names)]
            started = clock()
            operations[name]()
            samples[name].append(clock() - started)
    return tuple(Measurement(name=name, samples_ns=tuple(samples[name])) for name in names)


def headroom(measurement: Measurement, target: Target, *, at: float = 0.95) -> float:
    """How many times over the budget the measurement could grow before failing.

    Reported rather than only compared. A target met with fifty times to spare
    and a target met with one and a half are the same pass, and the difference is
    the only warning anybody gets.
    """
    observed = measurement.percentile_ns(at)
    return target.budget_ns / max(1, observed)


def scaling_ratio(
    measurements: Sequence[Measurement], *, fraction: float = 0.5
) -> tuple[float, ...]:
    """How much each doubling of the work cost, against the one before it.

    The ratios, not the durations. Two measurements from the same run on the
    same machine divide out whatever that machine was doing, which is what makes
    this assertable where a duration is not.

    A linear operation gives ratios near 2 across a doubling series; a quadratic
    one gives ratios near 4, and does so on a fast machine and a slow one alike.

    `fraction` is the quantile compared; the median by default. Noise only ever adds
    time, so on a busy host a lower quantile (a guard uses 0.25) is a fast sample where
    the median may already be a slow one. It does not make a quadratic operation look
    linear: every sample of it is quadratic.
    """
    if len(measurements) < 2:
        raise ValueError("a scaling ratio needs at least two measurements")
    picked = [measurement.percentile_ns(fraction) for measurement in measurements]
    return tuple(
        later / max(1, earlier) for earlier, later in zip(picked, picked[1:], strict=False)
    )
