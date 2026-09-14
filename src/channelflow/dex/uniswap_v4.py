"""Uniswap v4: one contract, every pool, and the hook address says what is safe.

# @trace: REQ-WP-047

PRD section 18.8 opens with the prohibition: v4 *"must not be implemented as
'v3 with a different factory'"*. Two things make that more than style.

**One address emits everything.** Section 18.8.2: *"Because many pools emit
through the same manager contract, filtering by contract address is
insufficient."* Measured on Ethereum mainnet, 2960 pools were initialised in a
forty-thousand-block window and **every one of them through a single address**.
A v3-shaped ingestion keyed on `(chain_id, address)` would file all of them under
one pool. The key is `(chain_id, pool_manager, pool_id)`.

**`PoolId` is a hash of the pool's configuration, not a counter.** `toId` is
`keccak256(poolKey, 0xa0)` -- five 32-byte slots, so ABI-*encoded* rather than
packed, with `int24 tickSpacing` sign-extended across a whole word. Packing it,
or sign-extending it wrongly, yields a 32-byte value indistinguishable from a
pool id except that it identifies nothing.

**The hook's permissions are in the hook's address.** Not in its code, not in a
call: `Hooks.sol` reads the low fourteen bits of the address, and a hook is
deployed to an address whose bits match what it implements. So section 18.8.1's
reconstruction class is derivable offline from the `Initialize` log alone, which
is what makes it usable in a replay.

Four of those fourteen bits are the ones that matter most -- the "returns delta"
permissions, which are exactly what let a hook change the amounts a swap moves.
A pool whose hook holds any of them is `CUSTOM_ACCOUNTING`: the standard curve
does not describe it, and a depth figure computed from ticks would be a
confident answer to the wrong question.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from eth_hash.auto import keccak

#: `LPFeeLibrary.DYNAMIC_FEE_FLAG`. The check in the source is equality, not a
#: bit test: a dynamic-fee pool's key holds exactly this value.
DYNAMIC_FEE_FLAG = 0x800000

#: `LPFeeLibrary.OVERRIDE_FEE_FLAG`, which a `beforeSwap` hook may return to
#: override the LP fee for one swap -- on a static-fee pool too.
OVERRIDE_FEE_FLAG = 0x400000

#: `LPFeeLibrary.MAX_LP_FEE`, 100% in hundredths of a basis point.
MAX_LP_FEE = 1_000_000

#: `Hooks.ALL_HOOK_MASK`: the low fourteen bits of a hook address.
ALL_HOOK_MASK = (1 << 14) - 1


class HookFlag:
    """`Hooks.sol`'s flag layout, bit for bit."""

    BEFORE_INITIALIZE = 1 << 13
    AFTER_INITIALIZE = 1 << 12
    BEFORE_ADD_LIQUIDITY = 1 << 11
    AFTER_ADD_LIQUIDITY = 1 << 10
    BEFORE_REMOVE_LIQUIDITY = 1 << 9
    AFTER_REMOVE_LIQUIDITY = 1 << 8
    BEFORE_SWAP = 1 << 7
    AFTER_SWAP = 1 << 6
    BEFORE_DONATE = 1 << 5
    AFTER_DONATE = 1 << 4
    BEFORE_SWAP_RETURNS_DELTA = 1 << 3
    AFTER_SWAP_RETURNS_DELTA = 1 << 2
    AFTER_ADD_LIQUIDITY_RETURNS_DELTA = 1 << 1
    AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA = 1 << 0


#: The four permissions that let a hook change the amounts a swap or a liquidity
#: change moves. These are what separate "a hook runs alongside the curve" from
#: "the curve no longer describes this pool".
RETURNS_DELTA_MASK = (
    HookFlag.BEFORE_SWAP_RETURNS_DELTA
    | HookFlag.AFTER_SWAP_RETURNS_DELTA
    | HookFlag.AFTER_ADD_LIQUIDITY_RETURNS_DELTA
    | HookFlag.AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA
)

#: Permissions that mean a swap's fee is not the key's fee.
FEE_TOUCHING_MASK = HookFlag.BEFORE_SWAP | HookFlag.AFTER_SWAP

_UINT24 = (1 << 24) - 1
_INT24_SPAN = 1 << 24
_INT24_MAX = (1 << 23) - 1
_ADDRESS_MASK = (1 << 160) - 1


class ReconstructionClass(StrEnum):
    """Section 18.8.1's classes, with the rules it attaches to each.

    The order of the members is the order of restriction, loosest first, which
    is the opposite of the order `classify` tests them in.
    """

    STANDARD_CL = "STANDARD_CL"
    DYNAMIC_FEE_CL = "DYNAMIC_FEE_CL"
    HOOK_AUGMENTED_CL = "HOOK_AUGMENTED_CL"
    CUSTOM_ACCOUNTING = "CUSTOM_ACCOUNTING"
    UNKNOWN = "UNKNOWN"


