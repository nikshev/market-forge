"""Slipstream's fee is an observation, never a derivation (REQ-WP-045).

The fixture is the deployed `DynamicSwapFeeModule`'s own inputs and its own
answer, read at one pinned block from two independent RPC endpoints that
agreed. So these are not tests that a port looks reasonable; they are tests
that it *is* the contract, to the pip.

What makes that worth doing is how quietly the alternative fails. Slipstream's
`Swap` event is byte-identical to Uniswap v3's, so a v3 decoder reads every
Slipstream swap correctly and is wrong only about the fee -- and the fee it
would reach for, the tick-spacing default, is wrong for seven of the eight live
pools below.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex.aerodrome import (
    CL_FACTORIES,
    V2_FACTORY,
    PoolFamily,
    UnknownFamily,
    classify,
)
from channelflow.dex.slipstream import (
    _INT24_MAX,
    PIPS,
    ZERO_FEE_INDICATOR,
    FeeSchedule,
    ModuleDefaults,
    Oracle,
    PoolKey,
    SpacingNotEnabled,
    UnknownFee,
    default_fee,
    dynamic_term,
    pool_state,
    swap_fee,
    time_weighted_tick,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "aerodrome" / "slipstream_pools.jsonl"


def _lines() -> list[dict[str, Any]]:
    assert FIXTURE.is_file(), (
        f"missing fixture {FIXTURE}; regenerate with tools.record.slipstream_capture"
    )
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


def _of_kind(kind: str) -> list[dict[str, Any]]:
    return [line for line in _lines() if line["kind"] == kind]


POOLS = _of_kind("pool")
FACTORY = _of_kind("factory")[0]
MODULE = _of_kind("module")[0]
SPACING_DEFAULTS = {int(spacing): fee for spacing, fee in FACTORY["defaults"].items()}


def _defaults() -> ModuleDefaults:
    return ModuleDefaults(
        scaling_factor=int(MODULE["default_scaling_factor"]),
        fee_cap=MODULE["default_fee_cap"],
        seconds_ago=MODULE["seconds_ago"],
    )


def _schedule(raw: dict[str, Any]) -> FeeSchedule:
    return FeeSchedule(
        base_fee=raw["base_fee"],
        fee_cap=raw["fee_cap"],
        scaling_factor=int(raw["scaling_factor"]),
        initial_fee_enabled=raw["initial_fee_enabled"],
        initial_fee=raw["initial_fee"],
    )


def _oracle(raw: dict[str, Any]) -> Oracle:
    cumulatives = raw["tick_cumulatives"]
    return Oracle(
        tick=raw["tick"],
        observation_cardinality=raw["observation_cardinality"],
        tick_cumulatives=None if cumulatives is None else (cumulatives[0], cumulatives[1]),
    )


def _chain_fee(raw: dict[str, Any]) -> int:
    return swap_fee(
        schedule=_schedule(raw),
        defaults=_defaults(),
        oracle=_oracle(raw),
        spacing_default=SPACING_DEFAULTS[raw["tick_spacing"]],
    )


# --- the port is the contract -------------------------------------------------


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize("raw", POOLS, ids=[pool["pool"][:10] for pool in POOLS])
def test_the_computed_fee_is_the_fee_the_chain_charges(raw: dict[str, Any]) -> None:
    """Exact, not within tolerance. Every intermediate in the module is integer."""
    assert _chain_fee(raw) == raw["factory_fee"]


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize("raw", POOLS, ids=[pool["pool"][:10] for pool in POOLS])
def test_the_pool_and_the_factory_agree_about_the_fee(raw: dict[str, Any]) -> None:
    """`CLPool.fee()` forwards to the factory, so at one block these cannot differ.

    Recorded from both call sites deliberately: a fixture that read only one
    could not show that the pool has no fee of its own to disagree with.
    """
    assert raw["pool_fee"] == raw["factory_fee"]


# --- why a derivation cannot work ---------------------------------------------


@pytest.mark.trace("REQ-WP-045")
def test_the_spacing_default_is_not_what_pools_charge() -> None:
    """The number a Uniswap v3 decoder would reach for, measured against reality."""
    wrong = [pool for pool in POOLS if SPACING_DEFAULTS[pool["tick_spacing"]] != pool["pool_fee"]]
    assert len(wrong) >= len(POOLS) - 1, (
        "the tick-spacing default was expected to be wrong for nearly every live pool; "
        f"it matched for {len(POOLS) - len(wrong)} of {len(POOLS)}"
    )
    # And not wrong by a rounding error: one pool charges four times its default.
    ratios = [pool["pool_fee"] / SPACING_DEFAULTS[pool["tick_spacing"]] for pool in wrong]
    assert max(ratios) >= 2.0


@pytest.mark.trace("REQ-WP-045")
def test_the_spacing_table_maps_several_spacings_to_one_fee() -> None:
    """So the fee cannot identify the spacing either, in the other direction.

    In Uniswap v3 the two determine each other and a pool key may carry either.
    Here 10, 50 and 100 all default to 500, which is why `PoolKey` carries the
    spacing and nothing derives one from the other.
    """
    collisions = [
        fee
        for fee in set(SPACING_DEFAULTS.values())
        if sum(1 for value in SPACING_DEFAULTS.values() if value == fee) > 1
    ]
    assert collisions, f"expected a non-injective table, got {SPACING_DEFAULTS}"


@pytest.mark.trace("REQ-WP-045")
def test_some_pools_carry_a_live_dynamic_term() -> None:
    """The fee is not merely per-pool, it moves with the pool's own price."""
    moved = [pool for pool in POOLS if _chain_fee(pool) != pool["base_fee"]]
    assert moved, "no pool in the fixture had a dynamic component; recapture at a busier block"


