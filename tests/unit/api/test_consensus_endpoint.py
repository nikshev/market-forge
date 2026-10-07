"""US2: `GET /api/v1/consensus` serves per-bar consensus mids (REQ-WP-091).

The rows come from the consensus table (`channelflow.tables.consensus`), which
is where the consensus pass writes them and where the endpoint reads them: the
lakehouse repository is built over the same catalog, so what this file seeds is
exactly what the route will be asked to serve.

Each bar's row already carries its own `bar_close_ns`, `venue_count` and
`refusal_reason`, so a refused bar is a row and not an absence -- the chart's
gap has to be able to say *why* there is no line there, and only the stored
reason can say it. `consensus_mid` is null where the consensus was refused: no
price a reader could mistake for one.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from channelflow.api import LakehouseRepository, create_app
from channelflow.lakehouse import Catalog
from channelflow.tables import consensus

#: §28.2's `timeframe_ns` is the bar width; the spec's own example is 15m.
TIMEFRAME_NS = 15 * 60 * 1_000_000_000
#: Three bar closes one hour apart, aligned to the bar width so no bar lands
#: mid-way through another. A fixed instant rather than a clock reading: the
#: suite must pass in 2030 as it does today (replay and live are one code path).
BASE_NS = 1_788_838_800_000_000_000 // TIMEFRAME_NS * TIMEFRAME_NS
BAR_1, BAR_2, BAR_3 = (BASE_NS + i * TIMEFRAME_NS for i in range(1, 4))

MID_1 = Decimal("65432.10")
MID_2 = Decimal("65435.20")

#: The series under test: two agreed bars and one refusal. The refusal is a
#: row with a reason, never a missing row (`one_venue` -- a median over one
#: venue is that venue's mid wearing a better name).
ROWS: tuple[consensus.Consensus, ...] = (
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="spot",
        bar_close_ns=BAR_1,
        consensus_mid=MID_1,
        venue_count=2,
        refusal_reason="",
    ),
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="spot",
        bar_close_ns=BAR_2,
        consensus_mid=MID_2,
        venue_count=3,
        refusal_reason="",
    ),
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="spot",
        bar_close_ns=BAR_3,
        consensus_mid=None,
        venue_count=1,
        refusal_reason="one_venue",
    ),
)


def client(catalog: Catalog) -> TestClient:
    """The app over a repository holding `ROWS` for one market."""
    repo = LakehouseRepository(catalog=catalog)
    # The consensus table is keyed by (asset, market_type), not by venue, so
    # the route resolves which consensus a chart's venue/symbol asks for
    # through the market it is -- the registry decides, as the library does.
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="spot")
    consensus.table_for(catalog).append([consensus.to_row(row) for row in ROWS])
    return TestClient(create_app(repository=repo))


def get(c: TestClient, **params):
    return c.get(
        "/api/v1/consensus",
        params={"venue": "binance", "symbol": "BTCUSDT", "timeframe_ns": TIMEFRAME_NS, **params},
    )


@pytest.mark.trace("REQ-WP-091")
def test_consensus_returns_per_bar_mids_with_venue_counts(catalog: Catalog) -> None:
    """FR-002 / SC-003: one row per bar, its mid as a string decimal and how
    many venues stood behind it."""
    response = get(client(catalog), window="24h")

    assert response.status_code == 200
    bars = response.json()["consensus"]
    assert [int(b["bar_close_ns"]) for b in bars] == [BAR_1, BAR_2, BAR_3]
    assert [b["venue_count"] for b in bars] == [2, 3, 1]

    for b in bars:
        assert {"bar_close_ns", "consensus_mid", "venue_count", "refusal_reason"} <= set(b)

    # A price is money: a string decimal the reader parses, never a float that
    # has already lost the cents on the way out of the response model. The two
    # agreed bars carry their medians and no refusal; the third is left to
    # `test_consensus_refusal_carries_reason`.
    #
    # Corrected 2026-10-07: the loop is over the two agreed bars, as the
    # comment above already said. It zipped all three against two medians with
    # `strict=True`, which raises `ValueError` on the length mismatch before a
    # single assertion runs -- so the test failed for a reason no
    # implementation could answer, while lines 94-95 pin all three bars as
    # present.
    for b, expected in zip(bars[:2], (MID_1, MID_2), strict=True):
        assert isinstance(b["consensus_mid"], str)
        assert Decimal(b["consensus_mid"]) == expected
        assert not b["refusal_reason"]


@pytest.mark.trace("REQ-WP-091")
def test_consensus_window_validation(catalog: Catalog) -> None:
    """FR-002: only 4h, 24h and 7d are windows; anything else is a 422 from
    the request validator, not a shorter or longer answer."""
    c = client(catalog)

    assert get(c, window="1h").status_code == 422
    assert get(c, window="25h").status_code == 422


@pytest.mark.trace("REQ-WP-091")
def test_consensus_point_in_time(catalog: Catalog) -> None:
    """Principle I: asked at bar 2's close, the answer holds no bar that had
    not closed by then -- bar 3's row exists in storage and must stay out."""
    response = get(client(catalog), window="24h", at_ns=BAR_2)

    assert response.status_code == 200
    closes = [int(b["bar_close_ns"]) for b in response.json()["consensus"]]
    assert all(c <= BAR_2 for c in closes)
    assert closes == [BAR_1, BAR_2]


@pytest.mark.trace("REQ-WP-091")
def test_consensus_refusal_carries_reason(catalog: Catalog) -> None:
    """A bar with fewer than two venues answers with its reason and no price,
    rather than a one-venue "consensus" or an absent row."""
    response = get(client(catalog), window="24h")

    assert response.status_code == 200
    bars = {int(b["bar_close_ns"]): b for b in response.json()["consensus"]}
    refused = bars[BAR_3]

    assert refused["venue_count"] <= 1
    assert refused["consensus_mid"] is None
    assert isinstance(refused["refusal_reason"], str) and refused["refusal_reason"]


@pytest.mark.trace("REQ-WP-091")
def test_consensus_unknown_market_404(catalog: Catalog) -> None:
    """A series nothing was stored for is a 404 naming what is missing, as the
    volume profile answers with "no price bins" -- never an empty 200 a chart
    would draw as a flat line at nothing."""
    response = get(client(catalog), venue="kraken", symbol="DOGEUSDT")

    assert response.status_code == 404
    # Not the router's "Not Found": the endpoint itself refused, and the
    # volume-profile route is the convention (`api/volume_profile.py`).
    assert response.json()["detail"] != "Not Found"
