"""PRD section 14.1's volume profile.

# @trace: REQ-WP-012

The section opens with the rule that gives the family its meaning: "Compute
true trade-based volume by price bins from exchange trades where available",
and then the prohibition that gives it teeth: "Do not infer buy/sell direction
from candle color if aggressor-side trades are available."

A profile built from candle direction is a different, worse measurement wearing
the same name -- and it is the easy one to write, because bars are already
aggregated. Everything here reads `TradeEvent`.

The value area's construction is ADR-028: grown from the point of control,
taking the larger neighbour, so it is contiguous and contains the POC. Neither
property follows from the 70% target, and both are what a reader assumes from
the name.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from channelflow.domain import TradeEvent

#: PRD section 14.1: "value-area percentage configurable, default 70%".
DEFAULT_VALUE_AREA = 0.70


class EmptyProfile(ValueError):
    """No trades in the window, so there is nothing to describe.

    Refused rather than returned empty: a profile with no bins has no point of
    control, and every consumer would then need its own answer to what that
    means.
    """


@dataclass(frozen=True)
class Bin:
    """One price range, and what traded in it."""

    index: int
    low: Decimal
    high: Decimal
    volume: Decimal
    buy_volume: Decimal
    sell_volume: Decimal
    trades: int

    @property
    def mid(self) -> Decimal:
        return (self.low + self.high) / 2


@dataclass(frozen=True)
class VolumeProfile:
    """The bins for a window, and where value was."""

    bins: tuple[Bin, ...]
    bin_width: Decimal
    poc_index: int
    value_area_indices: tuple[int, ...]
    #: True when the configured share could not be reached by a proper subset,
    #: so the whole profile is the value area. Small and load-bearing: a value
    #: area spanning everything looks like a wide market, and may instead mean
    #: there were four bins.
    value_area_is_whole_profile: bool
    #: True when two bins tied for most volume. The tie went to the lower
    #: price; recording it means a reader comparing two runs knows why.
    poc_tie: bool

    @property
    def total_volume(self) -> Decimal:
        return sum((b.volume for b in self.bins), Decimal(0))

    @property
    def poc(self) -> Bin:
        return self.bins[self.poc_index]

    @property
    def value_area(self) -> tuple[Bin, ...]:
        return tuple(self.bins[i] for i in self.value_area_indices)

    @property
    def vah(self) -> Decimal:
        return max(b.high for b in self.value_area)

    @property
    def val(self) -> Decimal:
        return min(b.low for b in self.value_area)


def build(
    trades: list[TradeEvent],
    *,
    bin_width: Decimal,
    value_area_share: float = DEFAULT_VALUE_AREA,
    anchor: Decimal | None = None,
) -> VolumeProfile:
    """Bin the trades and find the value area."""
    if not trades:
        raise EmptyProfile("no trades in the window")
    if bin_width <= 0:
        raise ValueError("bin_width must be positive")

    base = anchor if anchor is not None else min(t.price for t in trades)
    buckets: dict[int, list[TradeEvent]] = {}
    for trade in trades:
        # Integer division from a fixed anchor, so arrival order cannot change
        # the bins and a trade on a boundary always falls in the upper one.
        index = int((trade.price - base) // bin_width)
        buckets.setdefault(index, []).append(trade)

    ordered = sorted(buckets)
    bins = tuple(
        Bin(
            index=position,
            low=base + Decimal(index) * bin_width,
            high=base + Decimal(index + 1) * bin_width,
            volume=sum((t.qty_base for t in buckets[index]), Decimal(0)),
            # From the aggressor side, never from anything else (section 14.1).
            buy_volume=sum(
                (t.qty_base for t in buckets[index] if t.aggressor_side == "buy"), Decimal(0)
            ),
            sell_volume=sum(
                (t.qty_base for t in buckets[index] if t.aggressor_side == "sell"), Decimal(0)
            ),
            trades=len(buckets[index]),
        )
        for position, index in enumerate(ordered)
    )

    poc_index, poc_tie = _point_of_control(bins)
    indices, whole = _value_area(bins, poc_index=poc_index, share=value_area_share)
    return VolumeProfile(
        bins=bins,
        bin_width=bin_width,
        poc_index=poc_index,
        value_area_indices=indices,
        value_area_is_whole_profile=whole,
        poc_tie=poc_tie,
    )


def _point_of_control(bins: tuple[Bin, ...]) -> tuple[int, bool]:
    """The busiest bin. Ties go to the lower price, and are recorded."""
    most = max(b.volume for b in bins)
    tied = [b.index for b in bins if b.volume == most]
    return tied[0], len(tied) > 1


def _value_area(
    bins: tuple[Bin, ...], *, poc_index: int, share: float
) -> tuple[tuple[int, ...], bool]:
    """ADR-028: expand from the POC, taking the larger neighbour each step.

    Ties between the two neighbours go to the lower price -- the same direction
    the POC's own tie-break goes, so one rule covers both.
    """
    total = sum((b.volume for b in bins), Decimal(0))
    target = Decimal(str(share)) * total

    included = [poc_index]
    accumulated = bins[poc_index].volume
    low, high = poc_index, poc_index

    while accumulated < target and (low > 0 or high < len(bins) - 1):
        below = bins[low - 1].volume if low > 0 else None
        above = bins[high + 1].volume if high < len(bins) - 1 else None
        if above is None or (below is not None and below >= above):
            low -= 1
            included.append(low)
            accumulated += bins[low].volume
        else:
            high += 1
            included.append(high)
            accumulated += bins[high].volume

    return tuple(sorted(included)), len(included) == len(bins) and len(bins) > 1
