"""Uniswap v4 routes by pool id and knows what its hook makes unsafe (REQ-WP-047).

The fixture is real `Initialize` logs. That event is the only place a `PoolId`'s
preimage appears -- it carries the id the singleton computed *and* every field of
the key it computed it from -- so the mapping is checked against the chain's own
hash rather than against a reading of `PoolIdLibrary`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex.uniswap_v4 import (
    ALL_HOOK_MASK,
    DYNAMIC_FEE_FLAG,
    MAX_LP_FEE,
    RETURNS_DELTA_MASK,
    HookFlag,
    NotPointInTime,
    PoolKey,
    PoolRegistry,
    ReconstructionClass,
    RoutingKey,
    UnknownPool,
    classify,
    is_valid,
    key_fee,
    pool_id,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "uniswap_v4" / "initialize.jsonl"

CHAIN_ID = 1


def _rows() -> list[dict[str, Any]]:
    assert FIXTURE.is_file(), (
        f"missing fixture {FIXTURE}; regenerate with tools.record.uniswap_v4_capture"
    )
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


ROWS = _rows()
MANAGER = next(row for row in ROWS if row["kind"] == "manager")
POOLS = [row for row in ROWS if row["kind"] == "pool"]
IDS = [f"{row['shape']}-{row['pool_id'][:10]}" for row in POOLS]


def _key(raw: dict[str, Any]) -> PoolKey:
    return PoolKey(
        currency0=raw["currency0"],
        currency1=raw["currency1"],
        fee=raw["fee"],
        tick_spacing=raw["tick_spacing"],
        hooks=raw["hooks"],
    )


# --- the id is the manager's own ----------------------------------------------


@pytest.mark.trace("REQ-WP-047")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_pool_id_is_the_one_the_manager_computed(raw: dict[str, Any]) -> None:
    assert pool_id(_key(raw)) == raw["pool_id"].lower()


@pytest.mark.trace("REQ-WP-047")
def test_the_id_is_the_encoded_key_and_not_the_packed_one() -> None:
    """Five whole words. Packing the same fields gives a value that looks exactly
    as much like a pool id and identifies nothing."""
    from eth_hash.auto import keccak

    raw = POOLS[0]
    key = _key(raw)
    packed = (
        int(key.currency0, 16).to_bytes(20, "big")
        + int(key.currency1, 16).to_bytes(20, "big")
        + key.fee.to_bytes(3, "big")
        + (key.tick_spacing & 0xFFFFFF).to_bytes(3, "big")
        + int(key.hooks, 16).to_bytes(20, "big")
    )
    assert "0x" + keccak(packed).hex() != raw["pool_id"].lower()
    assert pool_id(key) == raw["pool_id"].lower()


@pytest.mark.trace("REQ-WP-047")
def test_a_negative_tick_spacing_is_sign_extended_across_a_whole_word() -> None:
    """Truncating the sign instead leaves every positive-spacing pool's id
    correct and every negative one's wrong, which is harder to notice than all
    of them being wrong."""
    base = _key(POOLS[0])
    negative = PoolKey(
        currency0=base.currency0,
        currency1=base.currency1,
        fee=base.fee,
        tick_spacing=-60,
        hooks=base.hooks,
    )
    from eth_hash.auto import keccak

    def encoded(spacing_word: bytes) -> str:
        return (
            "0x"
            + keccak(
                int(base.currency0, 16).to_bytes(32, "big")
                + int(base.currency1, 16).to_bytes(32, "big")
                + base.fee.to_bytes(32, "big")
                + spacing_word
                + int(base.hooks, 16).to_bytes(32, "big")
            ).hex()
        )

    truncated = encoded((-60 & 0xFFFFFF).to_bytes(32, "big"))
    extended = encoded((-60 & ((1 << 256) - 1)).to_bytes(32, "big"))
    assert truncated != extended
    assert pool_id(negative) == extended


@pytest.mark.trace("REQ-WP-047")
def test_an_unsorted_currency_pair_is_a_different_pool() -> None:
    """The manager sorts them, so a swapped pair hashes to a pool that does not
    exist rather than to the same one."""
    raw = POOLS[0]
    key = _key(raw)
    swapped = PoolKey(
        currency0=key.currency1,
        currency1=key.currency0,
        fee=key.fee,
        tick_spacing=key.tick_spacing,
        hooks=key.hooks,
    )
    assert pool_id(swapped) != pool_id(key)


@pytest.mark.trace("REQ-WP-047")
def test_a_key_that_does_not_fit_its_solidity_types_is_refused() -> None:
    common = {"currency0": "0x01", "currency1": "0x02", "hooks": "0x00"}
    with pytest.raises(ValueError, match="uint24"):
        PoolKey(**common, fee=1 << 24, tick_spacing=60)
    with pytest.raises(ValueError, match="int24"):
        PoolKey(**common, fee=3000, tick_spacing=1 << 23)


# --- one address, every pool ---------------------------------------------------


@pytest.mark.trace("REQ-WP-047")
def test_every_pool_on_the_chain_emits_through_one_address() -> None:
    """§18.8.2's claim, measured rather than quoted: filtering by the emitting
    address would file thousands of pools under one key, and the tick map that
    came out would be internally consistent and describe nothing."""
    assert MANAGER["distinct_emitters"] == 1
    assert MANAGER["pools_initialised"] > 1000, (
        "too few pools in the window for the point to be made"
    )


@pytest.mark.trace("REQ-WP-047")
def test_events_route_on_the_pool_id_and_not_the_address() -> None:
    registry = PoolRegistry()
    routes = [
        registry.initialised(chain_id=CHAIN_ID, pool_manager=MANAGER["manager"], key=_key(raw))
        for raw in POOLS
    ]
    # Every pool distinct, though every one shares the manager address.
    assert len({route.pool_id for route in routes}) == len(POOLS)
    assert len({route.pool_manager for route in routes}) == 1
    assert len(registry) == len(POOLS)
    for raw, route in zip(POOLS, routes, strict=True):
        # The registry derives the id rather than being handed one, so this ties
        # its derivation to the chain's: if it were wrong, every lookup below
        # would miss loudly instead of a fraction landing on the wrong pool.
        assert route.pool_id == raw["pool_id"].lower()
        found, resolved = registry.route(
            chain_id=CHAIN_ID, pool_manager=MANAGER["manager"], pool_id=raw["pool_id"]
        )
        assert found == route
        assert resolved == _key(raw)


@pytest.mark.trace("REQ-WP-047")
def test_an_event_for_a_pool_never_initialised_is_refused() -> None:
    """A `PoolId` is a hash, so there is nothing in it to fall back on. An event
    for an unknown pool is an ingestion gap, and resolving it to anything hides
    the gap."""
    registry = PoolRegistry()
    registry.initialised(chain_id=CHAIN_ID, pool_manager=MANAGER["manager"], key=_key(POOLS[0]))
    with pytest.raises(UnknownPool):
        registry.route(chain_id=CHAIN_ID, pool_manager=MANAGER["manager"], pool_id="0x" + "11" * 32)


@pytest.mark.trace("REQ-WP-047")
def test_the_same_pool_on_another_chain_or_manager_is_another_pool() -> None:
    """Which is the whole reason the key has three parts."""
    registry = PoolRegistry()
    key = _key(POOLS[0])
    registry.initialised(chain_id=CHAIN_ID, pool_manager=MANAGER["manager"], key=key)
    for wrong in (
        {"chain_id": 8453, "pool_manager": MANAGER["manager"]},
        {"chain_id": CHAIN_ID, "pool_manager": "0x" + "22" * 20},
    ):
        with pytest.raises(UnknownPool):
            registry.route(pool_id=pool_id(key), **wrong)


@pytest.mark.trace("REQ-WP-047")
def test_a_routing_key_is_case_insensitive_about_addresses() -> None:
    """A log's address casing is not a fact about the pool, and two spellings of
    one manager must not be two managers."""
    assert RoutingKey(chain_id=1, pool_manager="0xAbC", pool_id="0xDEF") == RoutingKey(
        chain_id=1, pool_manager="0xabc", pool_id="0xdef"
    )


# --- what the hook makes unsafe -----------------------------------------------


@pytest.mark.trace("REQ-WP-047")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_every_live_pool_classifies_as_its_shape(raw: dict[str, Any]) -> None:
    expected = {
        "no_hook": ReconstructionClass.STANDARD_CL,
        "dynamic_fee": ReconstructionClass.DYNAMIC_FEE_CL,
        "hooked": ReconstructionClass.HOOK_AUGMENTED_CL,
        "returns_delta": ReconstructionClass.CUSTOM_ACCOUNTING,
    }[raw["shape"]]
    assert classify(_key(raw)) is expected


@pytest.mark.trace("REQ-WP-047")
def test_all_four_classes_that_exist_on_chain_are_covered_by_real_pools() -> None:
    """A constructed hook address would only test the test."""
    produced = {classify(_key(raw)) for raw in POOLS}
    assert produced == {
        ReconstructionClass.STANDARD_CL,
        ReconstructionClass.DYNAMIC_FEE_CL,
        ReconstructionClass.HOOK_AUGMENTED_CL,
        ReconstructionClass.CUSTOM_ACCOUNTING,
    }


@pytest.mark.trace("REQ-WP-047")
def test_permissions_are_read_from_the_hook_address_and_not_from_a_call() -> None:
    """Which is what makes the classification usable in a replay at all."""
    hooked = next(raw for raw in POOLS if raw["shape"] != "no_hook")
    key = _key(hooked)
    assert key.permissions == int(key.hooks, 16) & ALL_HOOK_MASK
    assert key.permissions != 0


@pytest.mark.trace("REQ-WP-047")
def test_custom_accounting_wins_over_every_class_it_also_qualifies_for() -> None:
    """The classes are not exclusive and the answer must forbid the most.

    A pool can carry a dynamic fee and a hook that returns swap deltas; calling
    it `DYNAMIC_FEE_CL` would say "depth is reconstructible, mind the fee" about
    a pool whose curve does not describe it.
    """
    hooks = HookFlag.BEFORE_SWAP | HookFlag.BEFORE_SWAP_RETURNS_DELTA
    both = PoolKey(
        currency0="0x01",
        currency1="0x02",
        fee=DYNAMIC_FEE_FLAG,
        tick_spacing=60,
        hooks=hex(hooks),
    )
    assert both.is_dynamic_fee
    assert both.permissions & RETURNS_DELTA_MASK
    assert classify(both) is ReconstructionClass.CUSTOM_ACCOUNTING


@pytest.mark.trace("REQ-WP-047")
def test_a_static_fee_pool_with_a_swap_hook_is_not_a_static_fee_pool() -> None:
    """`beforeSwap` may return an override and replace the LP fee for that swap,
    so the key's fee is not the fee charged."""
    key = PoolKey(
        currency0="0x01",
        currency1="0x02",
        fee=3000,
        tick_spacing=60,
        hooks=hex(HookFlag.BEFORE_SWAP),
    )
    assert not key.is_dynamic_fee
    assert classify(key) is ReconstructionClass.DYNAMIC_FEE_CL
    with pytest.raises(NotPointInTime):
        key_fee(key)


