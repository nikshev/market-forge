"""A minute of an order book, finalised in event time (REQ-WP-095).

# @trace: REQ-WP-095

The collector does not store the raw book (ADR-070): it keeps the existing `BookService` and
`OFITracker` going and, when a minute ends, stores what the minute amounted to -- the one-minute
order-flow imbalance, the ten-level depth imbalance and the top-of-book quote -- with how many
frames and observations it rested on.

**Event time, and the state before the message that closes the minute.** A minute ending at `B` is
finalised by the first message dated `B` or later, from the book *as it was before that message*:
the closing message belongs to the next minute, and a summary that included it would contain
something the market had not yet shown at `B` (Principle I). A minute with no message at all is
finalised by the clock (`tick`) with a count of zero and no value.

**A thin minute is not a balanced one.** `OFIWindow` already carries its observation count because
"zero flow and no data both read as 0". A minute with no frame stores `frames == 0` and nothing
else; a minute whose frames gave fewer than two observations has no OFI (the first observation has
nothing to difference against).

**Sampling.** The tracker is fed one observation per second of event time -- the top of the book
at that second -- whatever rate the venue pushes at, so every venue's OFI is the same measurement
(a sampled one, stated in the feature's registration), and a 20 ms stream costs no more than a 1 s
one. No observation is invented for a silent second: after a gap the next message produces one,
and the difference against the last real one is the order flow over the gap.

**A reconnect or a sequence gap breaks the baseline** (`reset`, and a gap detected by
`BookService`): the book may have moved arbitrarily meanwhile, and an increment across the break
would be flow that never happened.

**Depth.** `depth_imbalance_10` is written only for a book with ten levels on each side; a
five-level book (OKX's `books5`) has no ten-level imbalance and does not get a five-level one
under that name. A crossed book (best bid at or above best ask) is refused: it is not a quote and
not an observation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from channelflow.book.book import BookInvalid
from channelflow.book.service import BookService
from channelflow.domain import BookDelta, BookSnapshot
from channelflow.features.instant import depth_imbalance_levels
from channelflow.features.ofi import Observation, OFITracker

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS

#: How long after a minute's end the clock waits before finalising it with no message: late
#: messages for the minute still in flight are applied to the book either way, but count towards
#: the next one.
TICK_GRACE_NS = 5 * SECOND_NS

DEPTH_LEVELS = 10


@dataclass(frozen=True)
class MinuteSummary:
    """What one minute of one book amounted to."""

    venue: str
    symbol: str
    minute_close_ns: int
    frames: int
    observations: int
    ofi: Decimal | None
    depth_imbalance_10: float | None
    bid: Decimal | None
    ask: Decimal | None
    mid: Decimal | None
    #: Event time of the last message applied before the minute ended: when the quote was true.
    quote_time_ns: int | None


class MinuteBook:
    def __init__(self, *, venue: str, symbol: str) -> None:
        self.venue = venue
        self.symbol = symbol
        self._service = BookService()
        self._tracker = OFITracker()
        self._next_sample_ns: int | None = None
        self._minute_start_ns: int | None = None
        self._frames = 0
        self._last_event_ns: int | None = None
        self.needs_resync = False

    # --- feeding -------------------------------------------------------------

    def feed(self, message: BookSnapshot | BookDelta) -> list[MinuteSummary]:
        """Apply one message; return the minutes it finished, oldest first."""
        at = message.meta.event_time_ns
        out = self._finish_minutes_up_to(at)
        self._sample_up_to(at - 1)
        self._apply(message)
        if self._minute_start_ns is None:
            self._minute_start_ns = (at // MINUTE_NS) * MINUTE_NS
        self._frames += 1
        self._last_event_ns = at
        return out

    def tick(self, *, now_ns: int) -> list[MinuteSummary]:
        """Finish the minutes that ended by the clock with nothing to close them."""
        if self._minute_start_ns is None:
            return []
        return self._finish_minutes_up_to(now_ns - TICK_GRACE_NS)

    def reset(self) -> None:
        """The connection was remade: nothing of the old book or its flow carries across."""
        self._service = BookService()
        self._tracker.on_discontinuity()
        self._next_sample_ns = None
        self.needs_resync = False

    # --- internals -----------------------------------------------------------

    def _apply(self, message: BookSnapshot | BookDelta) -> None:
        if isinstance(message, BookSnapshot):
            try:
                self._service.on_snapshot(message)
            except Exception:  # noqa: BLE001 -- a snapshot that cannot bootstrap is a resync
                self.needs_resync = True
                self._tracker.on_discontinuity()
                return
            self.needs_resync = False
            return
        was_usable = self._usable()
        self._service.on_delta(message)
        if was_usable and not self._usable():
            self.needs_resync = True
            self._tracker.on_discontinuity()

    def _usable(self) -> bool:
        book = self._service.book
        return book is not None and book.health().valid

    def _touch(self) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
        """`(bid price, bid qty, ask price, ask qty)`, or `None` if there is no honest quote."""
        if not self._usable():
            return None
        bids, asks = self._service.top(1)
        if not bids or not asks:
            return None
        bid, ask = bids[0], asks[0]
        if bid.price >= ask.price:
            return None  # crossed: not a quote and not an observation
        return bid.price, bid.qty, ask.price, ask.qty

    def _sample_up_to(self, limit_ns: int) -> None:
        """One observation at the latest whole second at or before `limit_ns`, if one is due."""
        grid = (limit_ns // SECOND_NS) * SECOND_NS
        if self._next_sample_ns is not None and grid < self._next_sample_ns:
            return
        touch = self._touch()
        if touch is None:
            self._next_sample_ns = grid + SECOND_NS
            return
        self._tracker.observe(
            Observation(
                bid_price=touch[0],
                bid_qty=touch[1],
                ask_price=touch[2],
                ask_qty=touch[3],
                event_time_ns=grid,
            )
        )
        self._next_sample_ns = grid + SECOND_NS

    def _finish_minutes_up_to(self, limit_ns: int) -> list[MinuteSummary]:
        out: list[MinuteSummary] = []
        while self._minute_start_ns is not None and self._minute_start_ns + MINUTE_NS <= limit_ns:
            boundary = self._minute_start_ns + MINUTE_NS
            if self._frames > 0:
                self._sample_up_to(boundary)
            out.append(self._summarise(boundary))
            self._minute_start_ns = boundary
            self._frames = 0
        return out

    def _summarise(self, boundary: int) -> MinuteSummary:
        if self._frames == 0:
            return MinuteSummary(
                self.venue, self.symbol, boundary, 0, 0, None, None, None, None, None, None
            )
        window = self._tracker.window(MINUTE_NS, as_of_ns=boundary)
        touch = self._touch()
        bid = ask = mid = None
        if touch is not None:
            bid, ask = touch[0], touch[2]
            mid = (bid + ask) / 2
        return MinuteSummary(
            venue=self.venue,
            symbol=self.symbol,
            minute_close_ns=boundary,
            frames=self._frames,
            observations=window.observations,
            ofi=window.value if window.observations > 0 else None,
            depth_imbalance_10=self._depth_imbalance() if touch is not None else None,
            bid=bid,
            ask=ask,
            mid=mid,
            quote_time_ns=self._last_event_ns,
        )

    def _depth_imbalance(self) -> float | None:
        bids, asks = self._service.top(DEPTH_LEVELS)
        if len(bids) < DEPTH_LEVELS or len(asks) < DEPTH_LEVELS:
            return None
        try:
            return depth_imbalance_levels(self._service, DEPTH_LEVELS)
        except BookInvalid:
            return None
