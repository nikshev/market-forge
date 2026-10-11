"""The two pools the DEX panes read, pinned from REQ-WP-058's measurement (REQ-WP-099)."""

from __future__ import annotations

import pytest

from channelflow.chain.hyperevm import FACTORIES, PoolFamily, family_for
from channelflow.dex import hyperevm_pools as pools

pytestmark = pytest.mark.trace("REQ-WP-099")


def test_the_registry_names_a_uniswap_v3_pool_and_an_algebra_pool() -> None:
    assert {pool.family for pool in pools.POOLS} == {
        PoolFamily.UNISWAP_V3,
        PoolFamily.ALGEBRA_INTEGRAL,
    }


def test_every_pool_comes_from_a_factory_the_decoders_know() -> None:
    for pool in pools.POOLS:
        assert pool.factory in FACTORIES
        assert family_for(pool.factory) == pool.family


def test_the_two_pools_are_the_same_pair_in_the_same_order() -> None:
    assert len({(pool.token0, pool.token1) for pool in pools.POOLS}) == 1


def test_an_algebra_pool_carries_no_pool_level_fee_and_a_v3_pool_does() -> None:
    for pool in pools.POOLS:
        assert (pool.fee_pips is None) == pool.dynamic_fee


def test_the_liquidity_pool_is_one_of_the_registered_pools() -> None:
    assert pools.LIQUIDITY_POOL in {pool.address for pool in pools.POOLS}


def test_addresses_are_lowercase_so_a_log_can_be_matched_by_equality() -> None:
    for pool in pools.POOLS:
        assert pool.address == pool.address.lower()


def test_token_decimals_are_known_for_both_tokens() -> None:
    pool = pools.POOLS[0]
    assert pools.DECIMALS[pool.token0] == 18
    assert pools.DECIMALS[pool.token1] == 6


def test_the_series_the_pools_are_shown_on_is_one_the_deployment_ingests() -> None:
    from channelflow.context import sources

    ingested = {(venue, symbol) for venue, symbol, _ in sources.SERIES}

    assert set(pools.SERIES) <= ingested
    assert len(pools.SERIES) == 2, "HYPE is on two venues; both carry the panes"
