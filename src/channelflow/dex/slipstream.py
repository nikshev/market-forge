"""Aerodrome Slipstream: a Uniswap v3 fork whose fee is not a constant.

# @trace: REQ-WP-045

PRD section 18.10 asks for `SLIPSTREAM_CL` as a shape distinct from Aerodrome's
v2 curves. The concentrated-liquidity arithmetic is Uniswap v3's and is already
[[REQ-WP-015]]'s: tick map, active liquidity, depth by traversal. This module
is the part that is not shared, and the reason a shared decoder is dangerous
rather than merely incomplete.

**The `Swap` event is byte-identical to Uniswap v3's.** Same argument list,
same topic hash, same decoding. A v3 decoder pointed at a Slipstream pool
produces correct amounts, a correct price and a correct tick, and is wrong
about only one thing -- and never says so.

**What differs is everything around the event.**

*The pool key is `(token0, token1, tickSpacing)`, not `(token0, token1, fee)`.*
The factory's own table is not injective: spacings 10, 50 and 100 all default
to 500 pips. In Uniswap v3, fee determines spacing; here neither determines the
other, so any derivation between them is guesswork with a plausible answer.

*The fee is not a property of the pool.* `CLPool.fee()` forwards to
`ICLFactory.getSwapFee(pool)`, which forwards to a swap fee module. The module
in force on Base computes

    fee = min(baseFee + |tick - twAvgTick| * K / 1e6, feeCap)

from the pool's own oracle. It changes with the price, every block, with no
transaction and no event to subscribe to. Of the eight live pools in this
module's fixture, seven charge something other than their spacing's default,
and three carry a dynamic term at the pinned block.

*The fee can also depend on who is asking.* The module subtracts a registered
discount keyed on `tx.origin`, so a fee read with `eth_call` and no sender is
the undiscounted one -- correct for a venue-level quote, wrong for a particular
account's execution. That is a parameter here, never a default.

So a Slipstream fee is **an observation at a block, for a caller**, and this
module computes it the way the chain does rather than looking it up. The port
is exact integer arithmetic against `DynamicSwapFeeModule.getFee`, which lets
the tests assert equality with the chain rather than a tolerance -- the same
standard the v2 curves are held to in `aerodrome.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.dex.pool import PoolState

#: The module's fixed-point base, `SCALING_PRECISION`, and the denominator fees
#: and discounts are quoted in. A fee of 500 is 0.05%.
PIPS = 1_000_000

#: `ZERO_FEE_INDICATOR`. A stored zero means "nothing configured", so the
#: contract needs a sentinel for a deliberate zero fee, and 420 is it.
ZERO_FEE_INDICATOR = 420

#: `MIN_SECONDS_AGO`. The oracle must hold at least `secondsAgo / MIN_SECONDS_AGO`
#: observations before the module will read a time-weighted tick from it.
MIN_SECONDS_AGO = 2

#: `MAX_FEE_CAP`, 5%. The module refuses to configure a cap above this.
MAX_FEE_CAP = 50_000

_INT24_SPAN = 1 << 24
_INT24_MAX = (1 << 23) - 1


class UnknownFee(LookupError):
    """A quote was asked for without an observed fee.

    There is deliberately no fallback. The tick-spacing default is wrong for
    seven of the eight pools this module's fixture records, so returning it
    would produce a plausible number and no symptom -- which is the failure
    this module exists to prevent.
    """


class SpacingNotEnabled(LookupError):
    """The factory does not enable this tick spacing.

    A pool cannot exist at a spacing the factory has not enabled, so being
    asked about one means the caller's pool identity is wrong.
    """


@dataclass(frozen=True)
class PoolKey:
    """What identifies a Slipstream pool.

    Tick spacing, not fee. Two pools on the same pair at spacings 10 and 100
    both default to 500 pips and are different pools; a key built from the fee
    would collide them.
    """

    token0: str
    token1: str
    tick_spacing: int


@dataclass(frozen=True)
class FeeSchedule:
    """The module's per-pool configuration, as read at one block.

    `base_fee` of zero means "not configured, fall back to the spacing
    default"; `ZERO_FEE_INDICATOR` means a deliberate zero. `scaling_factor` of
    zero means "use the module's defaults", and takes `fee_cap` with it -- the
    contract substitutes both together, so substituting one would cap a default
    scaling at a pool-specific cap that was never meant to apply to it.
    """

    base_fee: int
    fee_cap: int
    scaling_factor: int
    initial_fee_enabled: bool = False
    initial_fee: int = 0


@dataclass(frozen=True)
class ModuleDefaults:
    """What the module applies to a pool that configured no scaling of its own."""

    scaling_factor: int
    fee_cap: int
    seconds_ago: int


@dataclass(frozen=True)
class Oracle:
    """What the pool's own oracle says at the block being priced.

    `tick_cumulatives` is None where `observe` would revert -- a pool whose
    history does not reach back `seconds_ago`. The module catches that and
    charges no dynamic term, so the distinction has to survive into this
    module rather than being flattened into a zero somewhere upstream.

    `observation_is_current` is whether the newest observation carries this
    block's timestamp. It gates the initial-fee path, which charges the first
    swap of a block differently from the rest -- so a fee is not even constant
    within one block.
    """

    tick: int
    observation_cardinality: int
    tick_cumulatives: tuple[int, int] | None
    observation_is_current: bool = True


def _as_int24(value: int) -> int:
    """The contract's `int24(...)` cast, wrap included.

    Reachable only from an oracle reporting an average tick outside the range a
    pool can occupy, which is to say never on a healthy pool. Ported anyway: a
    port that silently behaves better than the contract is a port that
    disagrees with it, and the whole point here is that it does not.
    """
    return (value + _INT24_MAX + 1) % _INT24_SPAN - _INT24_MAX - 1


def _truncating_division(numerator: int, denominator: int) -> int:
    """Solidity's `/`, which truncates toward zero.

    Python's `//` floors, so the two differ by one on every negative numerator
    that does not divide evenly -- and tick cumulatives are routinely negative.
    """
    quotient = abs(numerator) // denominator
    return quotient if numerator >= 0 else -quotient


def time_weighted_tick(cumulatives: tuple[int, int], seconds_ago: int) -> int:
    """The oracle's average tick over `seconds_ago`, as the module reads it."""
    return _as_int24(_truncating_division(cumulatives[1] - cumulatives[0], seconds_ago))


