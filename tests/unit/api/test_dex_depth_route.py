"""The depth curve reaches the API with its refusals intact (REQ-WP-054).

PRD §27.2's "DEX liquidity bands", from the canonical table to the response. The
tests below check each boundary rather than only the end, because [[ADR-036]]'s
`reachable` has three chances to be dropped on the way and each one turns "this
pool is too thin to move 100 bps" into "100 bps costs this much here".
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from channelflow.api.app import create_app
from channelflow.api.repositories import InMemoryRepository
from channelflow.tables.dex_depth import DepthBand

POOL = "0xpool"
STATE_TIME = 1_700_000_000_000_000_000


def _band(**overrides: object) -> DepthBand:
    fields: dict[str, object] = {
        "state_time_ns": STATE_TIME,
        "chain_id": 1,
        "pool": POOL,
        "side": "up",
        "target_bps": Decimal("10"),
        "reachable": True,
        "reached_bps": Decimal("10"),
        "amount0": Decimal("1.25"),
        "amount1": Decimal("3750.5"),
        "reference_price": Decimal("3000.16666666666666666666"),
        "ticks_crossed": 4,
        "reason": "",
    }
    return DepthBand(**{**fields, **overrides})  # type: ignore[arg-type]


@pytest.fixture
def client() -> TestClient:
    repository = InMemoryRepository()
    repository.add_depth_band(_band())
    repository.add_depth_band(
        _band(
            target_bps=Decimal("100"),
            reachable=False,
            reached_bps=Decimal("17.5"),
            reason="exhausted the known liquidity",
        )
    )
    app = create_app(repository=repository)
    return TestClient(app)


@pytest.mark.trace("REQ-WP-054")
def test_the_endpoint_serves_a_pool_s_bands(client: TestClient) -> None:
    response = client.get(
        "/api/v1/dex/depth", params={"chain_id": 1, "pool": POOL, "at_ns": STATE_TIME}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pool"] == POOL
    assert len(body["bands"]) == 2


@pytest.mark.trace("REQ-WP-054")
def test_an_unreached_band_crosses_the_wire_marked(client: TestClient) -> None:
    """The boundary most likely to drop it. A band and a notional with no flag
    is a cheaper-looking market than exists, in the same ink as a real one."""
    body = client.get(
        "/api/v1/dex/depth", params={"chain_id": 1, "pool": POOL, "at_ns": STATE_TIME}
    ).json()
    by_band = {band["target_bps"]: band for band in body["bands"]}
    assert by_band["10"]["reachable"] is True
    assert by_band["100"]["reachable"] is False
    # And it says how far the book actually went, which the target alone cannot.
    assert by_band["100"]["reached_bps"] == "17.5"
    assert by_band["100"]["reason"]


@pytest.mark.trace("REQ-WP-054")
def test_money_crosses_the_wire_as_exact_strings(client: TestClient) -> None:
    """As bars' prices do, and for the same reason: JSON's number is a float64."""
    body = client.get(
        "/api/v1/dex/depth", params={"chain_id": 1, "pool": POOL, "at_ns": STATE_TIME}
    ).json()
    band = body["bands"][0]
    exact = "3000.16666666666666666666"
    assert band["reference_price"] == exact
    # A value float64 cannot hold, so a connector that went through a float on
    # the way out would be visibly short of it rather than accidentally right.
    assert str(float(Decimal(exact))) != exact
    assert isinstance(band["amount0"], str)
    assert isinstance(band["amount1"], str)


@pytest.mark.trace("REQ-WP-054")
def test_times_cross_the_wire_as_strings_too(client: TestClient) -> None:
    """A nanosecond epoch timestamp is about 1.7e18; JavaScript's safe integer
    maximum is 9.0e15. Sent as a JSON number it quantises to the nearest 256
    nanoseconds, and the browser cannot represent the value it was sent."""
    body = client.get(
        "/api/v1/dex/depth", params={"chain_id": 1, "pool": POOL, "at_ns": STATE_TIME}
    ).json()
    assert body["state_time_ns"] == str(STATE_TIME)
    assert body["requested_at_ns"] == str(STATE_TIME)
    assert int(body["state_time_ns"]) == STATE_TIME


@pytest.mark.trace("REQ-WP-054")
def test_the_instant_is_required_and_not_defaulted(client: TestClient) -> None:
    """Defaulting it to now would make a historical chart quietly show the
    present -- the look-ahead Principle I forbids, arriving through the one door
    nobody guards."""
    response = client.get("/api/v1/dex/depth", params={"chain_id": 1, "pool": POOL})
    assert response.status_code == 422


@pytest.mark.trace("REQ-WP-054")
def test_a_curve_computed_later_is_not_returned(client: TestClient) -> None:
    """Principle I at the boundary the overlay reads through."""
    body = client.get(
        "/api/v1/dex/depth",
        params={"chain_id": 1, "pool": POOL, "at_ns": STATE_TIME - 1},
    ).json()
    assert body["bands"] == []
    assert body["state_time_ns"] is None


@pytest.mark.trace("REQ-WP-054")
def test_a_pool_with_no_curve_says_so_rather_than_erroring(client: TestClient) -> None:
    """An absent curve is a fact about the pool, not a failure of the request --
    and the client draws the two differently."""
    body = client.get(
        "/api/v1/dex/depth",
        params={"chain_id": 1, "pool": "0xnothing", "at_ns": STATE_TIME},
    ).json()
    assert body["bands"] == []
    assert body["state_time_ns"] is None
    assert body["requested_at_ns"] == str(STATE_TIME)


@pytest.mark.trace("REQ-WP-054")
def test_the_newest_curve_at_or_before_the_instant_wins() -> None:
    """One curve, not every curve. Handing the caller the history is where a
    caller picks the newest and reintroduces the look-ahead."""
    repository = InMemoryRepository()
    repository.add_depth_band(_band(state_time_ns=STATE_TIME, target_bps=Decimal("10")))
    repository.add_depth_band(_band(state_time_ns=STATE_TIME + 1_000, target_bps=Decimal("25")))
    client = TestClient(create_app(repository=repository))

    at_first = client.get(
        "/api/v1/dex/depth", params={"chain_id": 1, "pool": POOL, "at_ns": STATE_TIME}
    ).json()
    assert [band["target_bps"] for band in at_first["bands"]] == ["10"]

    at_second = client.get(
        "/api/v1/dex/depth",
        params={"chain_id": 1, "pool": POOL, "at_ns": STATE_TIME + 5_000},
    ).json()
    assert [band["target_bps"] for band in at_second["bands"]] == ["25"]
    assert at_second["state_time_ns"] == str(STATE_TIME + 1_000)