@pytest.mark.trace("REQ-WP-047")
def test_a_hook_that_only_watches_liquidity_leaves_the_fee_alone() -> None:
    """So the previous test's rule is about swap hooks, not about hooks."""
    key = PoolKey(
        currency0="0x01",
        currency1="0x02",
        fee=3000,
        tick_spacing=60,
        hooks=hex(HookFlag.AFTER_ADD_LIQUIDITY),
    )
    assert classify(key) is ReconstructionClass.HOOK_AUGMENTED_CL
    assert key_fee(key) == 3000


@pytest.mark.trace("REQ-WP-047")
def test_a_dynamic_fee_pool_refuses_to_report_its_key_s_fee() -> None:
    """The field holds a sentinel. Returned as a number it reads as a fee of
    839%, which is positive, ordered and believable."""
    raw = next(raw for raw in POOLS if raw["shape"] == "dynamic_fee")
    key = _key(raw)
    assert key.fee == DYNAMIC_FEE_FLAG
    with pytest.raises(NotPointInTime):
        key_fee(key)


@pytest.mark.trace("REQ-WP-047")
def test_a_standard_pool_reports_its_fee() -> None:
    raw = next(raw for raw in POOLS if raw["shape"] == "no_hook")
    assert key_fee(_key(raw)) == raw["fee"] <= MAX_LP_FEE


