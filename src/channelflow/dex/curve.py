"""Curve: an invariant family, quoted from state rather than from a tick map.

# @trace: REQ-WP-046

PRD section 18.9 opens by ruling out the shortcut -- *"Curve must be modeled as
an invariant/quote-based AMM family rather than as a tick-based AMM"* -- and
section 18.9.1 says it again about depth: *"Do not derive a fake tick map."*

**Six shapes, one venue, and the pool does not announce which.** What it does
do is answer some functions and revert on others, so `classify` reads a set of
capabilities observed on the chain rather than a name, a token pair or a
factory's word. The discriminators here were measured against live pools, and
two plausible ones did not survive that:

* `base_pool()` identifies no metapool -- none answers it;
* `get_dy_underlying` identifies no metapool either -- the original 3pool
  answers it, having inherited a lending-pool interface it does not use.

What actually makes a metapool a metapool is that one of its coins is another
pool's LP token, and that is a fact about the registry rather than about the
pool. So it is read from Curve's MetaRegistry and passed in, with a third state
for "the registry does not know this address" — which is the answer *this is
not a Curve pool*, and must not be flattened into "a Curve pool that is not a
metapool".

**The quote is Stableswap-NG's own.** `CurveStableSwapNGViews.get_dy` is ported
here exactly, integer for integer, which lets the tests assert equality with the
chain rather than the tolerance section 18.25 allows. Three things in it are
easy to get plausibly wrong:

* **The fee denominator is 1e10**, not the 1e6 every other venue in this project
  uses. Off by ten thousand, in the direction of charging nothing.
* **The fee is not the base fee.** Stableswap-NG scales it by how far off peg
  the two coins sit, so a fee read once and cached is wrong in exactly the
  states that matter most. All four pools in this module's fixture have the
  multiplier switched on.
* **Balances are not `xp`.** Each coin carries a stored rate that folds in its
  decimals and, for a vault share or an accruing token, its current exchange
  rate. Quoting on raw balances is the same class of error as reading a venue's
  contract sizes as base units.

**Why the maths is here at all**, when section 18.9.1 permits a verified view
function and the pool has one: a depth curve reconstructed from stored state at
a past event time has no contract to call at that state. The view function is
the authority this is checked against, not the way it answers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

#: Curve's fee denominator. Not 1e6, which is what every other venue in this
#: project uses and what a careless port would assume.
FEE_DENOMINATOR = 10**10

#: The 1e18 base every balance is normalised to before the invariant sees it.
PRECISION = 10**18

#: `A` is stored scaled by this, so that it can be ramped in fractions.
A_PRECISION = 100

#: Basis points, for the depth grid section 18.9.1 asks for.
BPS = 10_000

#: Both Newton searches revert past this rather than returning an estimate.
MAX_ITERATIONS = 255


def _n_to_the_n(n_coins: int) -> int:
    """`n**n`, kept honest.

    Python's `**` is typed as possibly returning a float, and letting that
    escape here would make every integer below it a float by inference -- which
    is precisely the drift a bit-exact port cannot afford.
    """
    return int(n_coins**n_coins)


class DidNotConverge(RuntimeError):
    """A Newton search ran out of iterations.

    The contract raises here, and its comment says why: convergence takes four
    rounds or less, so reaching 255 means the pool is in a state nobody should
    quote from. Returning the last estimate would hand back a number that looks
    like a quote and is not one.
    """


class WrongFamily(ValueError):
    """This quote maths does not belong to this pool's shape.

    Refusing is the point. Every family here produces a positive, ordered,
    believable number from the wrong invariant, and nothing downstream shows a
    symptom.
    """


class PoolFamily(StrEnum):
    """Section 18.9's enumeration.

    `CRYPTOSWAP_NG` is absent deliberately: nothing observable on a live pool
    separates it from `CRYPTOSWAP` yet, and a classifier that guessed would be
    worse than one that does not offer the distinction.
    """

    STABLESWAP = "STABLESWAP"
    STABLESWAP_NG = "STABLESWAP_NG"
    CRYPTOSWAP = "CRYPTOSWAP"
    META_POOL = "META_POOL"
    UNKNOWN = "OTHER/UNKNOWN"


@dataclass(frozen=True)
class Capabilities:
    """What a pool answered when asked, at one block.

    Every field is an observation. A revert is an answer -- "no" -- and so is
    empty return data, which is what a contract with a payable fallback gives
    to any selector at all.

    `is_meta` is `None` where Curve's registry does not know the address, which
    is the answer *this is not a Curve pool*.
    """

    get_dy_int128: bool = False
    get_dy_uint256: bool = False
    offpeg_fee_multiplier: bool = False
    gamma: bool = False
    price_scale: bool = False
    price_scale_indexed: bool = False
    is_meta: bool | None = None


def classify(capabilities: Capabilities) -> PoolFamily:
    """Which shape a pool is, from what it answers and what the registry says.

    Order matters. A metapool is a metapool whatever curve it runs, so the
    registry's answer is read before the pool's own.
    """
    if capabilities.is_meta:
        return PoolFamily.META_POOL
    if capabilities.get_dy_uint256 and capabilities.gamma:
        return PoolFamily.CRYPTOSWAP
    if capabilities.get_dy_int128:
        return (
            PoolFamily.STABLESWAP_NG
            if capabilities.offpeg_fee_multiplier
            else PoolFamily.STABLESWAP
        )
    return PoolFamily.UNKNOWN


@dataclass(frozen=True)
class StableSwapNGState:
    """A Stableswap-NG pool as of one block.

    `stored_rates` is state, not configuration: for a vault share or an
    accruing token it moves every block, and section 18.9 lists it among what
    must be tracked for exactly that reason.
    """

    balances: tuple[int, ...]
    stored_rates: tuple[int, ...]
    amplification: int
    fee: int
    offpeg_fee_multiplier: int

    def __post_init__(self) -> None:
        if len(self.balances) != len(self.stored_rates):
            raise ValueError("a rate per coin, or the indices no longer line up")
        if len(self.balances) < 2:
            raise ValueError("a pool has at least two coins")

    @property
    def n_coins(self) -> int:
        return len(self.balances)

    @property
    def xp(self) -> tuple[int, ...]:
        """Balances normalised to 1e18. The invariant never sees anything else."""
        return tuple(
            rate * balance // PRECISION
            for rate, balance in zip(self.stored_rates, self.balances, strict=True)
        )


def invariant(xp: tuple[int, ...], amp: int) -> int:
    """`D`, by Newton's method, exactly as `get_D` computes it.

    `amp` is the pool's `A()` already multiplied by `A_PRECISION`, which is how
    the contract passes it -- keeping the scaling at the call site rather than
    here is the contract's choice and is preserved so the two stay comparable.
    """
    n_coins = len(xp)
    total = sum(xp)
    if total == 0:
        return 0

    d = total
    ann = amp * n_coins
    for _ in range(MAX_ITERATIONS):
        d_p = d
        for x in xp:
            d_p = d_p * d // x
        d_p //= _n_to_the_n(n_coins)
        previous = d
        d = (
            (ann * total // A_PRECISION + d_p * n_coins)
            * d
            // ((ann - A_PRECISION) * d // A_PRECISION + (n_coins + 1) * d_p)
        )
        if abs(d - previous) <= 1:
            return d
    raise DidNotConverge("get_D")


def _newton_y(b: int, c: int, d: int) -> int:
    """Newton on `y² + (b − D)·y − c = 0`, which is what `get_y` solves.

    The contract computes `2y + b - D` in `uint256`, so an underflow there
    reverts. There is no guard for it here because it cannot happen, and the
    argument is short enough to keep: `b` and `c` are sums of balances and so
    non-negative, the search starts at `y = D` where the denominator is
    `D + b > 0`, and every later iterate sits above the positive root, where
    `2y + b - D = 2(y - y*) + sqrt((D-b)² + 4c)` is positive too.

    A guard for that would be a branch nothing can reach, which is a branch no
    test can honestly cover -- and two hundred thousand randomly generated pools
    did not reach it either.
    """
    y = d
    for _ in range(MAX_ITERATIONS):
        previous = y
        y = (y * y + c) // (2 * y + b - d)
        if abs(y - previous) <= 1:
            return y
    raise DidNotConverge("newton_y")


def solve_for(i: int, j: int, x: int, xp: tuple[int, ...], amp: int, d: int) -> int:
    """`xp[j]` once `xp[i]` is set to `x`, holding `D` -- the contract's `get_y`."""
    n_coins = len(xp)
    if i == j:
        raise WrongFamily("a coin cannot be exchanged for itself")
    if not (0 <= i < n_coins and 0 <= j < n_coins):
        raise IndexError(f"coin index out of range for a {n_coins}-coin pool: {i}, {j}")

    total = 0
    c = d
    ann = amp * n_coins
    for index in range(n_coins):
        if index == j:
            continue
        value = x if index == i else xp[index]
        total += value
        c = c * d // (value * n_coins)
    c = c * d * A_PRECISION // (ann * n_coins)
    b = total + d * A_PRECISION // ann
    return _newton_y(b, c, d)


