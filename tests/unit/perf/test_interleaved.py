"""A scaling guard that measures its sizes under the same conditions (REQ-INFRA-011).

`tests/perf/` asserts that a doubling of the work costs about twice as much. The premise written
into
its module docstring was that "a ratio between two measurements from the same run divides the
machine
out". It does not, when the measurements are taken one after another: twenty runs of the small size,
then twenty of the next, then twenty of the largest. A burst of load that lasts a few seconds lands
on one size and not the others, the ratio across it is wrong by the size of the burst, and the test
fails on a code change that never happened. On a host with a load average of four it failed six
gates or full runs in one session, on two tests, each green when run alone.

These tests build a world where that is exact: a fake clock, operations whose cost is known, and a
burst of extra cost over a contiguous range of calls. The old way (one size, then the next) is
fooled by
it; measuring in rounds, so that every size sees every condition, is not.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from channelflow.perf import Measurement, scaling_ratio, timed
from channelflow.perf.targets import timed_interleaved

REPEATS = 20


class World:
    """A clock that only the operations move, and a burst of load over a range of calls."""

    def __init__(self, *, burst: range = range(0), burst_factor: int = 10) -> None:
        self.now = 0
        self.calls = 0
        self.order: list[str] = []
        self._burst = burst
        self._factor = burst_factor

    def clock(self) -> int:
        return self.now

    def operation(self, name: str, cost: int) -> Callable[[], None]:
        def run() -> None:
            self.order.append(name)
            noisy = self.calls in self._burst
            self.now += cost * (self._factor if noisy else 1)
            self.calls += 1

        return run


SIZES = {"1k": 1_000, "2k": 2_000, "4k": 4_000}


def _sequential(world: World, cost: Callable[[int], int]) -> tuple[Measurement, ...]:
    return tuple(
        timed(world.operation(name, cost(n)), name=name, repeats=REPEATS, clock=world.clock)
        for name, n in SIZES.items()
    )


def _interleaved(world: World, cost: Callable[[int], int]) -> tuple[Measurement, ...]:
    return timed_interleaved(
        {name: world.operation(name, cost(n)) for name, n in SIZES.items()},
        repeats=REPEATS,
        clock=world.clock,
    )


def linear(n: int) -> int:
    return n


def quadratic(n: int) -> int:
    return n * n // 1_000


# --- the fault, reproduced -------------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-011")
def test_measuring_one_size_after_another_is_fooled_by_a_burst_of_load() -> None:
    """The characterization: a perfectly linear operation, and a burst that happens to cover the
    middle size. The ratio across it is nowhere near two. This is the flake, made exact."""
    world = World(burst=range(REPEATS, 2 * REPEATS))  # exactly the second size's twenty calls

    ratios = scaling_ratio(_sequential(world, linear))

    assert ratios[0] > 3.0, ratios


@pytest.mark.trace("REQ-INFRA-011")
def test_measuring_in_rounds_survives_the_same_burst() -> None:
    """Same operation, same burst (twenty consecutive calls out of sixty). Every size sees it
    for about
    a third of its samples, so the medians move together and the ratios stay near two."""
    world = World(burst=range(REPEATS, 2 * REPEATS))

    ratios = scaling_ratio(_interleaved(world, linear))

    assert all(1.5 < ratio < 3.0 for ratio in ratios), ratios


@pytest.mark.trace("REQ-INFRA-011")
@pytest.mark.parametrize("start", [0, 7, 13, 25, 40])
def test_wherever_the_burst_falls_the_rounds_agree(start: int) -> None:
    world = World(burst=range(start, start + REPEATS))

    ratios = scaling_ratio(_interleaved(world, linear))

    assert all(ratio < 3.0 for ratio in ratios), (start, ratios)


# --- the guard must still bite ----------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-011")
def test_a_quadratic_operation_is_still_caught_when_measured_in_rounds() -> None:
    """Interleaving must not buy stability by going blind: a doubling that costs four times is a
    ratio near four with no noise at all, and with a burst."""
    quiet = scaling_ratio(_interleaved(World(), quadratic))
    noisy = scaling_ratio(_interleaved(World(burst=range(REPEATS, 2 * REPEATS)), quadratic))

    assert all(ratio >= 3.0 for ratio in quiet), quiet
    assert all(ratio >= 3.0 for ratio in noisy), noisy


@pytest.mark.trace("REQ-INFRA-011")
def test_with_no_noise_a_linear_operation_gives_exactly_two() -> None:
    ratios = scaling_ratio(_interleaved(World(), linear))

    assert ratios == (2.0, 2.0)


# --- what rounds are -------------------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-011")
def test_every_round_runs_every_operation_once() -> None:
    world = World()

    _interleaved(world, linear)

    for start in range(0, len(world.order), 3):
        assert sorted(world.order[start : start + 3]) == sorted(SIZES)
    assert len(world.order) == 3 * REPEATS


@pytest.mark.trace("REQ-INFRA-011")
def test_the_order_within_a_round_rotates() -> None:
    """If the largest size always ran last, it would always run on whatever the first two
    left behind
    (a warm cache, a heated core, a collected heap). Rotating the start spreads that too."""
    world = World()

    _interleaved(world, linear)

    firsts = [world.order[i] for i in range(0, 9, 3)]
    assert firsts == ["1k", "2k", "4k"]


@pytest.mark.trace("REQ-INFRA-011")
def test_the_measurements_come_back_in_the_order_they_were_given() -> None:
    """`scaling_ratio` pairs neighbours, so the order is part of the answer."""
    got = _interleaved(World(), linear)

    assert [m.name for m in got] == list(SIZES)
    assert all(len(m.samples_ns) == REPEATS for m in got)


@pytest.mark.trace("REQ-INFRA-011")
def test_nothing_to_measure_and_no_runs_are_refused() -> None:
    with pytest.raises(ValueError, match="nothing"):
        timed_interleaved({}, repeats=3)
    with pytest.raises(ValueError, match="at least one"):
        timed_interleaved({"a": lambda: None}, repeats=0)


# --- the statistic ---------------------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-011")
def test_a_lower_quantile_ignores_the_slow_half_that_noise_adds() -> None:
    """Noise only ever adds time. The median of a size whose slow samples outnumber its fast
    ones is a
    slow sample; the lower quartile is still a fast one."""
    small = Measurement(name="s", samples_ns=(10,) * 8)
    large = Measurement(name="l", samples_ns=(20, 20, 60, 60, 60, 60, 60, 60))

    assert scaling_ratio((small, large)) == (6.0,)  # the median, unchanged by default
    assert scaling_ratio((small, large), fraction=0.25) == (2.0,)