class UnknownPool(LookupError):
    """A routed event named a pool id the registry has never seen initialised.

    Refused rather than resolved to a guess. A `PoolId` is a hash, so there is
    nothing in it to fall back on -- an event for an unknown pool is an
    ingestion gap, and treating it as anything else hides the gap.
    """


class NotPointInTime(ValueError):
    """A dynamic or overridable fee was asked for from the pool key alone.

    Section 18.8.1 requires a `DYNAMIC_FEE_CL` pool's "effective fee must be
    point-in-time". The key's fee field is a sentinel, not a fee, and a hook may
    override even a static one -- so the fee has to come from the swap, and
    asking the key for it is a question with no answer.
    """


@dataclass(frozen=True)
class PoolKey:
    """v4's pool configuration, and the preimage of its id.

    Currencies are sorted numerically by the manager, so an unsorted pair is a
    different key and hashes to a pool that does not exist.
    """

    currency0: str
    currency1: str
    fee: int
    tick_spacing: int
    hooks: str

    def __post_init__(self) -> None:
        if not 0 <= self.fee <= _UINT24:
            raise ValueError(f"fee does not fit in uint24: {self.fee}")
        if not -_INT24_MAX - 1 <= self.tick_spacing <= _INT24_MAX:
            raise ValueError(f"tick spacing does not fit in int24: {self.tick_spacing}")

    @property
    def has_hook(self) -> bool:
        return int(self.hooks, 16) != 0

    @property
    def permissions(self) -> int:
        """The hook's declared permissions, read off its address."""
        return int(self.hooks, 16) & ALL_HOOK_MASK

    @property
    def is_dynamic_fee(self) -> bool:
        """`LPFeeLibrary.isDynamicFee`: equality with the sentinel, not a bit test.

        A fee of `0x800001` has the high bit set and is not a dynamic fee; it is
        an invalid fee, which the manager rejects.
        """
        return self.fee == DYNAMIC_FEE_FLAG


def _word(value: int) -> bytes:
    return (value & ((1 << 256) - 1)).to_bytes(32, "big")


def pool_id(key: PoolKey) -> str:
    """`keccak256(abi.encode(poolKey))`, which is what the manager computes.

    Five whole words. `tick_spacing` is a signed 24-bit value sign-extended to
    256 bits -- so a spacing of -1 contributes a word of `0xff…ff`, not
    `0x00…00ffffff`, and getting that wrong changes the id of every pool with a
    negative spacing while leaving every other pool's id correct.
    """
    encoded = (
        _word(int(key.currency0, 16) & _ADDRESS_MASK)
        + _word(int(key.currency1, 16) & _ADDRESS_MASK)
        + _word(key.fee)
        + _word(key.tick_spacing)
        + _word(int(key.hooks, 16) & _ADDRESS_MASK)
    )
    return "0x" + keccak(encoded).hex()


def is_valid(key: PoolKey) -> bool:
    """`Hooks.isValidHookAddress` plus the fee bound the manager enforces.

    Reproduced so that a key the manager would have rejected classifies as
    `UNKNOWN` rather than as whatever its bits happen to resemble.
    """
    if key.fee != DYNAMIC_FEE_FLAG and key.fee > MAX_LP_FEE:
        return False

    permissions = key.permissions
    paired = (
        (HookFlag.BEFORE_SWAP, HookFlag.BEFORE_SWAP_RETURNS_DELTA),
        (HookFlag.AFTER_SWAP, HookFlag.AFTER_SWAP_RETURNS_DELTA),
        (HookFlag.AFTER_ADD_LIQUIDITY, HookFlag.AFTER_ADD_LIQUIDITY_RETURNS_DELTA),
        (HookFlag.AFTER_REMOVE_LIQUIDITY, HookFlag.AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA),
    )
    for action, returns_delta in paired:
        if permissions & returns_delta and not permissions & action:
            return False

    if not key.has_hook:
        # No hook means no source for a dynamic fee.
        return not key.is_dynamic_fee
    return bool(permissions) or key.is_dynamic_fee


def classify(key: PoolKey) -> ReconstructionClass:
    """Section 18.8.1's class, from the key alone.

    Tested most restrictive first, because the classes are not exclusive: a pool
    can carry a dynamic fee *and* a hook that returns deltas, and the answer has
    to be the one that forbids the most.
    """
    if not is_valid(key):
        return ReconstructionClass.UNKNOWN

    permissions = key.permissions
    if permissions & RETURNS_DELTA_MASK:
        return ReconstructionClass.CUSTOM_ACCOUNTING
    if key.is_dynamic_fee or permissions & FEE_TOUCHING_MASK:
        # A swap hook can return an override fee even on a static-fee pool, so
        # the two cases are the same fact: depth is reconstructible, the fee is
        # not knowable in advance.
        return ReconstructionClass.DYNAMIC_FEE_CL
    if permissions:
        return ReconstructionClass.HOOK_AUGMENTED_CL
    return ReconstructionClass.STANDARD_CL


