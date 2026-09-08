"""PRD section 17.1's consensus price, and section 17.3's basis.

# @trace: REQ-WP-016

    "Create robust consensus mid from selected high-liquidity venues."
    `basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)`

Two refusals carry most of the weight here.

A consensus over fewer than two venues is refused: a median of one is that
venue's mid wearing a better name, and every consumer downstream would read
agreement where there was one opinion.

Mid-based basis is refused when a side is an AMM. Section 18.14: "Never compare
a CEX top-of-book quote against an AMM infinitesimal spot quote and call it
arbitrage." The refusal is the rule; a caption on the number would not travel
with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from channelflow.assets import AssetRegistry, UnknownAsset, VenueKind
from channelflow.crossvenue.models import VenueQuote

BPS = Decimal(10_000)

#: How old a quote may be and still contribute. Configuration, like every other
#: threshold here (Principle X).
DEFAULT_STALENESS_NS = 5 * 1_000_000_000


class NoConsensus(ValueError):
    """Fewer than two venues could contribute."""


class NotComparable(ValueError):
    """Quotes name representations of different canonical assets."""


class MidBasisRefused(ValueError):
    """Section 18.14: a mid-based comparison involving an AMM."""


@dataclass(frozen=True)
class Consensus:
    """The agreed mid, and an honest account of who agreed."""

    mid: Decimal
    contributors: tuple[str, ...]
    #: True when the contributor count was even, so the median is the mean of
    #: two observations rather than one of them. A reader comparing consensus
    #: figures across instants should know which they have.
    interpolated: bool
    excluded: dict[str, str]

    @property
    def contributor_count(self) -> int:
        return len(self.contributors)


def consensus_mid(
    quotes: list[VenueQuote],
    *,
    registry: AssetRegistry,
    at_ns: int,
    staleness_ns: int = DEFAULT_STALENESS_NS,
) -> Consensus:
    """The median of the contributing venues' mids (section 17.1)."""
    excluded: dict[str, str] = {}
    eligible: list[VenueQuote] = []

    for quote in quotes:
        if quote.observed_at_ns > at_ns:
            excluded[quote.venue_id] = "quote is later than the instant asked about"
            continue
        if at_ns - quote.observed_at_ns > staleness_ns:
            excluded[quote.venue_id] = (
                f"quote is {at_ns - quote.observed_at_ns}ns old, past the "
                f"{staleness_ns}ns tolerance"
            )
            continue
        eligible.append(quote)

    _require_one_asset(eligible, registry=registry)

    if len(eligible) < 2:
        raise NoConsensus(
            f"only {len(eligible)} venue(s) could contribute at {at_ns}; a median "
            "over one venue is that venue's mid wearing a better name"
        )

    ordered = sorted(eligible, key=lambda q: q.mid)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        mid = ordered[middle].mid
        interpolated = False
    else:
        mid = (ordered[middle - 1].mid + ordered[middle].mid) / 2
        interpolated = True

    return Consensus(
        mid=mid,
        contributors=tuple(sorted(q.venue_id for q in eligible)),
        interpolated=interpolated,
        excluded=excluded,
    )


def _require_one_asset(quotes: list[VenueQuote], *, registry: AssetRegistry) -> None:
    """Comparability comes from the registry, never from tickers.

    Section 18.13's prohibition, enforced at the one place two venues meet. A
    consensus across a real asset and a bridged lookalike reports agreement
    that does not exist.
    """
    assets = set()
    for quote in quotes:
        try:
            assets.add(registry.canonical_asset(quote.representation_key).asset_id)
        except UnknownAsset as exc:
            raise NotComparable(
                f"venue {quote.venue_id!r} quotes representation "
                f"{quote.representation_key!r}, which the registry does not know"
            ) from exc
    if len(assets) > 1:
        raise NotComparable(
            f"quotes span {len(assets)} canonical assets ({', '.join(sorted(assets))}); "
            "a consensus across different assets reports agreement that does not exist"
        )


def basis_bps(quote: VenueQuote, consensus: Consensus) -> float:
    """Section 17.3's formula, for order-book venues only.

    Refused for an AMM (section 18.14). An AMM's mid is its price at
    infinitesimal size, and comparing it to a book's top of book is the
    comparison the PRD names outright.
    """
    if quote.kind is not VenueKind.ORDER_BOOK:
        raise MidBasisRefused(
            f"venue {quote.venue_id!r} is {quote.kind.value}; PRD section 18.14 "
            "forbids comparing an AMM's infinitesimal spot quote against a "
            "top-of-book mid. Use executable_basis_bps with a notional instead"
        )
    return float((quote.mid / consensus.mid - 1) * BPS)


def executable_basis_bps(*, venue_price: Decimal, reference_price: Decimal) -> float:
    """Section 18.14's comparable basis, at a notional the caller chose.

        executable_basis_bps(N) = 10000 * (px(N) / reference_px(N) - 1)

    Both prices are executable at the same size. There is no default size: the
    right one depends on what the answer is for, and a default would be a
    trading assumption hidden in a helper (ADR-039).
    """
    if reference_price <= 0:
        raise ValueError("reference price must be positive")
    return float((venue_price / reference_price - 1) * BPS)