@pytest.mark.trace("REQ-WP-047")
def test_the_dynamic_fee_check_is_equality_and_not_a_bit_test() -> None:
    """`0x800001` has the high bit set and is not a dynamic fee; it is an invalid
    fee the manager rejects. A bit test would classify it as dynamic and quote
    it."""
    common = {
        "currency0": "0x01",
        "currency1": "0x02",
        "tick_spacing": 60,
        "hooks": hex(HookFlag.BEFORE_SWAP),
    }
    assert PoolKey(**common, fee=DYNAMIC_FEE_FLAG).is_dynamic_fee
    nearly = PoolKey(**common, fee=DYNAMIC_FEE_FLAG + 1)
    assert not nearly.is_dynamic_fee
    assert not is_valid(nearly)
    assert classify(nearly) is ReconstructionClass.UNKNOWN


# --- what the manager would have rejected ------------------------------------


@pytest.mark.trace("REQ-WP-047")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_every_live_pool_passes_the_manager_s_own_validation(raw: dict[str, Any]) -> None:
    """A reproduction of `isValidHookAddress` is only worth having if it accepts
    what the chain accepted."""
    assert is_valid(_key(raw))


@pytest.mark.trace("REQ-WP-047")
@pytest.mark.parametrize(
    ("fee", "hooks"),
    [
        # A dynamic fee with no hook: nothing to supply the fee.
        (DYNAMIC_FEE_FLAG, "0x00"),
        # A hook address with no permissions and a static fee: it would never be
        # called, so the manager refuses it. Note the trailing `00` -- the first
        # attempt used `0x40` repeated, whose low fourteen bits are `afterSwap`,
        # so it was a valid hook and the case proved nothing.
        (3000, "0x" + "40" * 19 + "00"),
        # Returns-delta without the action it belongs to, for each of the four.
        (3000, hex(HookFlag.BEFORE_SWAP_RETURNS_DELTA)),
        (3000, hex(HookFlag.AFTER_SWAP_RETURNS_DELTA)),
        (3000, hex(HookFlag.AFTER_ADD_LIQUIDITY_RETURNS_DELTA)),
        (3000, hex(HookFlag.AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA)),
        # A fee above the cap.
        (MAX_LP_FEE + 1, "0x00"),
    ],
)
def test_a_key_the_manager_would_reject_is_unknown_not_guessed_at(fee: int, hooks: str) -> None:
    """§18.8.1: `UNKNOWN` means raw data only, excluded from depth features.
    Classifying such a key by whatever its bits resemble is how a pool that
    cannot exist acquires a depth curve."""
    key = PoolKey(currency0="0x01", currency1="0x02", fee=fee, tick_spacing=60, hooks=hooks)
    assert not is_valid(key)
    assert classify(key) is ReconstructionClass.UNKNOWN


@pytest.mark.trace("REQ-WP-047")
def test_a_hook_with_an_action_and_its_delta_is_valid() -> None:
    """The mirror of the case above, so the pairing rule is not just "any
    returns-delta bit is invalid"."""
    key = PoolKey(
        currency0="0x01",
        currency1="0x02",
        fee=3000,
        tick_spacing=60,
        hooks=hex(HookFlag.AFTER_SWAP | HookFlag.AFTER_SWAP_RETURNS_DELTA),
    )
    assert is_valid(key)
    assert classify(key) is ReconstructionClass.CUSTOM_ACCOUNTING


@pytest.mark.trace("REQ-WP-047")
def test_the_fixture_names_one_manager_and_one_block_range() -> None:
    assert MANAGER["from_block"] < MANAGER["to_block"]
    assert all(MANAGER["from_block"] <= raw["block"] <= MANAGER["to_block"] for raw in POOLS)
