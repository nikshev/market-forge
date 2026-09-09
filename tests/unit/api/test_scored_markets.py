"""A ranked market list and a signal's contribution factors (REQ-US-001, REQ-US-004)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from channelflow.alerting import signal_id_for
from channelflow.api import InMemoryRepository, create_app
from channelflow.scoring import Group, GroupContribution, score_signal

from .conftest import candidate

FULL = (
    GroupContribution(group=Group.CHANNEL_STRUCTURE, value=26.0, factors=("slope_stability",)),
    GroupContribution(group=Group.REJECTION_QUALITY, value=17.0, factors=("wick_rejection",)),
    GroupContribution(group=Group.ORDER_FLOW, value=16.0, factors=("ofi_agrees",)),
    GroupContribution(group=Group.VOLUME, value=1.0, factors=("poc_far",)),
    GroupContribution(group=Group.DERIVATIVES, value=8.0, factors=("funding_z",)),
)


@pytest.fixture
def scored(repository: InMemoryRepository) -> InMemoryRepository:
    """Three markets: a strong illiquid one, a weaker liquid one, and one unscored."""
    repository.add_setup_score(
        venue="binance",
        symbol="ETHUSDT",
        score=score_signal(FULL, data_quality=1.0),
        feature_snapshot={"ofi_1m": 0.62},
        model_version="deterministic-v1",
        liquidity_factor=0.1,
    )
    repository.add_setup_score(
        venue="binance",
        symbol="BTCUSDT",
        score=score_signal(FULL, data_quality=0.9),
        feature_snapshot={"ofi_1m": 0.41},
        model_version="deterministic-v1",
        liquidity_factor=1.0,
    )
    # A second unscored market, added after the first in the repository but
    # before it by name, so the tail's ordering is observable rather than
    # whatever order the rows happened to be stored in.
    repository.add_market(venue="bybit", symbol="ADAUSDT", market_type="perp")
    return repository


@pytest.fixture
def scored_client(scored: InMemoryRepository) -> TestClient:
    return TestClient(create_app(repository=scored))


@pytest.mark.trace("REQ-US-001")
def test_the_market_list_is_ordered_by_rank_score(scored_client: TestClient) -> None:
    """SC-001, SC-002, FR-001.

    ETHUSDT has the higher setup score and a tenth of the liquidity. PRD §43
    multiplies, so the liquid market leads -- which is the factor's stated
    purpose: it "prevents noisy illiquid assets dominating".
    """
    markets = scored_client.get("/api/v1/markets").json()["markets"]

    assert [m["symbol"] for m in markets[:2]] == ["BTCUSDT", "ETHUSDT"]
    assert markets[0]["rank_score"] > markets[1]["rank_score"]
    assert markets[1]["setup_score"] > markets[0]["setup_score"]


@pytest.mark.trace("REQ-US-001")
def test_an_unscored_market_sorts_last_with_null_scores(scored_client: TestClient) -> None:
    """SC-004, FR-003.

    A market nobody has scored is not a market that scored zero. Sorting it
    among the low scores would say the setup was examined and found weak.
    """
    markets = scored_client.get("/api/v1/markets").json()["markets"]

    last = markets[-1]
    assert last["venue"] == "bybit"
    assert last["setup_score"] is None
    assert last["rank_score"] is None


@pytest.mark.trace("REQ-US-001")
def test_the_unscored_tail_is_ordered_by_name(scored_client: TestClient) -> None:
    """SC-004, FR-003.

    Two markets nobody has scored tie at "unscored". Left to the repository's
    own order the tail is a list that happens to be stable today, and reorders
    the first time rows arrive differently.
    """
    markets = scored_client.get("/api/v1/markets").json()["markets"]

    tail = [m["symbol"] for m in markets if m["setup_score"] is None]
    assert tail == ["ADAUSDT", "BTCUSDT"]


@pytest.mark.trace("REQ-US-001")
def test_the_order_is_the_same_twice(scored_client: TestClient) -> None:
    """SC-003, FR-002.

    A list that reorders itself between refreshes is one no reader can hold a
    place in.
    """
    first = scored_client.get("/api/v1/markets").json()["markets"]
    second = scored_client.get("/api/v1/markets").json()["markets"]

    assert [m["symbol"] for m in first] == [m["symbol"] for m in second]


@pytest.mark.trace("REQ-US-001")
def test_a_filtered_list_is_still_ordered(scored_client: TestClient) -> None:
    """SC-005, FR-005."""
    markets = scored_client.get("/api/v1/markets", params={"venue": "binance"}).json()["markets"]

    assert [m["symbol"] for m in markets] == ["BTCUSDT", "ETHUSDT"]


@pytest.mark.trace("REQ-US-001")
def test_a_market_carries_the_confidence_beside_its_score(scored_client: TestClient) -> None:
    """FR-004.

    The DeFi/cross-venue family is missing from every fixture score, so the
    confidence is 0.9. Without it a reader sees a number and no way to tell how
    much evidence stood behind it.
    """
    markets = scored_client.get("/api/v1/markets").json()["markets"]

    assert markets[0]["confidence"] == pytest.approx(0.9)


@pytest.mark.trace("REQ-US-004")
def test_a_scored_signals_detail_carries_its_explanation(scored_client: TestClient) -> None:
    """SC-006, FR-006, FR-007.

    PRD §22.4's five items, and REQ-US-004's five families. Every one of §22.1's
    six groups is accounted for -- as a contribution or as a stated absence.
    """
    signal_id = signal_id_for(candidate())

    detail = scored_client.get(f"/api/v1/signals/{signal_id}").json()

    explanation = detail["explanation"]
    assert explanation["model_version"] == "deterministic-v1"
    assert explanation["top_positive"]
    assert explanation["top_negative"]
    accounted = {f["group"] for f in explanation["factors"]} | set(explanation["missing"])
    assert accounted == {g.value for g in Group}


@pytest.mark.trace("REQ-US-004")
def test_a_missing_family_is_missing_and_not_a_negative_factor(
    scored_client: TestClient,
) -> None:
    """SC-007, FR-008.

    "We have no DeFi data" is not "the DeFi evidence is against this setup". The
    panel that merges them turns an outage into a reason.
    """
    signal_id = signal_id_for(candidate())

    explanation = scored_client.get(f"/api/v1/signals/{signal_id}").json()["explanation"]

    assert Group.DEFI_CROSSVENUE.value in explanation["missing"]
    assert Group.DEFI_CROSSVENUE.value not in {f["group"] for f in explanation["top_negative"]}


@pytest.mark.trace("REQ-US-004")
def test_an_unscored_signal_still_returns_its_detail(client: TestClient) -> None:
    """SC-006, FR-009.

    The base fixture stores no score. A detail that failed without one would
    make every signal from before scoring existed unreadable.
    """
    signal_id = signal_id_for(candidate())

    response = client.get(f"/api/v1/signals/{signal_id}")

    assert response.status_code == 200
    assert response.json()["explanation"] is None
    assert response.json()["decision"]["symbol"] == "BTCUSDT"


@pytest.mark.trace("REQ-US-004")
def test_the_outcome_stays_separate_from_the_explanation(scored_client: TestClient) -> None:
    """FR-011.

    PRD §27.4: the later outcome must be "visually separated so it cannot be
    confused with information available at signal time". An explanation nested
    beside the outcome in one object would make that impossible for any UI.
    """
    signal_id = signal_id_for(candidate())

    detail = scored_client.get(f"/api/v1/signals/{signal_id}").json()

    assert "outcome" in detail
    assert "outcome" not in detail["explanation"]
