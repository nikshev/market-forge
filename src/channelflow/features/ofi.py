"""Order flow imbalance, Cont-style (PRD section 15.3).

# @trace: REQ-WP-011

The increment between two consecutive top-of-book observations:

    e = 1[Pb_n >= Pb_{n-1}] * Qb_n  -  1[Pb_n <= Pb_{n-1}] * Qb_{n-1}
      - 1[Pa_n <= Pa_{n-1}] * Qa_n  +  1[Pa_n >= Pa_{n-1}] * Qa_{n-1}

The indicators are deliberately non-strict on both sides, so an unchanged price
fires both and the term collapses to the change in size. Writing them strictly
gives a function that is right whenever the touch moves and silently wrong the
rest of the time -- which is most of the time.

**Consecutive is load-bearing.** After a sequence gap the next observation is
not the successor of the last one: the states either side of an outage differ
by everything that happened during it, and differencing them attributes all of
it to one instant. The number looks completely ordinary. `on_discontinuity`
exists so the caller can say that happened, and the tracker drops its baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.features.registry import FeatureSpec, register

SECOND_NS = 1_000_000_000

#: PRD section 15.3's aggregate windows. The fifth -- "one signal timeframe
#: bar" -- is not a constant: it comes from REQ-WP-005's bar boundaries, so
#: `window` takes a length rather than an enum.
WINDOWS: tuple[int, ...] = (SECOND_NS, 5 * SECOND_NS, 30 * SECOND_NS, 60 * SECOND_NS)

FEATURES: tuple[str, ...] = ("ofi_1s", "ofi_5s", "ofi_30s", "ofi_1m", "ofi_bar")


@dataclass(frozen=True)
class Observation:
    """The top of book at one instant, and when that instant was."""

    bid_price: Decimal
    bid_qty: Decimal
    ask_price: Decimal
    ask_qty: Decimal
    event_time_ns: int


@dataclass(frozen=True)
class OFIWindow:
    """A window's total, and how many increments produced it.

    The count is not diagnostics. Zero flow and no data both read as 0, and a
    caller treating a silent feed as a balanced book is acting on nothing.
    """

    value: Decimal
    observations: int
    window_ns: int
    as_of_ns: int

    @property
    def is_empty(self) -> bool:
        return self.observations == 0


@dataclass
class OFITracker:
    """Consecutive observations in, windowed imbalance out."""

    _previous: Observation | None = None
    _increments: list[tuple[int, Decimal]] = field(default_factory=list)

    def observe(self, observation: Observation) -> Decimal | None:
        """Record an observation. Returns its increment, or None if there is none.

        None means "no increment exists", not "the increment was zero": the
        first observation and the first after a discontinuity have nothing to
        difference against.
        """
        previous = self._previous
        if previous is not None and observation.event_time_ns < previous.event_time_ns:
            raise ValueError(
                "observations must arrive in event-time order; "
                f"{observation.event_time_ns} follows {previous.event_time_ns}"
            )

        self._previous = observation
        if previous is None:
            return None

        increment = _cont_increment(previous, observation)
        self._increments.append((observation.event_time_ns, increment))
        return increment

    def on_discontinuity(self) -> None:
        """The feed broke -- a sequence gap, a rebuild, a reconnect.

        The next observation starts a new baseline instead of being differenced
        against a state from before the outage (FR-009).
        """
        self._previous = None

    def window(self, window_ns: int, *, as_of_ns: int) -> OFIWindow:
        """Sum the increments in `(as_of_ns - window_ns, as_of_ns]`.

        Half-open at the start so an increment belongs to exactly one window of
        a given length, however the windows are tiled.
        """
        floor = as_of_ns - window_ns
        inside = [value for time_ns, value in self._increments if floor < time_ns <= as_of_ns]
        return OFIWindow(
            value=sum(inside, Decimal(0)),
            observations=len(inside),
            window_ns=window_ns,
            as_of_ns=as_of_ns,
        )


def _cont_increment(previous: Observation, current: Observation) -> Decimal:
    bid = Decimal(0)
    if current.bid_price >= previous.bid_price:
        bid += current.bid_qty
    if current.bid_price <= previous.bid_price:
        bid -= previous.bid_qty

    ask = Decimal(0)
    if current.ask_price <= previous.ask_price:
        ask -= current.ask_qty
    if current.ask_price >= previous.ask_price:
        ask += previous.ask_qty

    return bid + ask


def _register_all() -> None:
    for name, lookback, cadence in (
        ("ofi_1s", "1s", "1s"),
        ("ofi_5s", "5s", "1s"),
        ("ofi_30s", "30s", "1s"),
        ("ofi_1m", "1m", "1s"),
        ("ofi_bar", "one signal timeframe bar", "per bar close"),
    ):
        register(
            FeatureSpec(
                name=name,
                version=1,
                family="order_flow",
                description=f"Cont-style top-of-book order flow imbalance over {lookback}.",
                formula=(
                    "sum over consecutive observations of "
                    "1[Pb_n >= Pb_n-1]*Qb_n - 1[Pb_n <= Pb_n-1]*Qb_n-1 "
                    "- 1[Pa_n <= Pa_n-1]*Qa_n + 1[Pa_n >= Pa_n-1]*Qa_n-1; "
                    "no increment is formed across a sequence gap"
                ),
                unit="base currency",
                source_events=("book_snapshot", "book_delta"),
                lookback=lookback,
                cadence=cadence,
                availability_lag_ms=0,
                null_policy=(
                    "a window with no observations reports zero and is flagged empty; "
                    "the two are not the same fact"
                ),
                clipping="none",
                normalization=(
                    "none; the raw sum is in base currency and is not comparable "
                    "across symbols without one"
                ),
                point_in_time_safe=True,
                test_fixture=(
                    "tests/unit/features/test_ofi.py::test_a_window_sums_the_increments_inside_it"
                ),
            )
        )


_register_all()