def dynamic_fee(xpi: int, xpj: int, fee: int, multiplier: int) -> int:
    """The fee, scaled by how far off peg the two coins sit.

    A multiplier at or below the denominator switches the scaling off and the
    base fee stands -- which is a configuration, not a special case, and the
    contract checks for it first.
    """
    if multiplier <= FEE_DENOMINATOR:
        return fee
    xps2 = (xpi + xpj) ** 2
    return (multiplier * fee) // (
        (multiplier - FEE_DENOMINATOR) * 4 * xpi * xpj // xps2 + FEE_DENOMINATOR
    )


def quote(state: StableSwapNGState, *, i: int, j: int, dx: int) -> int:
    """What a Stableswap-NG pool gives for `dx` of coin `i`, in coin `j`'s units.

    A port of `CurveStableSwapNGViews.get_dy`, in the contract's order. The fee
    is taken from the output, and it is evaluated at the *midpoint* of each
    coin's balance before and after -- not at either end, which would be a
    reasonable-looking choice and a different number.
    """
    xp = state.xp
    amp = state.amplification * A_PRECISION
    d = invariant(xp, amp)

    x = xp[i] + dx * state.stored_rates[i] // PRECISION
    y = solve_for(i, j, x, xp, amp, d)
    dy = xp[j] - y - 1

    fee = (
        dynamic_fee(
            (xp[i] + x) // 2,
            (xp[j] + y) // 2,
            state.fee,
            state.offpeg_fee_multiplier,
        )
        * dy
        // FEE_DENOMINATOR
    )
    return (dy - fee) * PRECISION // state.stored_rates[j]


