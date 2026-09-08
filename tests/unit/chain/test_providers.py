"""PRD section 18.17's provider strategy (REQ-WP-014).

"RPC is infrastructure, not a source of unquestioned truth."
"""

from __future__ import annotations

import pytest

from channelflow.chain import NoHealthyProvider, ProviderPool, compare_providers

from .conftest import at


@pytest.mark.trace("REQ-WP-014")
def test_health_reports_latency_errors_and_gaps() -> None:
    """FR-012, SC-008.

    Three counts rather than one score, because the failure modes need
    different responses: latency means route elsewhere, errors mean cool down,
    gaps mean the data is incomplete and a backfill is owed.
    """
    pool = ProviderPool()

    pool.observe("rpc-a", latency_ms=50.0, at_ns=at(1))
    pool.observe("rpc-a", latency_ms=150.0, at_ns=at(2), error=True)
    health = pool.observe("rpc-a", latency_ms=100.0, at_ns=at(3), gap=True)

    assert health.mean_latency_ms == pytest.approx(100.0)
    assert health.error_rate == pytest.approx(1 / 3)
    assert health.gap_rate == pytest.approx(1 / 3)


@pytest.mark.trace("REQ-WP-014")
def test_an_error_storm_puts_a_provider_in_cooldown() -> None:
    """FR-013, SC-008, PRD section 18.17's "provider cooldown on
    rate-limit/error storms"."""
    pool = ProviderPool(max_error_rate=0.2, cooldown_ns=60 * 1_000_000_000)

    pool.observe("rpc-a", latency_ms=10.0, at_ns=at(1))
    pool.observe("rpc-a", latency_ms=10.0, at_ns=at(2), error=True)
    pool.observe("rpc-b", latency_ms=80.0, at_ns=at(2))

    chosen = pool.choose(at(3))

    assert chosen.name == "rpc-b", "rpc-a is cooling down despite being faster"


@pytest.mark.trace("REQ-WP-014")
def test_the_fastest_healthy_provider_is_chosen() -> None:
    """FR-013. Routing must prefer something, or the health scores are
    decoration."""
    pool = ProviderPool()
    pool.observe("rpc-a", latency_ms=200.0, at_ns=at(1))
    pool.observe("rpc-b", latency_ms=20.0, at_ns=at(1))

    assert pool.choose(at(2)).name == "rpc-b"


@pytest.mark.trace("REQ-WP-014")
def test_a_cooldown_expires() -> None:
    """FR-013. A provider is cooled down, not banned.

    This test found a real defect: the rates were computed over the provider's
    lifetime, so one error left it permanently above any threshold and the
    cooldown could never help. They are windowed now -- a lifetime rate on a
    long-running process means one bad hour poisons a week.
    """
    pool = ProviderPool(max_error_rate=0.2, cooldown_ns=10 * 1_000_000_000)
    pool.observe("rpc-a", latency_ms=10.0, at_ns=at(1), error=True)

    with pytest.raises(NoHealthyProvider):
        pool.choose(at(5))

    for second in range(20, 30):
        pool.observe("rpc-a", latency_ms=10.0, at_ns=at(second))

    assert pool.choose(at(40)).name == "rpc-a"


@pytest.mark.trace("REQ-WP-014")
def test_no_healthy_provider_refuses() -> None:
    """SC-008, FR-015, the spec's fifth edge case.

    Data from a provider known to be failing looks exactly like data from a
    working one, and the consumer has no way to tell.
    """
    pool = ProviderPool(max_error_rate=0.0)
    pool.observe("rpc-a", latency_ms=10.0, at_ns=at(1), error=True)

    with pytest.raises(NoHealthyProvider, match="indistinguishable"):
        pool.choose(at(2))


@pytest.mark.trace("REQ-WP-014")
def test_an_empty_pool_refuses() -> None:
    """FR-015. Nothing observed is not a healthy provider."""
    with pytest.raises(NoHealthyProvider):
        ProviderPool().choose(at(1))


@pytest.mark.trace("REQ-WP-014")
def test_a_cross_provider_disagreement_is_reported_not_resolved() -> None:
    """SC-009, FR-014, PRD section 18.17's "sampled cross-provider consistency
    checks".

    Two providers disagreeing about a block hash is a fact about the
    infrastructure. Picking one and moving on would hide the only signal that
    something is wrong.
    """
    disagreement = compare_providers(100, {"rpc-a": "0xaaa", "rpc-b": "0xbbb", "rpc-c": "0xaaa"})

    assert disagreement is not None
    assert disagreement.distinct == 2
    assert disagreement.answers == {"rpc-a": "0xaaa", "rpc-b": "0xbbb", "rpc-c": "0xaaa"}


@pytest.mark.trace("REQ-WP-014")
def test_agreement_reports_nothing() -> None:
    """FR-014. A check that always reported would be noise, and noise gets
    muted."""
    assert compare_providers(100, {"rpc-a": "0xaaa", "rpc-b": "0xaaa"}) is None


@pytest.mark.trace("REQ-WP-014")
def test_the_rates_are_windowed_not_lifetime() -> None:
    """FR-012, and the defect the cooldown test uncovered.

    Twenty clean calls after one error: the lifetime rate is 1/21 and the
    windowed rate over the last five is zero. On a process that runs for weeks
    the difference is the whole question -- a provider that had a bad minute
    last Tuesday is not unhealthy today.
    """
    pool = ProviderPool()
    health = pool.observe("rpc-a", latency_ms=10.0, at_ns=at(1), error=True)
    health.window = 5
    for second in range(2, 22):
        pool.observe("rpc-a", latency_ms=10.0, at_ns=at(second))

    assert health.errors == 1, "the lifetime count is kept, for an operator"
    assert health.error_rate == 0.0, "but the rate is over the recent window"
