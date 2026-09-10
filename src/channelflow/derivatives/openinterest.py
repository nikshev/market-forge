"""PRD sections 16.2 and 16.3: open interest, and the gap between perp and spot.

# @trace: REQ-WP-013
# @trace: REQ-WP-026

Section 16.2's four-quadrant matrix is here, and ADR-027 is why nothing acts on
it. The PRD's own words: "Interpretation matrix stored as feature, not
hard-coded trading truth." The names below are its names, kept verbatim --
including the word "candidate" in each, which is the PRD hedging its own matrix
and which survives copy-paste into a dashboard where "new shorts" alone would
read as a fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from channelflow.derivatives.state import (
    DEFAULT_STALENESS_NS,
    ZScore,
    ratio,
    require_fresh,
    z_score,
)
from channelflow.domain import DerivativesState

BPS = 10_000.0


class PriceOIRegime(StrEnum):
    """PRD section 16.2's four quadrants, verbatim."""

    NEW_RISK_ENTERING = "new risk entering / trend participation candidate"
    SHORT_COVERING = "short-covering candidate"
    NEW_SHORTS = "new shorts / risk build candidate"
    LONG_LIQUIDATION = "long liquidation/de-risk candidate"
    #: Not in the PRD, and necessary: a flat leg is in none of the four
    #: quadrants, and forcing it into one would invent a reading.
    UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class OpenInterestPoint:
    at_ns: int
    open_interest_usd: float


def oi_series(
    states: list[DerivativesState],
    *,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> list[OpenInterestPoint]:
    """Open interest in USD, at or before `at_ns`, oldest first.

    States reporting base units only are skipped: multiplying by a price we
    chose would invent a figure the venue did not report.

    Refuses when the newest point is older than `staleness_ns`: a poll that
    failed leaves the last figure in place, and without the bound every reading
    below reports it as open interest now ([[REQ-WP-026]]).
    """
    points = [
        OpenInterestPoint(at_ns=s.meta.event_time_ns, open_interest_usd=s.open_interest_usd)
        for s in states
        if s.open_interest_usd is not None and s.meta.event_time_ns <= at_ns
    ]
    ordered = sorted(points, key=lambda p: p.at_ns)
    if ordered:
        require_fresh(ordered[-1].at_ns, at_ns=at_ns, staleness_ns=staleness_ns)
    return ordered


def oi_change(
    states: list[DerivativesState],
    *,
    at_ns: int,
    window_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> float | None:
    """Change in open interest across a window, in USD.

    Measured from the last observation at or before the window's start, not
    from the first observation inside it: a window that opens in a gap should
    compare against what was actually known then.
    """
    points = oi_series(states, at_ns=at_ns, staleness_ns=staleness_ns)
    if not points:
        return None
    start = at_ns - window_ns
    earlier = [p for p in points if p.at_ns <= start]
    if not earlier:
        return None
    return points[-1].open_interest_usd - earlier[-1].open_interest_usd


def oi_z(
    states: list[DerivativesState],
    *,
    at_ns: int,
    window: int = 20,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> ZScore:
    return z_score(
        [p.open_interest_usd for p in oi_series(states, at_ns=at_ns, staleness_ns=staleness_ns)],
        window=window,
    )


def oi_to_volume(open_interest_usd: float, volume_usd: float) -> float | None:
    """How much open risk there is per unit of turnover. Absent on no volume."""
    return ratio(open_interest_usd, volume_usd)


def price_oi_regime(*, price_change: float, oi_change_usd: float) -> PriceOIRegime:
    """PRD section 16.2's matrix, as a label.

    ADR-027: this is returned and stored. Nothing in this package branches on
    it, and a signal rule that did would encode folklore as a threshold --
    invisible, because it would look like domain knowledge.
    """
    if price_change == 0.0 or oi_change_usd == 0.0:
        return PriceOIRegime.UNDETERMINED
    if price_change > 0:
        return (
            PriceOIRegime.NEW_RISK_ENTERING if oi_change_usd > 0 else PriceOIRegime.SHORT_COVERING
        )
    return PriceOIRegime.NEW_SHORTS if oi_change_usd > 0 else PriceOIRegime.LONG_LIQUIDATION


def basis_bps(*, perp_price: Decimal | None, spot_price: Decimal | None) -> float | None:
    """PRD section 16.3: perp against spot, relative to spot."""
    if perp_price is None or spot_price is None or spot_price == 0:
        return None
    return float((perp_price - spot_price) / spot_price) * BPS


def mark_premium_bps(*, mark_price: Decimal | None, index_price: Decimal | None) -> float | None:
    """Mark against index, relative to the index."""
    if mark_price is None or index_price is None or index_price == 0:
        return None
    return float((mark_price - index_price) / index_price) * BPS
