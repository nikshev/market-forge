"""PRD section 17.4's fragmentation and liquidity.

# @trace: REQ-WP-016

    - depth by venue at 10/25/50bps;
    - best effective execution venue for fixed notional sizes;
    - concentration of liquidity across venues.

The second is where the section's expensive mistake lives. The venue with the
best top-of-book price and the venue with the best actual execution cost are
different venues as soon as size stops being infinitesimal, and section 18.14
forbids the comparison that conflates them. So `best_execution_venue` reads
`all_in_cost_bps` and nothing else -- there is no code path here that ranks by
price.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from channelflow.crossvenue.models import ExecutableQuote

#: Section 17.4's bands.
DEFAULT_BANDS: tuple[int, ...] = (10, 25, 50)


class NoFillableVenue(ValueError):
    """No venue can fill the size, so there is no best one."""


@dataclass(frozen=True)
class VenueDepth:
    """One venue's depth at one band, in its own executable measure."""

    venue_id: str
    band_bps: int
    depth: Decimal


@dataclass(frozen=True)
class ExecutionChoice:
    """Where to execute, why, and who could not."""

    venue_id: str
    all_in_cost_bps: float
    considered: tuple[str, ...]
    excluded: dict[str, str]


def best_execution_venue(quotes: list[ExecutableQuote]) -> ExecutionChoice:
    """The cheapest venue all in, not the one with the best headline price.

    A venue that cannot fill the size is excluded and reported rather than
    ranked last: "cannot fill" and "expensive" are different answers, and a
    ranking that mixed them would put an unusable venue above a costly one
    whenever the costly one was costly enough.
    """
    if not quotes:
        raise NoFillableVenue("no venues were offered")

    excluded = {q.venue_id: f"cannot fill {q.notional}" for q in quotes if not q.fillable}
    fillable = [q for q in quotes if q.fillable]
    if not fillable:
        raise NoFillableVenue(f"no venue can fill {quotes[0].notional}; every one was excluded")

    # Ties break by venue id so two runs over one set agree (Principle XI).
    # `fillable` guarantees `all_in_cost_bps` is not None, which mypy cannot
    # see through the property -- hence the explicit float, not an ignore.
    best = min(fillable, key=lambda q: (float(q.all_in_cost_bps or 0.0), q.venue_id))
    return ExecutionChoice(
        venue_id=best.venue_id,
        all_in_cost_bps=float(best.all_in_cost_bps or 0.0),
        considered=tuple(sorted(q.venue_id for q in fillable)),
        excluded=excluded,
    )


def concentration(depths: dict[str, Decimal]) -> float:
    """How concentrated liquidity is across venues, in [0, 1].

    The Herfindahl index of the depth shares: 1 when one venue holds
    everything, approaching 1/n when they hold equal parts. Chosen over "share
    of the largest venue" because that figure is unchanged whether the rest is
    split between two venues or twenty, and the difference is exactly what
    fragmentation means.
    """
    total = sum(depths.values(), Decimal(0))
    if total <= 0:
        return 0.0
    return float(sum((depth / total) ** 2 for depth in depths.values()))


def depth_table(
    depths: dict[str, dict[int, Decimal]], *, bands: tuple[int, ...] = DEFAULT_BANDS
) -> list[VenueDepth]:
    """Section 17.4's depth by venue at each band.

    Each venue's number comes from its own executable-depth measure --
    REQ-WP-004's for a book, REQ-WP-015's for a pool. The engine tabulates
    them; measuring is each venue's own business, because the two are not the
    same computation.
    """
    rows: list[VenueDepth] = []
    for venue_id in sorted(depths):
        for band in bands:
            value = depths[venue_id].get(band)
            if value is None:
                continue
            rows.append(VenueDepth(venue_id=venue_id, band_bps=band, depth=value))
    return rows
