"""US5: mixed spot and perpetual instruments keep their consensuses apart (REQ-WP-091).

FR-006 pins the rule this spec chose for mixed instrument types: consensus is
taken **per market type** -- spot venues together, perpetual venues together,
never blended -- and the viewed venue's basis is measured against the consensus
of *its own* type. A median over a spot mid and two perpetual mids would fold
the spot-perp basis into the thing called "consensus" (§17.1's "normalized
mids" never asked for that), and the number would then move for a reason that
has nothing to do with the venue.

The rule is read end-to-end through the two endpoints that serve it, over the
rows the consensus pass would have written (`channelflow.tables.consensus` and
`channelflow.tables.quotes`):

* `GET /api/v1/consensus` -- which consensus a chart's `venue`/`symbol` asks
  for is resolved by the registry (`routes._market_type`), never by the
  request;
* `GET /api/v1/features/timeseries` -- whose merged `venue_basis_bps` is PRD
  §17.3's `10000 * (mid_i / consensus_mid - 1)` over that same type's
  consensus.

Every median and every basis below is computed by hand from the seeded
decimals, and so is every number a *blended* rule would produce: a regression
that mixes the types therefore fails on a number, not on a comment.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from channelflow.api import LakehouseRepository, create_app
from channelflow.lakehouse import Catalog
from channelflow.tables import consensus, quotes

#: §28.2's `timeframe_ns` is the bar width; the spec's own example is 15m.
TIMEFRAME_NS = 15 * 60 * 1_000_000_000
#: Two bar closes one bar apart, aligned to the bar width so no bar lands
#: mid-way through another. A fixed instant rather than a clock reading: the
#: suite must pass in 2030 as it does today (replay and live are one code path).
BASE_NS = 1_788_838_800_000_000_000 // TIMEFRAME_NS * TIMEFRAME_NS
BAR_1, BAR_2 = (BASE_NS + i * TIMEFRAME_NS for i in range(1, 3))

#: What the consensus pass stored for BTCUSDT per type: two medians that are
#: apart by roughly 68 dollars, which is the spot-perp basis itself -- the
#: quantity a blended consensus would quietly absorb.
SPOT_MID_1 = Decimal("65432.10")
SPOT_MID_2 = Decimal("65435.20")
PERP_MID_1 = Decimal("65500.00")
PERP_MID_2 = Decimal("65510.00")

#: What a blended rule would answer at each bar: the median of the spot and
#: perpetual mids together (with two values, also their mean). FR-006 forbids
#: it, so neither endpoint may ever serve these numbers.
BLENDED_1 = Decimal("65466.05")  # (65432.10 + 65500.00) / 2
BLENDED_2 = Decimal("65472.60")  # (65435.20 + 65510.00) / 2
#: The other shape a blend takes: one pool of all four mids, median taken.
BLENDED_FOUR = Decimal("65467.60")  # (65435.20 + 65500.00) / 2

SPOT_ROWS: tuple[consensus.Consensus, ...] = (
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="spot",
        bar_close_ns=BAR_1,
        consensus_mid=SPOT_MID_1,
        venue_count=2,
        refusal_reason="",
    ),
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="spot",
        bar_close_ns=BAR_2,
        consensus_mid=SPOT_MID_2,
        venue_count=3,
        refusal_reason="",
    ),
)

PERP_ROWS: tuple[consensus.Consensus, ...] = (
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="perp",
        bar_close_ns=BAR_1,
        consensus_mid=PERP_MID_1,
        venue_count=2,
        refusal_reason="",
    ),
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="perp",
        bar_close_ns=BAR_2,
        consensus_mid=PERP_MID_2,
        venue_count=2,
        refusal_reason="",
    ),
)

#: The viewed venues' own mids at those closes: above and below their
#: consensus on the first bar respectively, so a sign error cannot hide
#: behind both being on the same side.
BINANCE_MID_1 = Decimal("65440.00")
BINANCE_MID_2 = Decimal("65427.00")
BYBIT_MID_1 = Decimal("65490.00")
BYBIT_MID_2 = Decimal("65525.00")

#: §17.3 by hand, each venue against **its own type's** consensus.
#: 10000 * (65440.00 / 65432.10 - 1) = 1.2073584677856892...
BASIS_BINANCE_1 = 1.2073584677856892
#: 10000 * (65427.00 / 65435.20 - 1) = -1.2531481526762354...
BASIS_BINANCE_2 = -1.2531481526762354
#: 10000 * (65490.00 / 65500.00 - 1) = -1.5267175572519085...
BASIS_BYBIT_1 = -1.5267175572519085
#: 10000 * (65525.00 / 65510.00 - 1) = 2.2897267592733934...
BASIS_BYBIT_2 = 2.2897267592733934

#: What the same mids would produce against the **other** type's consensus --
#: the numbers a blended rule would serve. Neither view may show them.
CROSS_BINANCE_VS_PERP = -9.16030534351145  # 10000 * (65440.00 / 65500.00 - 1)
CROSS_BYBIT_VS_SPOT = 8.848867757568533  # 10000 * (65490.00 / 65432.10 - 1)

#: An asset with a single spot venue: the pass refuses rather than publishing
#: that venue's mid under a better name, so the row carries the reason and no
#: price at all.
SINGLE_ASSET = "ETHUSDT"
SINGLE_MID_1 = Decimal("3210.55")
SINGLE_MID_2 = Decimal("3211.10")


def refused(bar_close_ns: int) -> consensus.Consensus:
    """One bar of an asset whose market type has fewer than two venues."""
    return consensus.Consensus(
        asset=SINGLE_ASSET,
        market_type="spot",
        bar_close_ns=bar_close_ns,
        consensus_mid=None,
        venue_count=1,
        refusal_reason="one_venue",
    )


def quote(venue: str, symbol: str, mid: Decimal, ts_ns: int) -> quotes.Quote:
    """One viewed-venue quote at a bar close: `ts_ns` is the close itself.

    A quote *at* the close is available at it (`<= at_ns`, the spec's edge
    case), and `ingest_ns` trails `ts_ns` rather than replacing it -- receive
    time says how old the observation was when it arrived and never decides
    availability (Principle II).
    """
    return quotes.Quote(
        venue=venue,
        symbol=symbol,
        bid=mid - Decimal("0.05"),
        ask=mid + Decimal("0.05"),
        mid=mid,
        ts_ns=ts_ns,
        ingest_ns=ts_ns + 1,
    )


def client(
    catalog: Catalog,
    *,
    markets: tuple[tuple[str, str, str], ...],
    consensus_rows: tuple[consensus.Consensus, ...],
    quote_rows: tuple[quotes.Quote, ...] = (),
) -> TestClient:
    """The app over a repository holding the seeded markets, rows and quotes.

    `markets` is `(venue, symbol, market_type)` per registry entry: the route
    resolves which consensus a view asks for through these rows, so seeding
    them is how the fixture states that binance quotes BTCUSDT spot while
    bybit quotes the same symbol as a perpetual.
    """
    repo = LakehouseRepository(catalog=catalog)
    for venue, symbol, market_type in markets:
        repo.add_market(venue=venue, symbol=symbol, market_type=market_type)
    consensus.table_for(catalog).append([consensus.to_row(row) for row in consensus_rows])
    if quote_rows:
        quotes.table_for(catalog).append([quotes.to_row(row) for row in quote_rows])
    return TestClient(create_app(repository=repo))


def consensus_bars(c: TestClient, *, venue: str, symbol: str) -> list[dict[str, object]]:
    """`GET /consensus`'s rows for one view, or an assertion on how it failed."""
    response = c.get(
        "/api/v1/consensus",
        params={"venue": venue, "symbol": symbol, "timeframe_ns": TIMEFRAME_NS, "window": "24h"},
    )
    assert response.status_code == 200, response.text
    return response.json()["consensus"]


