"""The order-flow features as of a bar's close, from stored book minutes (REQ-WP-095).

# @trace: REQ-WP-095

Pure, like `context_values`: no table, no clock, nothing that reaches a storage backend.

**Which minute.** The latest stored minute that ended at or before the close. A minute's summary
is computed from the book as it stood *before* its closing boundary (`MinuteBook`), so it contains
nothing the market had not shown by then; it is stored a moment after the boundary, which is why
the rule here is the minute's own close and not the receipt time the derivatives states are held
to.

**Absent, not zero.** A minute with no frame writes nothing; one with fewer than two observations
has no OFI; a book with fewer than ten levels a side has no ten-level imbalance; a minute older
than `STALENESS_NS` at the close is not the value now. `OFIWindow` carries its observation count
because "zero flow and no data both read as 0", and this is where that is honoured."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence

from channelflow.tables.book_minutes import BookMinute

MINUTE_NS = 60_000_000_000

#: A minute summary is current for two minutes: the one that just ended and one missed.
STALENESS_NS = 2 * MINUTE_NS

BOOK_FEATURES: tuple[str, ...] = ("ofi_1m", "depth_imbalance_10")


def book_values(
    minutes: Sequence[BookMinute],
    *,
    close_ns: int,
    times: Sequence[int] | None = None,
    **_: object,
) -> dict[str, float]:
    """`ofi_1m` and `depth_imbalance_10` at `close_ns`; a value that cannot be is absent.

    `minutes` is sorted by minute close; `times` is the same list's close times, passed by the pass
    so the lookup is a bisect and not a scan per bar.
    """
    closes = times if times is not None else [m.minute_close_ns for m in minutes]
    i = bisect_right(closes, close_ns)
    if i == 0:
        return {}
    minute = minutes[i - 1]
    if close_ns - minute.minute_close_ns > STALENESS_NS or minute.frames == 0:
        return {}
    values: dict[str, float] = {}
    if minute.ofi is not None and minute.observations > 0:
        values["ofi_1m"] = float(minute.ofi)
    if minute.depth_imbalance_10 is not None:
        values["depth_imbalance_10"] = float(minute.depth_imbalance_10)
    return values