@pytest.mark.trace("REQ-WP-045")
def test_a_pool_state_refuses_to_be_built_without_an_observed_fee() -> None:
    """`PoolState.fee_tier` is a constant, which is true of v3 and false here."""
    key = PoolKey(token0="0xaa", token1="0xbb", tick_spacing=100)
    with pytest.raises(UnknownFee):
        pool_state(key, address="0xpool", observed_fee=None)
    assert pool_state(key, address="0xpool", observed_fee=1414).fee_tier == 1414


@pytest.mark.trace("REQ-WP-045")
def test_the_pool_key_is_the_spacing_not_the_fee() -> None:
    """Two pools on one pair at two spacings share a default fee and are not one pool."""
    pair = {"token0": "0xaa", "token1": "0xbb"}
    assert PoolKey(**pair, tick_spacing=10) != PoolKey(**pair, tick_spacing=100)
    assert SPACING_DEFAULTS[10] == SPACING_DEFAULTS[100]


@pytest.mark.trace("REQ-WP-045")
def test_the_default_table_refuses_a_spacing_the_factory_does_not_enable() -> None:
    with pytest.raises(SpacingNotEnabled):
        default_fee(SPACING_DEFAULTS, 7)
    assert default_fee(SPACING_DEFAULTS, 200) == 3000


# --- the branches the live pools do not reach ---------------------------------


@pytest.mark.trace("REQ-WP-045")
def test_a_deliberate_zero_fee_is_not_an_unconfigured_one() -> None:
    """Stored zero means "nothing set"; 420 means "zero, on purpose"."""
    oracle = Oracle(tick=0, observation_cardinality=1000, tick_cumulatives=(0, 0))
    deliberate = FeeSchedule(base_fee=ZERO_FEE_INDICATOR, fee_cap=3000, scaling_factor=0)
    unset = FeeSchedule(base_fee=0, fee_cap=3000, scaling_factor=0)
    common = {"defaults": _defaults(), "oracle": oracle, "spacing_default": 500}
    assert swap_fee(schedule=deliberate, **common) == 0
    assert swap_fee(schedule=unset, **common) == 500


@pytest.mark.trace("REQ-WP-045")
def test_the_cap_binds_after_the_dynamic_term_and_not_before() -> None:
    """A pool that has moved far enough pays its cap, not base plus everything."""
    oracle = Oracle(tick=1_000, observation_cardinality=1000, tick_cumulatives=(0, 0))
    schedule = FeeSchedule(base_fee=2400, fee_cap=2800, scaling_factor=3_000_000)
    fee = swap_fee(schedule=schedule, defaults=_defaults(), oracle=oracle, spacing_default=3000)
    assert dynamic_term(oracle=oracle, scaling_factor=3_000_000, seconds_ago=600) == 3000
    assert fee == 2800