# --- executable depth, by simulation (PRD section 18.9.1) ---------------------


@dataclass(frozen=True)
class DepthPoint:
    """What one notional actually costs.

    `effective_price` is exact: a `Fraction` of two integers the contract
    produced, not a float. Slippage of a few basis points on a stable pool is
    the whole signal, and it is the first thing binary floating point rounds
    away.
    """

    notional: int
    received: int
    effective_price: Fraction
    slippage_bps: Fraction


@dataclass(frozen=True)
class DepthTarget:
    """How much it takes to move the price by `bps`, or that it cannot be moved.

    `reached` is the field a caller must read first. When it is false the
    notional is the largest one searched and the slippage is what that bought --
    a liquidity fact, and a different one from "this is what N bps costs". The
    same distinction [[ADR-036]] draws for the concentrated-liquidity curve, for
    the same reason: a bare number conflates them.
    """

    bps: int
    reached: bool
    notional: int
    received: int
    slippage_bps: Fraction


def reference_price(state: StableSwapNGState, *, i: int, j: int, probe: int) -> Fraction:
    """The rate a vanishingly small trade would get, fees included.

    Slippage has to be measured against something, and the honest something is
    a quote from this same arithmetic at a size small enough not to move the
    pool. It is a parameter rather than a constant because "small" is a fact
    about the coin's decimals, which this module does not know -- a probe of
    1e18 is dust in an 18-decimal pool and a large trade in a 6-decimal one.
    """
    if probe <= 0:
        raise ValueError("a probe of nothing prices nothing")
    received = quote(state, i=i, j=j, dx=probe)
    if received <= 0:
        raise WrongFamily(f"a probe of {probe} bought nothing; too small for this pool's decimals")
    return Fraction(received, probe)


def depth_by_notional(
    state: StableSwapNGState,
    *,
    i: int,
    j: int,
    notionals: Sequence[int],
    probe: int,
) -> tuple[DepthPoint, ...]:
    """The depth curve, by quote simulation over a grid -- never from a tick map."""
    reference = reference_price(state, i=i, j=j, probe=probe)
    points = []
    for notional in notionals:
        if notional <= 0:
            raise ValueError(f"a notional of {notional} is not a trade")
        received = quote(state, i=i, j=j, dx=notional)
        effective = Fraction(received, notional)
        points.append(
            DepthPoint(
                notional=notional,
                received=received,
                effective_price=effective,
                slippage_bps=(1 - effective / reference) * BPS,
            )
        )
    return tuple(points)


def notional_for_bps(
    state: StableSwapNGState,
    *,
    i: int,
    j: int,
    bps: int,
    ceiling: int,
    probe: int,
) -> DepthTarget:
    """The inverse: how much it takes to move the price by `bps`.

    Bisection, because the only way to evaluate the forward direction is to run
    the pool's own Newton search and there is no closed form to invert. The
    curve is monotone in notional, which is what makes bisection valid and is
    a property of the invariant rather than an assumption about the data.

    `ceiling` has no default on purpose. The right bound is a fact about the
    pool's balances and the coin's decimals; a default would be a guess that
    silently reports "unreachable" for a pool it was too small for.
    """
    if bps <= 0:
        raise ValueError("a target of zero basis points is the current price")
    if ceiling <= 0:
        raise ValueError("a ceiling of nothing cannot be searched")

    reference = reference_price(state, i=i, j=j, probe=probe)

    def slippage(notional: int) -> tuple[int, Fraction]:
        received = quote(state, i=i, j=j, dx=notional)
        return received, (1 - Fraction(received, notional) / reference) * BPS

    received, at_ceiling = slippage(ceiling)
    if at_ceiling < bps:
        return DepthTarget(
            bps=bps,
            reached=False,
            notional=ceiling,
            received=received,
            slippage_bps=at_ceiling,
        )

    low, high = 1, ceiling
    while low < high:
        middle = (low + high) // 2
        if slippage(middle)[1] < bps:
            low = middle + 1
        else:
            high = middle
    received, reached_at = slippage(low)
    return DepthTarget(
        bps=bps, reached=True, notional=low, received=received, slippage_bps=reached_at
    )