def dynamic_term(
    *,
    oracle: Oracle,
    scaling_factor: int,
    seconds_ago: int,
) -> int:
    """How much the pool's recent movement adds to its fee.

    Zero in three distinct cases, and they are different facts: an oracle too
    short to answer, an `observe` that reverted, and a pool that has not moved.
    The contract collapses all three to zero and so does this; what it must not
    do is collapse them somewhere the caller can no longer tell them apart.
    """
    if oracle.observation_cardinality < seconds_ago // MIN_SECONDS_AGO:
        return 0
    if oracle.tick_cumulatives is None:
        return 0
    delta = oracle.tick - time_weighted_tick(oracle.tick_cumulatives, seconds_ago)
    return abs(delta) * scaling_factor // PIPS


def swap_fee(
    *,
    schedule: FeeSchedule,
    defaults: ModuleDefaults,
    oracle: Oracle,
    spacing_default: int,
    discount_pips: int = 0,
) -> int:
    """What the pool charges, in pips, at the block the oracle describes.

    A port of `DynamicSwapFeeModule.getFee`, in the contract's own order --
    which matters, because the cap applies to base plus dynamic and the
    discount applies after the cap. Reordering any of the three produces a
    number that is right for most pools and wrong for the ones near a bound.
    """
    if schedule.base_fee == ZERO_FEE_INDICATOR:
        return 0

    base_fee = schedule.base_fee if schedule.base_fee != 0 else spacing_default

    if schedule.initial_fee_enabled and not oracle.observation_is_current:
        if schedule.initial_fee == 0:
            return base_fee
        if schedule.initial_fee == ZERO_FEE_INDICATOR:
            return 0
        return schedule.initial_fee

    scaling_factor, fee_cap = schedule.scaling_factor, schedule.fee_cap
    if scaling_factor == 0:
        scaling_factor, fee_cap = defaults.scaling_factor, defaults.fee_cap

    total = base_fee + dynamic_term(
        oracle=oracle, scaling_factor=scaling_factor, seconds_ago=defaults.seconds_ago
    )
    total = min(total, fee_cap)

    if discount_pips > 0:
        # Rounding up, as the contract does: the discount is subtracted, so
        # rounding it up rounds the fee down, and a port that rounded the other
        # way would overstate the fee by a pip on most pools.
        total -= (total * discount_pips + PIPS - 1) // PIPS
    return total


def default_fee(spacing_defaults: dict[int, int], tick_spacing: int) -> int:
    """The factory's default fee for a tick spacing.

    Here for one purpose: so a caller can *compare* it with the observed fee and
    see how far apart they are. It is not a fallback and `swap_fee` never reads
    it except as `spacing_default`, which the caller must have observed.
    """
    if tick_spacing not in spacing_defaults:
        raise SpacingNotEnabled(tick_spacing)
    return spacing_defaults[tick_spacing]


def pool_state(
    key: PoolKey,
    *,
    address: str,
    observed_fee: int | None,
    current_tick: int = 0,
    sqrt_price_x96: int = 0,
) -> PoolState:
    """A CL pool state for [[REQ-WP-015]]'s kernel, with the fee's provenance forced.

    `PoolState.fee_tier` is a single number the depth kernel treats as constant,
    which is true of Uniswap v3 and false here. Passing `observed_fee=None`
    raises rather than substituting a default, so a Slipstream pool cannot enter
    the kernel carrying a fee nobody read off the chain.
    """
    if observed_fee is None:
        raise UnknownFee(address)
    return PoolState(
        address=address,
        token0=key.token0,
        token1=key.token1,
        fee_tier=observed_fee,
        tick_spacing=key.tick_spacing,
        current_tick=current_tick,
        sqrt_price_x96=sqrt_price_x96,
    )