@pytest.mark.trace("REQ-WP-045")
def test_scaling_and_cap_are_substituted_together_or_not_at_all() -> None:
    """The contract swaps both when scaling is unset; swapping one caps a default.

    A pool with no scaling of its own but a tight cap of its own would otherwise
    have the module's default scaling squeezed through a cap that was never
    meant to apply to it.
    """
    oracle = Oracle(tick=1_000, observation_cardinality=1000, tick_cumulatives=(0, 0))
    schedule = FeeSchedule(base_fee=500, fee_cap=600, scaling_factor=0)
    defaults = ModuleDefaults(scaling_factor=3_000_000, fee_cap=30_000, seconds_ago=600)
    fee = swap_fee(schedule=schedule, defaults=defaults, oracle=oracle, spacing_default=500)
    assert fee == 3500, "the pool's own cap of 600 must not apply to the default scaling"


@pytest.mark.trace("REQ-WP-045")
def test_an_oracle_too_short_to_answer_charges_no_dynamic_term() -> None:
    moving = {"tick": 1_000, "tick_cumulatives": (0, 0)}
    schedule = FeeSchedule(base_fee=500, fee_cap=30_000, scaling_factor=3_000_000)
    common = {"schedule": schedule, "defaults": _defaults(), "spacing_default": 500}
    # 600 / MIN_SECONDS_AGO = 300 observations required.
    assert swap_fee(oracle=Oracle(observation_cardinality=299, **moving), **common) == 500
    assert swap_fee(oracle=Oracle(observation_cardinality=300, **moving), **common) == 3500


@pytest.mark.trace("REQ-WP-045")
def test_a_reverting_observe_charges_no_dynamic_term() -> None:
    """The module catches the revert. A port that let it propagate would refuse
    to quote a pool the chain quotes happily."""
    schedule = FeeSchedule(base_fee=500, fee_cap=30_000, scaling_factor=3_000_000)
    oracle = Oracle(tick=1_000, observation_cardinality=1000, tick_cumulatives=None)
    assert (
        swap_fee(schedule=schedule, defaults=_defaults(), oracle=oracle, spacing_default=500) == 500
    )


@pytest.mark.trace("REQ-WP-045")
def test_the_first_swap_of_a_block_can_be_charged_differently() -> None:
    """So a fee is not constant even within one block, let alone across blocks."""
    schedule = FeeSchedule(
        base_fee=500,
        fee_cap=30_000,
        scaling_factor=3_000_000,
        initial_fee_enabled=True,
        initial_fee=100,
    )
    common = {"schedule": schedule, "defaults": _defaults(), "spacing_default": 500}
    stale = Oracle(
        tick=1_000,
        observation_cardinality=1000,
        tick_cumulatives=(0, 0),
        observation_is_current=False,
    )
    current = Oracle(tick=1_000, observation_cardinality=1000, tick_cumulatives=(0, 0))
    assert swap_fee(oracle=stale, **common) == 100
    assert swap_fee(oracle=current, **common) == 3500


@pytest.mark.trace("REQ-WP-045")
@pytest.mark.parametrize(
    ("initial_fee", "expected"), [(0, 500), (ZERO_FEE_INDICATOR, 0), (100, 100)]
)
def test_the_initial_fee_has_its_own_three_way_sentinel(initial_fee: int, expected: int) -> None:
    schedule = FeeSchedule(
        base_fee=500,
        fee_cap=30_000,
        scaling_factor=3_000_000,
        initial_fee_enabled=True,
        initial_fee=initial_fee,
    )
    oracle = Oracle(
        tick=1_000,
        observation_cardinality=1000,
        tick_cumulatives=(0, 0),
        observation_is_current=False,
    )
    fee = swap_fee(schedule=schedule, defaults=_defaults(), oracle=oracle, spacing_default=500)
    assert fee == expected


# --- the arithmetic itself ----------------------------------------------------


@pytest.mark.trace("REQ-WP-045")
def test_the_average_tick_truncates_toward_zero_as_solidity_does() -> None:
    """Python floors and Solidity truncates, and tick cumulatives go negative.

    They differ by exactly one tick on every negative average that does not
    divide evenly -- which, multiplied by a scaling factor of 3e6, is three
    pips of fee on a pool that had none.
    """
    # -599 / 600 is 0 truncated, -1 floored.
    assert time_weighted_tick((0, -599), 600) == 0
    assert (0 - 599) // 600 == -1
    assert time_weighted_tick((0, 599), 600) == 0
    assert time_weighted_tick((0, -1200), 600) == -2


