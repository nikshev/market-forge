"""AS-SEEN-THEN against CURRENT REFIT (REQ-API-001, REQ-WP-009).

PRD section 27.5 calls this critical and says it "directly exposes repaint-like
differences and protects research integrity". This is the file that proves the
exposure is real.

The fixture makes the two modes *disagree* deliberately. A fixture where they
agreed would pass under an implementation that ignored the parameter
altogether -- which is exactly the failure ADR-020 is about, and it would leave
every deep link ever sent quietly opening a refit.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from channelflow.api import AS_SEEN_THEN, CURRENT_REFIT, InMemoryRepository, create_app

from .conftest import BASE_NS, MINUTE_NS, bar, snapshot

AT_NS = BASE_NS + 60 * MINUTE_NS


@pytest.fixture
def diverging() -> InMemoryRepository:
    """A stored snapshot, then history that would refit to something else.

    The stored channel is centred at 112,000 with a downward slope. The bars
    that follow rise steeply, so a refit over current history centres far
    higher -- the shape of every repainting story: the model, refitted today,
    looks like it saw what was coming.
    """
    repo = InMemoryRepository()
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="spot")
    for i in range(120):
        repo.add_bar(bar(i, 112000.0 + i * 40.0))
    repo.add_channel_snapshot(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        snapshot=snapshot(as_of_ns=AT_NS, center=112000.0, slope=-0.01),
    )
    return repo


@pytest.fixture
def diverging_client(diverging: InMemoryRepository) -> TestClient:
    return TestClient(create_app(repository=diverging))


def _channel(client: TestClient, **params: object) -> dict:
    response = client.get(
        "/api/v1/channels",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": AT_NS,
            **params,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.trace("REQ-API-001")
@pytest.mark.trace("REQ-WP-009")
def test_the_parameter_defaults_to_as_seen_then(diverging_client: TestClient) -> None:
    """SC-001, FR-001, PRD section 28.3.

    The single most consequential default in the system. Every alert already
    sent carries a deep link built on it.
    """
    default = _channel(diverging_client)

    assert default["mode"] == AS_SEEN_THEN
    assert default["center_now"] == 112000.0


@pytest.mark.trace("REQ-API-001")
def test_as_seen_then_returns_the_stored_snapshot_unchanged(
    diverging_client: TestClient, diverging: InMemoryRepository
) -> None:
    """SC-002, FR-002. Compared field by field against what was stored, which
    is only possible because REQ-WP-006's snapshots are frozen."""
    stored = diverging.channel_snapshot_at(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, at_ns=AT_NS
    )
    assert stored is not None

    served = _channel(diverging_client, as_seen_then=True)

    assert served["center_now"] == stored.center_now
    assert served["upper_now"] == stored.upper_now
    assert served["lower_now"] == stored.lower_now
    assert served["slope_normalized"] == stored.slope_normalized
    assert served["as_of_ns"] == str(stored.as_of_ns)
    assert served["quality_score"] == stored.quality.score


@pytest.mark.trace("REQ-API-001")
@pytest.mark.trace("REQ-WP-009")
def test_the_two_modes_disagree_and_that_is_the_point(
    diverging_client: TestClient,
) -> None:
    """SC-002, FR-003, PRD section 27.5.

    If these ever return the same numbers the test has stopped testing
    anything: an implementation ignoring `as_seen_then` entirely would pass.
    """
    stored = _channel(diverging_client, as_seen_then=True)
    refit = _channel(diverging_client, as_seen_then=False)

    assert stored["mode"] == AS_SEEN_THEN
    assert refit["mode"] == CURRENT_REFIT
    assert refit["center_now"] != stored["center_now"]
    assert refit["slope_normalized"] > stored["slope_normalized"], (
        "the refit sees the rise that followed; the snapshot never did"
    )


@pytest.mark.trace("REQ-API-001")
def test_the_refit_cannot_see_past_the_requested_instant(
    diverging_client: TestClient,
) -> None:
    """SC-010, FR-017, Principle I.

    Later data is planted by the fixture -- 120 bars, of which only the first
    61 are at or before `at_ns`. A refit that used all of them would be a
    better-looking channel derived from the future.
    """
    refit = _channel(diverging_client, as_seen_then=False)

    assert int(refit["source_max_event_time_ns"]) <= AT_NS


@pytest.mark.trace("REQ-API-001")
def test_a_refit_without_enough_history_is_refused() -> None:
    """FR-003, and the spec's third edge case.

    Approximating over fewer bars would put a different model beside a real one
    under the same name -- REQ-WP-006's own reasoning, at the API boundary.
    """
    repo = InMemoryRepository()
    for i in range(5):
        repo.add_bar(bar(i, 112000.0))
    client = TestClient(create_app(repository=repo))

    response = client.get(
        "/api/v1/channels",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": BASE_NS + 5 * MINUTE_NS,
            "as_seen_then": False,
        },
    )

    assert response.status_code == 404
    assert "refit" in response.json()["detail"]


@pytest.mark.trace("REQ-API-001")
def test_as_seen_then_is_never_reconstructed_after_the_fact() -> None:
    """FR-002.

    With no stored snapshot, AS-SEEN-THEN refuses rather than quietly refitting
    one. Silently substituting a refit here is the whole failure: it would
    answer with a channel labelled as the one that was seen at the time, when
    nobody ever saw it.
    """
    repo = InMemoryRepository()
    for i in range(120):
        repo.add_bar(bar(i, 112000.0 + i * 40.0))
    client = TestClient(create_app(repository=repo))

    response = client.get(
        "/api/v1/channels",
        params={
            "venue": "binance",
            "symbol": "BTCUSDT",
            "timeframe_ns": MINUTE_NS,
            "at_ns": AT_NS,
        },
    )

    assert response.status_code == 404
    assert "AS-SEEN-THEN" in response.json()["detail"]


@pytest.mark.trace("REQ-API-001")
def test_a_snapshot_taken_after_the_instant_is_not_returned(
    diverging: InMemoryRepository,
) -> None:
    """FR-017 at the repository. A later snapshot is hindsight wearing the
    label of the moment asked about."""
    diverging.add_channel_snapshot(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        snapshot=snapshot(as_of_ns=AT_NS + 30 * MINUTE_NS, center=999999.0),
    )
    client = TestClient(create_app(repository=diverging))

    served = _channel(client)

    assert served["center_now"] == 112000.0, "the later snapshot must not be chosen"