def basis(c: TestClient, *, venue: str, symbol: str) -> dict[int, float]:
    """`venue_basis_bps` per bar close from the merged feature series."""
    response = c.get(
        "/api/v1/features/timeseries",
        params={
            "venue": venue,
            "symbol": symbol,
            "timeframe_ns": TIMEFRAME_NS,
            "start_ns": BAR_1,
            "end_ns": BAR_2,
        },
    )
    assert response.status_code == 200, response.text
    found: dict[int, float] = {}
    for point in response.json()["points"]:
        values = point.get("values")
        if not isinstance(values, dict) or "venue_basis_bps" not in values:
            continue
        # The bar's close under either name the contract and the series use.
        at = point.get("at_ns", point.get("bar_close_ns"))
        assert at is not None, point
        found[int(at)] = float(values["venue_basis_bps"])
    return found


@pytest.mark.trace("REQ-WP-091")
def test_spot_and_perp_consensus_are_separate(catalog: Catalog) -> None:
    """FR-006 / US5.1: one asset, two consensuses -- and neither is a blend.

    The same symbol is registered once as spot (binance) and once as a
    perpetual (bybit), and the table holds both types' medians for both bars.
    Each view must answer with exactly its own type's two numbers: not the
    other type's, not four pooled rows, and not the blended median a rule
    that ignored `market_type` would compute.
    """
    c = client(
        catalog,
        markets=(("binance", "BTCUSDT", "spot"), ("bybit", "BTCUSDT", "perp")),
        consensus_rows=SPOT_ROWS + PERP_ROWS,
    )

    spot_bars = consensus_bars(c, venue="binance", symbol="BTCUSDT")
    perp_bars = consensus_bars(c, venue="bybit", symbol="BTCUSDT")

    spot_mids = [b["consensus_mid"] for b in spot_bars]
    perp_mids = [b["consensus_mid"] for b in perp_bars]

    # Two bars, in order, each with its own type's median -- a read that
    # ignored the type would return four rows for two bar closes.
    assert [int(b["bar_close_ns"]) for b in spot_bars] == [BAR_1, BAR_2]
    assert [int(b["bar_close_ns"]) for b in perp_bars] == [BAR_1, BAR_2]
    assert spot_mids == [str(SPOT_MID_1), str(SPOT_MID_2)]
    assert perp_mids == [str(PERP_MID_1), str(PERP_MID_2)]

    # The two consensuses differ: the spot-perp basis is real, which is the
    # whole reason FR-006 keeps them apart.
    assert spot_mids != perp_mids

    # And neither answer is a blend of the two types -- not at either bar,
    # not from one pool of all four mids.
    for blended in (BLENDED_1, BLENDED_2, BLENDED_FOUR):
        assert str(blended) not in spot_mids
        assert str(blended) not in perp_mids