#: Section 18.8.1's classes that permit a standard depth reconstruction.
#:
#: A permit list, not a deny list. `CUSTOM_ACCOUNTING` is excluded because the
#: section says so outright; `UNKNOWN` because it gets "raw data only; exclude
#: from predictive depth features", which is the same prohibition reached by a
#: different route. A class added later is excluded until somebody decides
#: otherwise, which is the safe direction to fail.
CURVE_RECONSTRUCTIBLE = frozenset(
    {
        ReconstructionClass.STANDARD_CL,
        ReconstructionClass.DYNAMIC_FEE_CL,
        ReconstructionClass.HOOK_AUGMENTED_CL,
    }
)


class CurveDoesNotApply(ValueError):
    """The tick kernel was asked about a pool whose class forbids it.

    Raised rather than answered, because the answer the kernel would give is
    the dangerous one. Measured at block 25975796: three of the four
    `CUSTOM_ACCOUNTING` pools in `tests/fixtures/uniswap_v4/` hold zero
    liquidity in the manager, so a tick traversal reports "the pool has no
    active liquidity, so its price cannot be moved" -- and two of those three
    absorb a whole ether. The liquidity is in the hook.
    """


def require_curve_applies(key: PoolKey) -> None:
    """Refuse the standard curve where section 18.8.1 refuses it.

    The gate is on the class rather than on the reconstructed state because the
    class is the only place the information exists. A `PoolState` built from
    such a pool passes `require_tick_map_complete` -- an empty tick map explains
    a pool reporting zero liquidity exactly -- and nothing downstream of that
    can tell the difference. The hook address can.
    """
    found = classify(key)
    if found in CURVE_RECONSTRUCTIBLE:
        return
    raise CurveDoesNotApply(
        f"pool {pool_id(key)} is {found.value}; section 18.8.1 does not permit the "
        f"standard curve here, and a depth from it would report the pool as empty "
        f"rather than failing. Quote it instead. Permitted: "
        f"{', '.join(sorted(c.value for c in CURVE_RECONSTRUCTIBLE))}"
    )


def key_fee(key: PoolKey) -> int:
    """The pool's LP fee, where the key is allowed to answer at all.

    Refuses for a dynamic fee and for a pool whose hook can override one. The
    alternative -- returning the sentinel `0x800000` as though it were a fee of
    839%, or a static fee a hook silently replaces -- is the shape of error this
    whole module exists to head off.
    """
    if key.is_dynamic_fee or key.permissions & FEE_TOUCHING_MASK:
        raise NotPointInTime(f"fee for {pool_id(key)} must come from the swap, not the key")
    return key.fee


@dataclass(frozen=True)
class RoutingKey:
    """Section 18.8.2's required key. Not the emitting address."""

    chain_id: int
    pool_manager: str
    pool_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "pool_manager", self.pool_manager.lower())
        object.__setattr__(self, "pool_id", self.pool_id.lower())


class PoolRegistry:
    """`PoolId` back to `PoolKey`, per manager per chain.

    The registry is built from `Initialize` events and nothing else, because
    that is the only place the preimage appears: a `Swap` log carries the id
    alone, and a hash cannot be inverted.
    """

    def __init__(self) -> None:
        self._keys: dict[RoutingKey, PoolKey] = {}

    def initialised(self, *, chain_id: int, pool_manager: str, key: PoolKey) -> RoutingKey:
        """Record a pool, deriving its id rather than trusting one.

        Deriving is the point: if the derivation is wrong, every routing lookup
        misses, loudly, instead of a fraction of them landing on the wrong pool.
        """
        route = RoutingKey(chain_id=chain_id, pool_manager=pool_manager, pool_id=pool_id(key))
        self._keys[route] = key
        return route

    def resolve(self, route: RoutingKey) -> PoolKey:
        if route not in self._keys:
            raise UnknownPool(route)
        return self._keys[route]

    def route(
        self, *, chain_id: int, pool_manager: str, pool_id: str
    ) -> tuple[RoutingKey, PoolKey]:
        """Where an event belongs, and what the pool is."""
        candidate = RoutingKey(chain_id=chain_id, pool_manager=pool_manager, pool_id=pool_id)
        return candidate, self.resolve(candidate)

    def __len__(self) -> int:
        return len(self._keys)
