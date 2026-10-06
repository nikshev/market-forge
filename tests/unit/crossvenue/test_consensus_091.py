"""US1 acceptance for REQ-WP-091 — consensus mid correctness at a bar's close.

The library under test is `channelflow.crossvenue.consensus_mid`, built by
REQ-WP-016 and deliberately left untouched here: this file pins the same
behaviour to REQ-WP-091's acceptance scenarios (SC-001, SC-002, FR-001), so
the chart layer built on top of it inherits a checked contract rather than an
assumed one.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.assets import AssetRegistry, VenueKind
from channelflow.crossvenue import NoConsensus, VenueQuote, consensus_mid

from .conftest import BINANCE_KEY, at, quote


@pytest.mark.trace("REQ-WP-091")
def test_two_venues_median_is_interpolated(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """US1 scenario 1, SC-001: two order-book venues, 3000 and 2999.

    An even contributor count has no middle observation, so the median is the
    mean of the two and `interpolated` says so — a reader comparing consensus
    figures across instants must know which they are looking at.
    """
    quotes = [q for q in three_venues if q.kind is VenueKind.ORDER_BOOK]

    result = consensus_mid(quotes, registry=registry, at_ns=at(12))

    assert result.contributors == ("binance", "okx")
    assert result.contributor_count == 2
    assert result.mid == (quotes[0].mid + quotes[1].mid) / 2 == Decimal("2999.5")
    assert result.interpolated is True


@pytest.mark.trace("REQ-WP-091")
def test_three_venues_median(registry: AssetRegistry, three_venues: list[VenueQuote]) -> None:
    """US1 scenario 2, SC-001: mids 2999, 3000, 3010 — median 3000, observed
    rather than interpolated, with nobody excluded.

    `consensus_mid` does not filter AMM venues out of the consensus (only
    `basis_bps` refuses an AMM), so all three quote the same asset and all
    three contribute.
    """
    result = consensus_mid(three_venues, registry=registry, at_ns=at(12))

    assert result.contributors == ("binance", "okx", "uniswap")
    assert result.contributor_count == 3
    assert result.mid == Decimal("3000")
    assert result.interpolated is False
    assert result.excluded == {}


@pytest.mark.trace("REQ-WP-091")
def test_stale_quote_excluded_with_reason(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """US1 scenario 3, SC-001: a quote older than the staleness tolerance is
    dropped and the reason says which threshold it crossed.

    OKX is observed at t-10s while the instant asked about is t+12s, so the
    quote is 22s old against a 5s tolerance. Binance and Uniswap remain.
    """
    quotes = [three_venues[0], quote("okx", "2999", second=-10), three_venues[2]]

    result = consensus_mid(quotes, registry=registry, at_ns=at(12))

    assert "okx" not in result.contributors
    assert result.contributor_count == 2
    assert "okx" in result.excluded
    assert "tolerance" in result.excluded["okx"]


@pytest.mark.trace("REQ-WP-091")
def test_future_quote_excluded(registry: AssetRegistry, three_venues: list[VenueQuote]) -> None:
    """US1 scenario 4, SC-001, Principle I: a quote later than the instant
    asked about cannot contribute to that instant, however fresh it looks.

    The consensus at t+12s is then the median of the two quotes that existed
    at that moment, not a number the future moved.
    """
    quotes = [
        three_venues[0],
        three_venues[1],
        quote("uniswap", "9999", second=60, kind=VenueKind.AMM_POOL),
    ]

    result = consensus_mid(quotes, registry=registry, at_ns=at(12))

    assert "uniswap" not in result.contributors
    assert "uniswap" in result.excluded
    assert "later than the instant" in result.excluded["uniswap"]
    assert result.contributors == ("binance", "okx")
    assert result.mid == Decimal("2999.5")
    assert result.interpolated is True


@pytest.mark.trace("REQ-WP-091")
def test_one_venue_refuses(registry: AssetRegistry) -> None:
    """US1 scenario 5, SC-001: one venue gives no consensus.

    A median over one venue is that venue's mid wearing a better name, so the
    line is absent rather than quietly drawn from a single opinion.
    """
    with pytest.raises(NoConsensus):
        consensus_mid([quote("binance", "3000")], registry=registry, at_ns=at(12))


@pytest.mark.trace("REQ-WP-091")
def test_consensus_unchanged_when_later_quotes_appended(
    registry: AssetRegistry, three_venues: list[VenueQuote]
) -> None:
    """US1 scenario 6, SC-002, Principle I: the consensus at bar time `t` is
    unchanged when quotes later than `t` are appended.

    The chart computes each bar's consensus at that bar's close; appending a
    future quote must move neither the value nor the set of contributors, or
    replayed history would differ from what was known live.
    """
    before = consensus_mid(three_venues, registry=registry, at_ns=at(12))
    with_later = [*three_venues, quote("bybit", "65100", second=60, key=BINANCE_KEY)]

    after = consensus_mid(with_later, registry=registry, at_ns=at(12))

    assert after.mid == before.mid
    assert after.contributors == before.contributors
    assert after.interpolated == before.interpolated
    assert after.excluded["bybit"] == "quote is later than the instant asked about"
