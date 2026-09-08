"""Bootstrap, gap and rebuild -- the book's lifecycle.

# @trace: REQ-WP-004

PRD section 11.1 gives five steps, and only the middle three are about applying
deltas. The other two are about *when a book may be used at all*: buffer before
you have a snapshot, and stop when the sequence breaks. `OrderBook` owns the
state; this owns the question of whether there is a trustworthy one yet.

No I/O and no clock (ADR-012). On a gap this asks for a snapshot -- through
`needs_snapshot` -- and the caller supplies one. How long to wait, how many
times to retry, and what to do when the venue keeps failing are operational
questions with no correct answer inside a data structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.book.book import BookHealth, BookInvalid, OrderBook
from channelflow.domain import BookDelta, BookSnapshot, PriceLevel


class BootstrapFailed(RuntimeError):
    """The buffer and the snapshot do not belong together.

    Distinct from `BookInvalid`, which means "this book cannot answer". This
    means "no book was built", and the caller's response differs: fetch another
    snapshot rather than inspect what went wrong.
    """


@dataclass
class BookService:
    """One venue, one symbol: a book and the story of how it got there."""

    book: OrderBook | None = None
    _buffer: list[BookDelta] = field(default_factory=list)
    #: Gaps seen by books this service has *retired*. The live book counts its
    #: own; adding them at rebuild time rather than at gap time is what keeps a
    #: gap from being counted twice while the book that saw it is still here.
    _retired_gap_count: int = 0

    @property
    def is_bootstrapped(self) -> bool:
        return self.book is not None

    @property
    def needs_snapshot(self) -> bool:
        """True when the caller should fetch one: no book yet, or a broken one."""
        return self.book is None or not self.book.health().valid

    def on_delta(self, delta: BookDelta) -> None:
        """Apply, or buffer until there is something to apply to."""
        if self.book is None or not self.book.health().valid:
            self._buffer.append(delta)
            return
        before = self.book.health().gap_count
        self.book.apply(delta)
        if self.book.health().gap_count > before:
            # PRD section 8.1: the gap is recorded, not smoothed over. The
            # buffer restarts here so a later snapshot has deltas to connect to.
            self._buffer = [delta]

    def on_snapshot(self, snapshot: BookSnapshot) -> None:
        """PRD section 11.1 steps 2-4: snapshot, discard obsolete, apply the rest.

        Raises `BootstrapFailed` rather than building a book with a hole in it.
        """
        book = OrderBook.from_snapshot(snapshot)
        pending = [
            d
            for d in self._buffer
            if d.final_update_id is not None and d.final_update_id > snapshot.update_id
        ]

        if pending:
            first, *rest = pending
            try:
                book.apply_bootstrap(first)
            except BookInvalid as exc:
                # The buffer starts after the snapshot ends: the deltas between
                # them were never seen. Applying `first` anyway would give a
                # book that looks healthy and is wrong at every level those
                # missing deltas touched.
                raise BootstrapFailed(
                    f"buffered deltas do not connect to the snapshot at {snapshot.update_id}: {exc}"
                ) from exc
            for d in rest:
                book.apply(d)
            if not book.health().valid:
                raise BootstrapFailed(
                    f"the buffer itself has a sequence gap; "
                    f"snapshot at {snapshot.update_id} cannot bootstrap from it"
                )

        if self.book is not None:
            # SC-003: the retiring book's gaps are this service's history. A
            # book that forgot them on every rebuild would report perfect
            # health while flapping.
            self._retired_gap_count += self.book.health().gap_count
        self.book = book
        self._buffer = []

    def rebuild(self, snapshot: BookSnapshot) -> None:
        """Recover from a gap. The cumulative gap count survives (FR-006)."""
        self.on_snapshot(snapshot)

    def health(self, as_of_ns: int | None = None) -> BookHealth:
        if self.book is None:
            return BookHealth(valid=False, gap_count=self._retired_gap_count, last_sequence=0)
        inner = self.book.health(as_of_ns)
        return BookHealth(
            valid=inner.valid,
            gap_count=self._retired_gap_count + inner.gap_count,
            last_sequence=inner.last_sequence,
            stale_ns=inner.stale_ns,
        )

    def best_bid_ask(self) -> tuple[Decimal | None, Decimal | None]:
        return self._usable().best_bid_ask()

    def top(self, n: int) -> tuple[tuple[PriceLevel, ...], tuple[PriceLevel, ...]]:
        return self._usable().top(n)

    def depth_within_bps(self, bps: float) -> tuple[Decimal, Decimal]:
        return self._usable().depth_within_bps(bps)

    def mid(self) -> Decimal:
        return self._usable().mid()

    def _usable(self) -> OrderBook:
        """The one thing the service knows that the book does not: whether
        there is a book at all.

        Refusing an *invalid* book is `OrderBook`'s own job, and every read
        there already does it. Checking again here read as defence in depth
        and was the opposite: with two guards over one property, removing
        either changed no result and no test noticed. The backtest work
        (REQ-WP-010) found the same shape.
        """
        if self.book is None:
            raise BookInvalid(
                "the book has not bootstrapped: deltas alone cannot say what "
                "rests at prices no delta has mentioned"
            )
        return self.book
