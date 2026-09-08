"""Local order-book reconstruction.

# @trace: REQ-WP-003
# @trace: REQ-WP-004

Venue-agnostic by ADR-012: nothing here parses an exchange payload. It takes
normalized `BookDelta` and `BookSnapshot` values, which is why it lives here
rather than inside the connector that happened to need it first -- Principle
VIII ("connectors share one interface") is empty if the shared thing sits
inside one connector.

PRD section 11.1 gives the procedure and this follows it literally: buffer
deltas, take a snapshot, discard obsolete deltas, apply by exact sequence rules,
and mark the book stale on a gap.

Two things here are load-bearing rather than defensive.

PRD section 8.1 forbids hiding sequence gaps -- so a delta that does not follow
the last one is *not* applied, and the book records that it happened. A book
that quietly accepted it would diverge from the venue while still reporting
itself healthy, which is the failure mode a feed library would hide.

PRD section 11.1 rule 6 forbids emitting features from an invalid or stale book
-- so `best_bid_ask` raises rather than returning its last good contents. If it
answered anyway, every caller would have to remember the rule, and one of them
would not.

Pure: no socket, no clock. A recorded delta and a live one follow the same path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.domain import BookDelta, BookSnapshot, PriceLevel


class BookInvalid(RuntimeError):
    """The book cannot answer because it is not in a trustworthy state."""


@dataclass(frozen=True)
class BookHealth:
    """The status PRD section 11.1 requires a reconstruction to expose."""

    valid: bool
    gap_count: int
    last_sequence: int
    stale_ns: int = 0


@dataclass
class OrderBook:
    """A reconstructed book, plus an honest account of whether to trust it."""

    bids: dict[Decimal, Decimal] = field(default_factory=dict)
    asks: dict[Decimal, Decimal] = field(default_factory=dict)
    _last_sequence: int = 0
    _gap_count: int = 0
    _valid: bool = True
    #: Event time of the last applied delta or snapshot. Never ingest time --
    #: PRD section 9 forbids treating that as market information.
    _last_event_time_ns: int = 0

    @classmethod
    def from_snapshot(cls, snapshot: BookSnapshot) -> OrderBook:
        """Start from a REST snapshot -- PRD section 11.1 step 2."""
        book = cls(
            _last_sequence=snapshot.update_id,
            _last_event_time_ns=snapshot.meta.event_time_ns,
        )
        for level in snapshot.bids:
            book.bids[level.price] = level.qty
        for level in snapshot.asks:
            book.asks[level.price] = level.qty
        return book

    @classmethod
    def from_first_delta(cls, delta: BookDelta) -> OrderBook:
        """Start from a delta, for replaying a recorded stream without a
        snapshot. Real ingestion always uses `from_snapshot`."""
        book = cls(
            _last_sequence=delta.final_update_id or 0,
            _last_event_time_ns=delta.meta.event_time_ns,
        )
        book._apply_levels(delta)
        return book

    def health(self, as_of_ns: int | None = None) -> BookHealth:
        """Whether to trust this book, and how far behind it is.

        `as_of_ns` is the caller's event time -- staleness is the distance from
        the last applied event to it. Reading a clock here would make the same
        recorded stream report different health on a second replay (ADR-012).
        """
        stale_ns = 0
        if as_of_ns is not None and self._last_event_time_ns:
            stale_ns = max(0, as_of_ns - self._last_event_time_ns)
        return BookHealth(
            valid=self._valid,
            gap_count=self._gap_count,
            last_sequence=self._last_sequence,
            stale_ns=stale_ns,
        )

    def apply_bootstrap(self, delta: BookDelta) -> None:
        """Apply the first delta after a snapshot -- PRD section 11.1 step 4.

        The steady-state rule in `apply` demands exact continuity. The first
        delta after a snapshot is the one case where a venue does not promise
        it: Binance documents that the first update to apply is the one whose
        range *contains* `lastUpdateId + 1`, because a delta may straddle the
        moment the snapshot was taken. Refusing that here would make every
        bootstrap fail against a live feed.

        This is the one place the exact rule is relaxed, and it is relaxed by
        a narrower one -- the range must still contain the next sequence.
        """
        first = delta.first_update_id
        final = delta.final_update_id
        if first is None or final is None:
            raise BookInvalid("delta carries no sequence range")
        if not first <= self._last_sequence + 1 <= final:
            raise BookInvalid(
                f"delta [{first}, {final}] does not contain sequence "
                f"{self._last_sequence + 1}; it cannot be the first after this snapshot"
            )
        self._apply_levels(delta)
        self._last_sequence = final
        self._last_event_time_ns = delta.meta.event_time_ns

    def apply(self, delta: BookDelta) -> None:
        """Apply one delta, or record why it could not be applied."""
        first = delta.first_update_id
        final = delta.final_update_id
        if first is None or final is None:
            raise BookInvalid("delta carries no sequence range")

        # Step 3: a delta the snapshot already covers is obsolete, not a gap.
        if final <= self._last_sequence:
            return

        # Step 4/5: the sequence must be exactly continuous. Anything else is a
        # gap, and the delta is refused rather than applied out of order.
        if first != self._last_sequence + 1:
            self._gap_count += 1
            self._valid = False
            return

        self._apply_levels(delta)
        self._last_sequence = final
        self._last_event_time_ns = delta.meta.event_time_ns

    def _apply_levels(self, delta: BookDelta) -> None:
        for level in delta.bids:
            if level.qty == 0:
                self.bids.pop(level.price, None)
            else:
                self.bids[level.price] = level.qty
        for level in delta.asks:
            if level.qty == 0:
                self.asks.pop(level.price, None)
            else:
                self.asks[level.price] = level.qty

    def top(self, n: int) -> tuple[tuple[PriceLevel, ...], tuple[PriceLevel, ...]]:
        """The n levels nearest the touch on each side, best price first.

        Both sides start at the touch and walk outward, so index 0 is always
        the most aggressive rung and the two sides are directly comparable.

        Sorts each side per call. At the few thousand rungs a venue publishes
        this is not worth a sorted structure, and PRD section 0.14 puts
        correctness first -- but the cost is linear in the whole book, not in n.
        """
        self._require_usable()
        bids = sorted(self.bids.items(), key=lambda item: item[0], reverse=True)[:n]
        asks = sorted(self.asks.items(), key=lambda item: item[0])[:n]
        return (
            tuple(PriceLevel(price=price, qty=qty) for price, qty in bids),
            tuple(PriceLevel(price=price, qty=qty) for price, qty in asks),
        )

    def mid(self) -> Decimal:
        """The reference price for every distance query -- ADR-011.

        Raises when either side is empty: a distance from a price that does not
        exist is not a smaller answer, it is a different question.
        """
        bid, ask = self.best_bid_ask()
        if bid is None or ask is None:
            raise BookInvalid(
                "no mid price: one side of the book is empty, so there is no "
                "reference to measure a distance from"
            )
        return (bid + ask) / 2

    def depth_within_bps(self, bps: float) -> tuple[Decimal, Decimal]:
        """Resting quantity per side within `bps` of the mid (PRD section 15.5).

        The band is symmetric around one reference, which is what makes the two
        numbers a ratio worth taking -- section 15.1's `DI_k`. Measured from
        each side's own best price they would be two different distances
        wearing one name, and the imbalance would move with the spread.
        """
        mid = self.mid()
        distance = mid * Decimal(str(bps)) / Decimal(10_000)
        floor = mid - distance
        ceiling = mid + distance
        bid_depth = sum((qty for price, qty in self.bids.items() if price >= floor), Decimal(0))
        ask_depth = sum((qty for price, qty in self.asks.items() if price <= ceiling), Decimal(0))
        return bid_depth, ask_depth

    def _require_usable(self) -> None:
        if not self._valid:
            raise BookInvalid(
                f"book is stale after {self._gap_count} sequence gap(s); "
                "rebuild from a fresh snapshot before using it"
            )

    def best_bid_ask(self) -> tuple[Decimal | None, Decimal | None]:
        """The top of book -- or a refusal.

        PRD section 11.1 rule 6: never emit features from an invalid book.
        """
        self._require_usable()
        return (
            max(self.bids) if self.bids else None,
            min(self.asks) if self.asks else None,
        )