@pytest.mark.trace("REQ-WP-045")
def test_a_negative_average_tick_still_contributes_its_distance() -> None:
    """The dynamic term is the absolute gap; a pool falling pays like one rising."""
    rising = Oracle(tick=100, observation_cardinality=1000, tick_cumulatives=(0, 0))
    falling = Oracle(tick=-100, observation_cardinality=1000, tick_cumulatives=(0, 0))
    term = {"scaling_factor": 3_000_000, "seconds_ago": 600}
    assert dynamic_term(oracle=rising, **term) == dynamic_term(oracle=falling, **term) == 300


@pytest.mark.trace("REQ-WP-045")
def test_the_discount_rounds_in_the_payer_s_favour() -> None:
    """`mulDivRoundingUp` on the discount rounds the fee down, not up.

    Rounding the other way overstates the fee by a pip on most pools -- small,
    unidirectional, and therefore exactly the kind of drift a tolerance hides.
    """
    oracle = Oracle(tick=0, observation_cardinality=1000, tick_cumulatives=(0, 0))
    schedule = FeeSchedule(base_fee=1001, fee_cap=30_000, scaling_factor=0)
    common = {
        "schedule": schedule,
        "defaults": _defaults(),
        "oracle": oracle,
        "spacing_default": 500,
    }
    # 1001 * 1 / 1e6 = 0.001001, which rounds up to a whole pip of discount.
    assert swap_fee(discount_pips=1, **common) == 1000
    assert swap_fee(**common) == 1001
    # And at half the maximum, the arithmetic is the contract's, not a float's.
    assert swap_fee(discount_pips=250_000, **common) == 1001 - (1001 * 250_000 + PIPS - 1) // PIPS


# --- what a pool is -----------------------------------------------------------


@pytest.mark.trace("REQ-WP-045")
def test_every_captured_pool_classifies_as_slipstream() -> None:
    assert FACTORY["factory"].lower() in CL_FACTORIES
    assert classify(factory=FACTORY["factory"], stable=None) is PoolFamily.SLIPSTREAM_CL


@pytest.mark.trace("REQ-WP-045")
def test_the_curve_comes_from_the_factory_and_never_from_a_guess() -> None:
    assert classify(factory=V2_FACTORY, stable=True) is PoolFamily.V2_STABLE
    assert classify(factory=V2_FACTORY, stable=False) is PoolFamily.V2_VOLATILE
    # A v2 pool that did not answer is refused, not assumed to be the common case.
    with pytest.raises(UnknownFamily):
        classify(factory=V2_FACTORY, stable=None)
    # And so is a shape nobody has written an adapter for yet.
    with pytest.raises(UnknownFamily):
        classify(factory="0x0000000000000000000000000000000000000001", stable=False)


@pytest.mark.trace("REQ-WP-045")
def test_all_three_slipstream_factories_are_recognised() -> None:
    """Three CL factories are live on Base and all hold pools.

    Recognising only the original -- the one this fixture reads -- would leave
    a third of the venue's CL pools falling through to `UnknownFamily`.
    """
    assert len(CL_FACTORIES) == 3
    for factory in CL_FACTORIES:
        assert classify(factory=factory, stable=None) is PoolFamily.SLIPSTREAM_CL


@pytest.mark.trace("REQ-WP-045")
def test_the_fixture_is_one_block() -> None:
    """A fee assembled across blocks pairs one block's tick with another's average."""
    blocks = {line["block"] for line in _lines()}
    assert len(blocks) == 1, f"fixture spans {sorted(blocks)}"


@pytest.mark.trace("REQ-WP-045")
def test_an_average_tick_beyond_int24_wraps_as_the_contract_casts_it() -> None:
    """Unreachable from a healthy pool, and ported anyway.

    A pool's tick is bounded to +/-887272, so no real oracle produces an average
    outside `int24`. The contract still casts, and a port that quietly behaved
    better than the contract would be a port that disagrees with it -- which is
    the one thing this module must never do.

    Found by a mutation sweep: replacing the cast with the identity left every
    other assertion passing.
    """
    beyond = _INT24_MAX + 2
    assert time_weighted_tick((0, beyond * 600), 600) == beyond - (1 << 24)
    assert time_weighted_tick((0, _INT24_MAX * 600), 600) == _INT24_MAX
