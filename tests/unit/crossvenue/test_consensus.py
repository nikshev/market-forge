"""PRD sections 17.1 and 17.3 (REQ-WP-016)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.assets import AssetRegistry, VenueKind
from channelflow.crossvenue import (
    MidBasisRefused,
    NoConsensus,
    NotComparable,
    VenueQuote,
    basis_bps,
    consensus_mid,
    executable_basis_bps,
)

from .conftest import at, quote


@pytest.mark.trace("REQ-WP-016")
def test_the_consensus_is_the_median_and_names_its_contributors(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """SC-001, FR-001. Mids 2999, 3000, 3010 — median 3000."""
    result = consensus_mid(three_venues, registry=registry, at_ns=at(12))

    assert result.mid == Decimal("3000")
    assert result.contributors == ("binance", "okx", "uniswap")
    assert result.contributor_count == 3
    assert not result.interpolated


@pytest.mark.trace("REQ-WP-016")
def test_a_stale_venue_does_not_contribute(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """SC-002, FR-002. The tolerance is five seconds; OKX's quote is twenty
    seconds old at the instant asked about."""
    stale = [*three_venues[:1], quote("okx", "2999", second=-10), three_venues[2]]

    result = consensus_mid(stale, registry=registry, at_ns=at(12))

    assert "okx" not in result.contributors
    assert result.contributor_count == 2
    assert "okx" in result.excluded and "tolerance" in result.excluded["okx"]


@pytest.mark.trace("REQ-WP-016")
def test_a_quote_from_after_the_instant_does_not_contribute(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """FR-015, Principle I. A consensus at `t` cannot include a quote from
    `t + 1`, however fresh it looks."""
    future = [*three_venues[:2], quote("uniswap", "9999", second=60, kind=VenueKind.AMM_POOL)]

    result = consensus_mid(future, registry=registry, at_ns=at(12))

    assert "uniswap" not in result.contributors
    assert result.mid < Decimal("3001")


@pytest.mark.trace("REQ-WP-016")
def test_fewer_than_two_contributors_is_refused(registry: AssetRegistry) -> None:
    """SC-003, FR-003.

    A median over one venue is that venue's mid wearing a better name, and
    every consumer downstream would read agreement where there was one opinion.
    """
    with pytest.raises(NoConsensus, match="better name"):
        consensus_mid([quote("binance", "3000")], registry=registry, at_ns=at(12))


@pytest.mark.trace("REQ-WP-016")
def test_every_venue_stale_is_refused_not_zero(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """The spec's first edge case: a consensus of nothing is not zero."""
    with pytest.raises(NoConsensus):
        consensus_mid(three_venues, registry=registry, at_ns=at(600))


@pytest.mark.trace("REQ-WP-016")
def test_an_even_count_reports_that_the_median_is_interpolated(registry: AssetRegistry) -> None:
    """SC-001, FR-005, the spec's second edge case.

    A reader comparing consensus figures across instants should know whether
    the number was observed or averaged between two observations.
    """
    result = consensus_mid(
        [quote("binance", "3000"), quote("okx", "3010")], registry=registry, at_ns=at(12)
    )

    assert result.mid == Decimal("3005")
    assert result.interpolated


@pytest.mark.trace("REQ-WP-016")
def test_venues_are_comparable_through_the_registry_not_their_tickers(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """SC-004, FR-004.

    Binance quotes "ETH" and Uniswap quotes "WETH". They are comparable because
    the registry says both represent ETH — PRD section 18.13's whole purpose.
    """
    tickers = {registry.representations[q.representation_key].ticker for q in three_venues}

    assert tickers == {"ETH", "WETH"}, "the tickers differ"
    assert consensus_mid(three_venues, registry=registry, at_ns=at(12)).contributor_count == 3


@pytest.mark.trace("REQ-WP-016")
def test_venues_quoting_different_assets_are_refused(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """SC-004, the spec's third edge case.

    Comparing across assets is the mistake the registry exists to prevent, and
    a consensus is where two venues meet — so this is where it is caught.
    """
    wrong = [*three_venues[:2], quote("other", "60000", key="0:0xbtc")]

    with pytest.raises(NotComparable, match="different assets"):
        consensus_mid(wrong, registry=registry, at_ns=at(12))


@pytest.mark.trace("REQ-WP-016")
def test_a_quote_the_registry_does_not_know_is_refused(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """FR-004. An unregistered representation cannot be shown comparable to
    anything, and assuming it is would be merging by hope."""
    unknown = [*three_venues[:2], quote("ghost", "3000", key="0:0xnowhere")]

    with pytest.raises(NotComparable, match="does not know"):
        consensus_mid(unknown, registry=registry, at_ns=at(12))


@pytest.mark.trace("REQ-WP-016")
def test_basis_matches_the_formula(registry: AssetRegistry, three_venues: list[VenueQuote]) -> None:
    """SC-005, FR-006. `10000 * (2999 / 3000 - 1)` is -3.333... bps."""
    result = consensus_mid(three_venues, registry=registry, at_ns=at(12))

    assert basis_bps(quote("okx", "2999"), result) == pytest.approx(-10_000 / 3000)
    assert basis_bps(quote("binance", "3000"), result) == pytest.approx(0.0)


@pytest.mark.trace("REQ-WP-016")
def test_mid_basis_is_refused_for_an_amm(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """SC-006, FR-007, PRD section 18.14:

        "Never compare a CEX top-of-book quote against an AMM infinitesimal
         spot quote and call it arbitrage."

    Refused rather than computed with a caption: a caption does not travel with
    a number.
    """
    result = consensus_mid(three_venues, registry=registry, at_ns=at(12))
    amm = quote("uniswap", "3010", kind=VenueKind.AMM_POOL)

    with pytest.raises(MidBasisRefused, match="section 18.14"):
        basis_bps(amm, result)


@pytest.mark.trace("REQ-WP-016")
def test_executable_basis_compares_prices_at_one_size() -> None:
    """SC-006, FR-008, PRD section 18.14's comparable basis.

    3030 against 3000 is 100 bps — and both are executable at the same size,
    which is what makes the comparison legitimate at all.
    """
    assert executable_basis_bps(
        venue_price=Decimal("3030"), reference_price=Decimal("3000")
    ) == pytest.approx(100.0)


@pytest.mark.trace("REQ-WP-016")
def test_executable_basis_refuses_an_impossible_reference() -> None:
    """FR-008."""
    with pytest.raises(ValueError, match="positive"):
        executable_basis_bps(venue_price=Decimal("3000"), reference_price=Decimal("0"))
