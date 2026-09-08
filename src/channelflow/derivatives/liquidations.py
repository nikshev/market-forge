"""PRD section 16.4's liquidation aggregates.

# @trace: REQ-WP-013

Forced selling is not ordinary selling: it arrives without regard to price and
stops when the position is gone. Aggregating it separately from volume is the
point of the family.

Every window here is event-time, and the clusters are the one place a
configurable bucket size matters -- too fine and every print is its own
cluster, too coarse and the structure disappears.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from channelflow.derivatives.state import ratio
from channelflow.domain import LiquidationEvent


@dataclass(frozen=True)
class LiquidationWindow:
    """What was forced out in a span of event time."""

    long_usd: Decimal
    short_usd: Decimal
    events: int
    window_ns: int
    as_of_ns: int

    @property
    def total_usd(self) -> Decimal:
        return self.long_usd + self.short_usd

    @property
    def imbalance(self) -> float | None:
        """Which side was liquidated more, normalized. Absent when neither was.

        Zero would mean "both sides equally", which is a fact about a busy
        window, not about a quiet one.
        """
        return ratio(float(self.long_usd - self.short_usd), float(self.total_usd))


def window(events: list[LiquidationEvent], *, as_of_ns: int, window_ns: int) -> LiquidationWindow:
    """Everything liquidated in `(as_of_ns - window_ns, as_of_ns]`."""
    floor = as_of_ns - window_ns
    inside = [e for e in events if floor < e.meta.event_time_ns <= as_of_ns]
    return LiquidationWindow(
        long_usd=sum((e.notional_usd for e in inside if e.side == "long_liquidated"), Decimal(0)),
        short_usd=sum((e.notional_usd for e in inside if e.side == "short_liquidated"), Decimal(0)),
        # A zero-notional print counts as an event: it is a data-quality signal,
        # not an absence.
        events=len(inside),
        window_ns=window_ns,
        as_of_ns=as_of_ns,
    )


def intensity(liquidated_usd: Decimal, traded_volume_usd: Decimal) -> float | None:
    """Liquidation notional as a fraction of turnover. Absent on no volume."""
    return ratio(float(liquidated_usd), float(traded_volume_usd))


def clusters(
    events: list[LiquidationEvent], *, bucket_bps: float = 25.0, reference_price: Decimal
) -> dict[int, Decimal]:
    """Liquidated notional by price bucket, keyed by bucket index from the
    reference price.

    Buckets are relative rather than absolute, so the same configuration works
    at any price level -- an absolute bucket size tuned on one symbol is
    meaningless on another.
    """
    if reference_price <= 0:
        return {}
    grouped: dict[int, Decimal] = {}
    width = float(reference_price) * bucket_bps / 10_000.0
    for event in events:
        offset = float(event.price - reference_price)
        index = int(offset // width)
        grouped[index] = grouped.get(index, Decimal(0)) + event.notional_usd
    return grouped


def time_since_spike(
    events: list[LiquidationEvent], *, as_of_ns: int, spike_usd: Decimal
) -> int | None:
    """Event-time distance to the last print above the threshold.

    `None` means no spike has been seen, which is different from a spike
    infinitely long ago -- and a caller plotting the latter would draw a line
    at whatever sentinel we picked.
    """
    spikes = [
        e.meta.event_time_ns
        for e in events
        if e.notional_usd >= spike_usd and e.meta.event_time_ns <= as_of_ns
    ]
    return as_of_ns - max(spikes) if spikes else None
