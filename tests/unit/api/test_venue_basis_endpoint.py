"""US2: `GET /api/v1/features/timeseries?feature=venue_basis_bps` (REQ-WP-091).

The route exists and already serves a feature series -- but it does not know
`venue_basis_bps` yet. It takes no `feature` parameter at all (so a request
naming one is silently ignored), and the rows it reads are the stored feature
snapshots, not the consensus rows and top-of-book quotes this feature is built
from. These tests pin what the endpoint must answer once T012-T014 wire it:
the first fails until they do. The one asserting a 422 for a request with no
`feature` was corrected on 2026-10-07 -- it had read
`contracts/api-contract.md`'s `feature: required` into a parameter the
endpoint has never had; see `test_venue_basis_requires_feature_param`.

What is seeded is what the pipeline would have written: a consensus row per bar
(`channelflow.tables.consensus` -- the median the cross-venue pass stores at the
bar close) and the viewed venue's own quote at that same close
(`channelflow.tables.quotes`). The basis is then PRD §17.3's formula over those
two numbers, which neither the route nor this file gets to choose:

    venue_basis_bps = 10000 * (mid_i / consensus_mid - 1)

**Two point shapes are accepted, deliberately.** The contract in
`specs/140-cross-venue-consensus/contracts/api-contract.md` writes
`{bar_close_ns, venue_basis_bps}`; the series this endpoint serves today writes
`{at_ns, values}`. Either carries the same fact -- the bar and its number -- and
which one T014 picks is a shape decision this suite should not be the reason to
make. What is not negotiable is the *number*, and that is asserted against
values computed here from the seeded decimals, never read back out of the
response twice.

The value must arrive as a JSON number rather than a string decimal: a price is
money and travels as a string everywhere else in this API, but PRD §19 registers
a *feature* as float64, and `venue_basis_bps` is a feature.
"""

from __future__ import annotations

from decimal import Decimal

import httpx
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

#: What the consensus pass stored for each bar -- two venues and three, both
#: agreed, so neither bar is a refusal and the formula has a denominator.
CONSENSUS_1 = Decimal("65432.10")
CONSENSUS_2 = Decimal("65435.20")

#: The viewed venue's (binance) mid at those same closes: one above its
#: consensus, one below, so a sign error cannot hide behind both being positive.
MID_1 = Decimal("65440.00")
MID_2 = Decimal("65427.00")

#: §17.3 by hand: 10000 * (65440.00 / 65432.10 - 1) = 1.2073584677856892...
BASIS_1 = 1.2073584677856892
#: 10000 * (65427.00 / 65435.20 - 1) = -1.2531481526762354...
BASIS_2 = -1.2531481526762354

CONSENSUS_ROWS: tuple[consensus.Consensus, ...] = (
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="spot",
        bar_close_ns=BAR_1,
        consensus_mid=CONSENSUS_1,
        venue_count=2,
        refusal_reason="",
    ),
    consensus.Consensus(
        asset="BTCUSDT",
        market_type="spot",
        bar_close_ns=BAR_2,
        consensus_mid=CONSENSUS_2,
        venue_count=3,
        refusal_reason="",
    ),
)


def quote(mid: Decimal, ts_ns: int) -> quotes.Quote:
    """One viewed-venue quote at a bar close: `ts_ns` is the close itself.

    A quote *at* the close is available at it (`<= at_ns`, the spec's edge case),
    and `ingest_ns` trails `ts_ns` rather than replacing it -- receive time says
    how old the observation was when it arrived and never decides availability
    (Principle II).
    """
    return quotes.Quote(
        venue="binance",
        symbol="BTCUSDT",
        bid=mid - Decimal("0.05"),
        ask=mid + Decimal("0.05"),
        mid=mid,
        ts_ns=ts_ns,
        ingest_ns=ts_ns + 1,
    )


QUOTES: tuple[quotes.Quote, ...] = (quote(MID_1, BAR_1), quote(MID_2, BAR_2))


def client(catalog: Catalog, *, cvd_at_ns: int | None = None) -> TestClient:
    """The app over a repository holding the consensus rows and the quotes.

    `cvd_at_ns` additionally writes one ordinary feature snapshot, so a test
    can ask for a feature this requirement never touched and be told whether it
    still comes back.
    """
    repo = LakehouseRepository(catalog=catalog)
    # The consensus table is keyed by (asset, market_type), not by venue, so
    # the route resolves which consensus a chart's venue/symbol asks for
    # through the market it is -- the registry decides, as the library does.
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="spot")
    if cvd_at_ns is not None:
        repo.add_feature_snapshot(
            venue="binance",
            symbol="BTCUSDT",
            timeframe_ns=TIMEFRAME_NS,
            at_ns=cvd_at_ns,
            values={"cvd_base": 42.0},
        )
    consensus.table_for(catalog).append([consensus.to_row(row) for row in CONSENSUS_ROWS])
    quotes.table_for(catalog).append([quotes.to_row(row) for row in QUOTES])
    return TestClient(create_app(repository=repo))


def get(
    c: TestClient,
    *,
    start_ns: int,
    end_ns: int,
    feature: str | None = None,
) -> httpx.Response:
    """One call to the endpoint, optionally carrying an extra `feature` param.

    `routes.get_feature_series` takes exactly five query parameters --
    `venue`, `symbol`, `timeframe_ns`, `start_ns`, `end_ns` -- so `feature` is
    never a parameter of this endpoint and defaults to not being sent at all.
    Passing one sends a query parameter FastAPI has nothing to bind it to,
    which is how the test below asks for it and is ignored.
    """
    params: dict[str, str | int] = {
        "venue": "binance",
        "symbol": "BTCUSDT",
        "timeframe_ns": TIMEFRAME_NS,
        "start_ns": start_ns,
        "end_ns": end_ns,
    }
    if feature is not None:
        params["feature"] = feature
    return c.get("/api/v1/features/timeseries", params=params)