@pytest.mark.trace("REQ-WP-091")
def test_viewed_venue_uses_its_own_type(catalog: Catalog) -> None:
    """FR-006 / US5.2: §17.3's basis of the viewed venue, per market type.

    binance (spot) is measured against the spot consensus and bybit (perp)
    against the perpetual one -- both numbers computed here by hand from the
    seeded decimals. Measured against the *other* type's consensus the same
    mids would give -9.16 and +8.85 bps, and neither view may show those.
    """
    c = client(
        catalog,
        markets=(("binance", "BTCUSDT", "spot"), ("bybit", "BTCUSDT", "perp")),
        consensus_rows=SPOT_ROWS + PERP_ROWS,
        quote_rows=(
            quote("binance", "BTCUSDT", BINANCE_MID_1, BAR_1),
            quote("binance", "BTCUSDT", BINANCE_MID_2, BAR_2),
            quote("bybit", "BTCUSDT", BYBIT_MID_1, BAR_1),
            quote("bybit", "BTCUSDT", BYBIT_MID_2, BAR_2),
        ),
    )

    spot_basis = basis(c, venue="binance", symbol="BTCUSDT")
    perp_basis = basis(c, venue="bybit", symbol="BTCUSDT")

    # One point per bar, for both views.
    assert sorted(spot_basis) == [BAR_1, BAR_2]
    assert sorted(perp_basis) == [BAR_1, BAR_2]

    # Hand-computed against each venue's own type's consensus.
    assert spot_basis[BAR_1] == pytest.approx(BASIS_BINANCE_1, abs=1e-9)
    assert spot_basis[BAR_2] == pytest.approx(BASIS_BINANCE_2, abs=1e-9)
    assert perp_basis[BAR_1] == pytest.approx(BASIS_BYBIT_1, abs=1e-9)
    assert perp_basis[BAR_2] == pytest.approx(BASIS_BYBIT_2, abs=1e-9)

    # The blend check in numbers: the cross-type denominators would give these,
    # and the distance between them and what is served is far beyond tolerance.
    assert abs(spot_basis[BAR_1] - CROSS_BINANCE_VS_PERP) > 1.0
    assert abs(perp_basis[BAR_1] - CROSS_BYBIT_VS_SPOT) > 1.0


@pytest.mark.trace("REQ-WP-091")
def test_single_venue_type_refuses(catalog: Catalog) -> None:
    """FR-006's edge case: one venue in a market type refuses, in both reads.

    The consensus row exists with `venue_count` below two and its reason and
    no price -- a gap the chart can explain. The viewed venue's basis is then
    *absent*, never zero: the quote is seeded at both closes, so an empty
    series is the refusal speaking rather than a missing observation, and
    zero would claim agreement where there was nothing to agree with.
    """
    c = client(
        catalog,
        markets=(("kraken", SINGLE_ASSET, "spot"),),
        consensus_rows=(refused(BAR_1), refused(BAR_2)),
        quote_rows=(
            quote("kraken", SINGLE_ASSET, SINGLE_MID_1, BAR_1),
            quote("kraken", SINGLE_ASSET, SINGLE_MID_2, BAR_2),
        ),
    )

    bars = consensus_bars(c, venue="kraken", symbol=SINGLE_ASSET)
    assert [int(b["bar_close_ns"]) for b in bars] == [BAR_1, BAR_2]
    for bar in bars:
        assert bar["venue_count"] < 2
        assert bar["consensus_mid"] is None
        assert isinstance(bar["refusal_reason"], str) and bar["refusal_reason"]

    # Silence, not zero: no point at either close.
    assert basis(c, venue="kraken", symbol=SINGLE_ASSET) == {}
