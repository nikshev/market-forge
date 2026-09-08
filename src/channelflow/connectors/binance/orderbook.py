"""Local order-book reconstruction.

# @trace: REQ-WP-003

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

from channelflow.domain import BookDelta, BookSnapshot


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

    @classmethod
    def from_snapshot(cls, snapshot: BookSnapshot) -> OrderBook:
        """Start from a REST snapshot -- PRD section 11.1 step 2."""
        book = cls(_last_sequence=snapshot.update_id)
        for level in snapshot.bids:
            book.bids[level.price] = level.qty
        for level in snapshot.asks:
            book.asks[level.price] = level.qty
        return book

    @classmethod
    def from_first_delta(cls, delta: BookDelta) -> OrderBook:
        """Start from a delta, for replaying a recorded stream without a
        snapshot. Real ingestion always uses `from_snapshot`."""
        book = cls(_last_sequence=delta.final_update_id or 0)
        book._apply_levels(delta)
        return book

    @property
    def health(self) -> BookHealth:
        return BookHealth(
            valid=self._valid,
            gap_count=self._gap_count,
            last_sequence=self._last_sequence,
        )

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

    def best_bid_ask(self) -> tuple[Decimal | None, Decimal | None]:
        """The top of book -- or a refusal.

        PRD section 11.1 rule 6: never emit features from an invalid book.
        """
        if not self._valid:
            raise BookInvalid(
                f"book is stale after {self._gap_count} sequence gap(s); "
                "rebuild from a fresh snapshot before using it"
            )
        return (
            max(self.bids) if self.bids else None,
            min(self.asks) if self.asks else None,
        )
