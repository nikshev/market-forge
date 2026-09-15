"""Liquidity wall lifecycle (PRD section 15.6).

# @trace: REQ-WP-011
# @trace: REQ-NRT-LEAK

A level whose resting size is anomalous against its neighbours is tracked from
the moment it appears until it is gone, and what happened to it is split into
what traded through and what was pulled.

That split is the reason the family exists. PRD section 2.2: large passive
orders can vanish quickly, so a static heatmap or snapshot imbalance can create
a false sense of liquidity. A wall that was eaten and a wall that was pulled
look identical in the book and mean opposite things.

The book cannot tell them apart on its own -- hence PRD section 15.6's own
`_est` suffixes. ADR-014 states the rule: executed is bounded by the volume that
actually printed at that price in the interval, and the remainder is
cancellation. The bias is towards reporting cancellation, which is the safer
error: over-reporting execution turns an abandoned wall into absorbed demand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from channelflow.book import BookService
from channelflow.domain import TradeEvent
from channelflow.features.registry import FeatureSpec, register

FEATURES: tuple[str, ...] = (
    "wall_persistence_ns",
    "wall_executed_size_est",
    "wall_cancelled_size_est",
    "wall_refill_count",
)

#: How many times the neighbouring average a level must exceed to count as a
#: wall. PRD section 13.11's warning applies: a research default, not a proven
#: parameter, which is why it is an argument.
DEFAULT_SIZE_MULTIPLE = 5.0
#: Levels either side used as the comparison. Too few and a two-level shelf
#: hides the anomaly; too many and the far book drowns it.
NEIGHBOUR_LEVELS = 3


@dataclass
class Wall:
    """PRD section 15.6's `WallState`, accumulated over the wall's life."""

    side: Literal["bid", "ask"]
    price: Decimal
    first_seen_ns: int
    last_seen_ns: int
    max_size: Decimal
    _size_sum: Decimal
    _observations: int
    executed_size_est: Decimal = Decimal(0)
    cancelled_size_est: Decimal = Decimal(0)
    refill_count: int = 0
    move_count: int = 0
    current_size: Decimal = Decimal(0)
    #: Set when the wall leaves the book. A finished wall is history and is
    #: never edited again -- Principle III.
    finished: bool = False

    @property
    def persistence_ns(self) -> int:
        return self.last_seen_ns - self.first_seen_ns

    @property
    def avg_size(self) -> Decimal:
        return self._size_sum / self._observations if self._observations else Decimal(0)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "finished", False):
            raise AttributeError(
                f"wall at {self.price} is finished; its record is history and "
                "PRD section 0.5 forbids rewriting it"
            )
        super().__setattr__(name, value)


@dataclass
class WallTracker:
    """Book states in, wall lifecycles out.

    Each `observe` takes the trades since the previous call, so ADR-014's
    `min(decrease, traded)` is local to one interval and the tracker never has
    to hold -- or trim -- a trade history.
    """

    size_multiple: float = DEFAULT_SIZE_MULTIPLE
    _active: dict[tuple[str, Decimal], Wall] = field(default_factory=dict)
    _finished: list[Wall] = field(default_factory=list)

    @property
    def active(self) -> tuple[Wall, ...]:
        return tuple(self._active.values())

    @property
    def finished(self) -> tuple[Wall, ...]:
        return tuple(self._finished)

    def observe(
        self, service: BookService, *, trades: tuple[TradeEvent, ...], as_of_ns: int
    ) -> None:
        """Advance every tracked wall by one observation.

        **Trades after `as_of_ns` are ignored here rather than by the caller.**
        This takes the data and the moment separately, and nothing reconciled
        them: handing over the whole day's trades with an earlier `as_of_ns`
        attributed future volume to a wall's execution. Measured before the
        filter existed, on a wall shrinking 3 units a step against trades of 0.2:
        `executed_size_est` 2.0 filtered against 4.0 unfiltered, with
        `cancelled_size_est` moving 25.0 to 23.0 to match.

        Nothing in production called it that way. It was reachable through the
        signature, which is the same argument `state_at` makes for owning its
        own freshness rule: a rule each call site has to remember is a rule one
        call site will forget ([[REQ-NRT-LEAK]], PRD §35.4).
        """
        bids, asks = service.top(50)
        traded = _volume_by_price(tuple(t for t in trades if t.meta.event_time_ns <= as_of_ns))

        seen: set[tuple[str, Decimal]] = set()
        for side, levels in (("bid", bids), ("ask", asks)):
            sizes = [level.qty for level in levels]
            for index, level in enumerate(levels):
                if not _is_anomalous(sizes, index, self.size_multiple):
                    continue
                key = (side, level.price)
                seen.add(key)
                self._advance(key, side, level.price, level.qty, as_of_ns, traded)

        for key in [k for k in self._active if k not in seen]:
            self._retire(key, as_of_ns, traded)

    def _advance(
        self,
        key: tuple[str, Decimal],
        side: str,
        price: Decimal,
        size: Decimal,
        as_of_ns: int,
        traded: dict[Decimal, Decimal],
    ) -> None:
        wall = self._active.get(key)
        if wall is None:
            self._active[key] = Wall(
                side=side,  # type: ignore[arg-type]
                price=price,
                first_seen_ns=as_of_ns,
                last_seen_ns=as_of_ns,
                max_size=size,
                _size_sum=size,
                _observations=1,
                current_size=size,
            )
            return

        if size < wall.current_size:
            self._attribute(wall, wall.current_size - size, traded.get(price, Decimal(0)))
        elif size > wall.current_size:
            # A wall that comes back is the same wall behaving a certain way --
            # section 15.6 scores refills. Treating each as new would erase the
            # persistence it is scoring.
            wall.refill_count += 1

        wall.current_size = size
        wall.last_seen_ns = as_of_ns
        wall.max_size = max(wall.max_size, size)
        wall._size_sum += size
        wall._observations += 1

    def _retire(
        self, key: tuple[str, Decimal], as_of_ns: int, traded: dict[Decimal, Decimal]
    ) -> None:
        wall = self._active.pop(key)
        self._attribute(wall, wall.current_size, traded.get(wall.price, Decimal(0)))
        wall.current_size = Decimal(0)
        wall.last_seen_ns = as_of_ns
        wall.finished = True
        self._finished.append(wall)

    @staticmethod
    def _attribute(wall: Wall, decrease: Decimal, traded_here: Decimal) -> None:
        """ADR-014, in one place.

        `traded_here` is evidence; the book difference is not. Attributing more
        to execution than the tape shows would manufacture liquidity
        consumption out of an observation gap.
        """
        already = wall.executed_size_est
        executed = min(decrease, max(Decimal(0), traded_here - already))
        wall.executed_size_est += executed
        wall.cancelled_size_est += decrease - executed


def _volume_by_price(trades: tuple[TradeEvent, ...]) -> dict[Decimal, Decimal]:
    """Base volume that printed at each price in this interval.

    Keyed by exact price: ADR-014 attributes a trade to the price it printed
    at, not to a band around it.
    """
    totals: dict[Decimal, Decimal] = {}
    for event in trades:
        totals[event.price] = totals.get(event.price, Decimal(0)) + event.qty_base
    return totals


def _is_anomalous(sizes: list[Decimal], index: int, multiple: float) -> bool:
    """Is this level far larger than the levels around it?

    Compared against its neighbours rather than against the whole book: a book
    that is uniformly thick has no walls in it, and one that is uniformly thin
    should not have every second level flagged.
    """
    neighbours = [
        size
        for offset, size in enumerate(sizes)
        if offset != index and abs(offset - index) <= NEIGHBOUR_LEVELS
    ]
    if not neighbours:
        return False
    average = sum(neighbours, Decimal(0)) / len(neighbours)
    if average == 0:
        return sizes[index] > 0
    return sizes[index] >= average * Decimal(str(multiple))


def _register_all() -> None:
    common = {
        "family": "order_book",
        "source_events": ("book_snapshot", "book_delta", "trade"),
        "lookback": "the wall's lifetime",
        "cadence": "per book update",
        "availability_lag_ms": 0,
        "clipping": "none",
        "point_in_time_safe": True,
        "test_fixture": "tests/unit/features/test_walls.py",
    }
    register(
        FeatureSpec(
            name="wall_persistence_ns",
            version=1,
            description="How long a wall has rested, in event time.",
            formula="last_seen_event_time - first_seen_event_time",
            unit="nanoseconds",
            null_policy="absent while no wall is tracked at that level",
            normalization="none; compare against the timeframe in use",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="wall_executed_size_est",
            version=1,
            description="Estimated size traded through a wall over its lifetime.",
            formula=(
                "per interval, min(size_decrease, base volume printed at that exact "
                "price); summed over the wall's life (ADR-014)"
            ),
            unit="base currency",
            null_policy="zero until a decrease is matched by trades at that price",
            normalization="none; compare against max_size",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="wall_cancelled_size_est",
            version=1,
            description="Estimated size pulled from a wall over its lifetime.",
            formula="per interval, size_decrease minus the executed estimate (ADR-014)",
            unit="base currency",
            null_policy=(
                "zero until a decrease occurs; a decrease with no matching trades "
                "counts entirely here, which is the deliberate bias"
            ),
            normalization="none; compare against max_size",
            **common,  # type: ignore[arg-type]
        )
    )
    register(
        FeatureSpec(
            name="wall_refill_count",
            version=1,
            description="How many times a wall's size grew after shrinking.",
            formula="count of observations where size exceeded the previous observation",
            unit="count",
            null_policy="zero for a wall that has never grown",
            normalization="none",
            **common,  # type: ignore[arg-type]
        )
    )


_register_all()