def raw_time(point: dict[str, object]) -> object:
    """The bar's close under either name the contract and the series use."""
    for key in ("bar_close_ns", "at_ns"):
        if key in point:
            return point[key]
    raise AssertionError(f"a point carries neither bar_close_ns nor at_ns: {point!r}")


def raw_basis(point: dict[str, object], name: str) -> object:
    """One feature's value, at the top level or inside the series' `values`."""
    if name in point:
        return point[name]
    values = point.get("values")
    if isinstance(values, dict) and name in values:
        return values[name]
    raise AssertionError(f"{name} is absent from {point!r}")


@pytest.mark.trace("REQ-WP-091")
def test_venue_basis_returns_points(catalog: Catalog) -> None:
    """FR-003 / SC-003: one point per bar carrying §17.3's number.

    The window holds both bars, so both must come back, at their closes, with
    the value the seeded decimals produce -- above consensus on the first bar,
    below on the second. Called **without** `feature`: the endpoint's shape is
    `routes.get_feature_series(venue, symbol, timeframe_ns, start_ns, end_ns)`
    and naming a feature is not part of it (corrected 2026-10-07 -- this test
    used to send `feature=venue_basis_bps` as though the endpoint selected on
    it).
    """
    response = get(client(catalog), start_ns=BAR_1, end_ns=BAR_2)

    assert response.status_code == 200
    points = response.json()["points"]
    assert len(points) == 2
    assert [int(raw_time(p)) for p in points] == [BAR_1, BAR_2]

    for point, expected in zip(points, (BASIS_1, BASIS_2), strict=True):
        value = raw_basis(point, "venue_basis_bps")
        # A number, not the string decimal a price would travel as: §19
        # registers a feature's value as float64 and the pane plots a float.
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert float(value) == pytest.approx(expected, abs=1e-9)


@pytest.mark.trace("REQ-WP-091")
def test_venue_basis_unknown_feature_unchanged(catalog: Catalog) -> None:
    """No regression: a feature this requirement did not touch still answers.

    Naming `feature` must not become a filter that only `venue_basis_bps` can
    pass -- `cvd_base` is registered, produced and plotted, and it has to keep
    coming back exactly as it did before the new feature was wired in.
    """
    response = get(
        client(catalog, cvd_at_ns=BAR_1), feature="cvd_base", start_ns=BAR_1, end_ns=BAR_1
    )

    assert response.status_code == 200
    points = response.json()["points"]
    assert [int(raw_time(p)) for p in points] == [BAR_1]
    assert float(raw_basis(points[0], "cvd_base")) == pytest.approx(42.0, abs=1e-9)


@pytest.mark.trace("REQ-WP-091")
@pytest.mark.parametrize("feature", [None, ""], ids=["missing", "empty"])
def test_venue_basis_requires_feature_param(catalog: Catalog, feature: str | None) -> None:
    """FR-003, **corrected 2026-10-07**: naming no `feature` is answered, not refused.

    This test used to assert 422 here -- that the endpoint asks *which*
    feature it should serve, with an empty string refused rather than silently
    replaced. That contract belonged to `contracts/api-contract.md`, which
    lists `feature` as a required query parameter; **the endpoint never had
    one.** `routes.get_feature_series` is declared as
    `(venue, symbol, timeframe_ns, start_ns, end_ns)` and takes nothing else,
    and `apps/web/src/api.ts`'s `fetchFeatureSeries` sends exactly those five
    -- a required `feature` would have broken every caller of an endpoint
    that has always answered with the whole point.

    So a `feature` here (an empty one for this test, a named one for
    `test_venue_basis_unknown_feature_unchanged`) is a query parameter FastAPI
    has nothing to bind it to: ignored, and the basis comes back all the same
    -- 200 with `venue_basis_bps` at both bar closes. The endpoint's shape is
    the fact; the request validator's 422 would be a fiction about it.
    """
    response = get(client(catalog), feature=feature, start_ns=BAR_1, end_ns=BAR_2)

    assert response.status_code == 200
    points = response.json()["points"]
    assert [int(raw_time(p)) for p in points] == [BAR_1, BAR_2]
    for point, expected in zip(points, (BASIS_1, BASIS_2), strict=True):
        assert float(raw_basis(point, "venue_basis_bps")) == pytest.approx(expected, abs=1e-9)


@pytest.mark.trace("REQ-WP-091")
def test_venue_basis_empty_window(catalog: Catalog) -> None:
    """A window with no consensus rows is a state: 200 with no points.

    Not a 500, and not a 404 either: `/features/timeseries` has always said
    "nothing here" with an empty `points` list, and the chart reads exactly
    that as its `empty` series -- the state [[REQ-WP-084]] distinguishes from a
    failure, where a 404 would leave the pane calling a load error "no data"
    (FR-006). The same convention the bars endpoint answers an unknown symbol
    with ([[REQ-API-001]] FR-009: "nothing known is a fact, not an error").
    The consensus table holds rows for BAR_1 and BAR_2; this window starts a
    bar later and reaches neither.
    """
    response = get(client(catalog), start_ns=BAR_2 + TIMEFRAME_NS, end_ns=BAR_2 + 5 * TIMEFRAME_NS)

    assert response.status_code == 200
    assert response.json()["points"] == []
