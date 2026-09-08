"""PRD section 14.1's high- and low-volume nodes.

# @trace: REQ-WP-012

A high-volume node is a shelf: price spent effort there and it tends to attract
price back. A low-volume node is a gap price moved through quickly.

Both are relative to their neighbours, not to the profile as a whole -- a
profile that is uniformly busy has no shelves in it, and one that is uniformly
thin should not have every second bin flagged. Same reasoning as REQ-WP-011's
wall detector, and the same failure if it were absolute: everything becomes a
node, so nothing is.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from channelflow.volume.profile import Bin, VolumeProfile

#: How many bins either side form the comparison. Too few and a two-bin shelf
#: hides itself; too many and local structure is averaged away.
NEIGHBOUR_BINS = 2


@dataclass(frozen=True)
class Node:
    """A bin that stands out from the bins around it."""

    kind: Literal["HVN", "LVN"]
    bin: Bin
    ratio_to_neighbours: float


def nodes(
    profile: VolumeProfile,
    *,
    high_multiple: float = 1.8,
    low_multiple: float = 0.4,
    neighbours: int = NEIGHBOUR_BINS,
) -> tuple[Node, ...]:
    """Every bin far above or far below its surroundings."""
    found: list[Node] = []
    for position, current in enumerate(profile.bins):
        around = [
            b.volume
            for offset, b in enumerate(profile.bins)
            if offset != position and abs(offset - position) <= neighbours
        ]
        if not around:
            continue
        average = sum(around, Decimal(0)) / len(around)
        if average == 0:
            continue
        ratio = float(current.volume / average)
        if ratio >= high_multiple:
            found.append(Node(kind="HVN", bin=current, ratio_to_neighbours=ratio))
        elif ratio <= low_multiple:
            found.append(Node(kind="LVN", bin=current, ratio_to_neighbours=ratio))
    return tuple(found)


def nodes_at(
    profile: VolumeProfile, prices: list[Decimal], **kwargs: object
) -> dict[Decimal, Node | None]:
    """Which node, if any, each price falls inside.

    PRD section 14.1's "node overlap with channel boundaries": pass the
    channel's upper, centre and lower and read back what each one sits on. A
    boundary resting on a high-volume shelf is a different proposition from one
    hanging over a gap, and the difference is the reason the feature exists.
    """
    found = nodes(profile, **kwargs)  # type: ignore[arg-type]
    result: dict[Decimal, Node | None] = {}
    for price in prices:
        result[price] = next(
            (n for n in found if n.bin.low <= price < n.bin.high),
            None,
        )
    return result
