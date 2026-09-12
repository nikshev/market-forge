"""Curve Cryptoswap: a cubic in closed form, and the pool says what it is.

# @trace: REQ-WP-046

PRD section 18.9 asks for the Cryptoswap families as shapes distinct from
Stableswap, and section 18.9.1 forbids a derived tick map for either. Where
`curve.py` ports Stableswap-NG, this ports **tricrypto-ng**, whose invariant
adds a `gamma` and a `price_scale` the pool rebalances around.

**The version was established rather than assumed.** The deployed pools report
`version() == "v2.0.0"` and `tricrypto-ng`'s published `main` declares the same
string. That check earned its keep immediately: the sibling `twocrypto-ng`
deployment reports `v3.0.0` while its repository's `main` says `v2.1.0`, so the
obvious source is the wrong contract -- which is why this module covers
tricrypto and `twocrypto` is classified but not quoted.

**What makes this port different from the others here is the arithmetic itself.**
`get_y` is not a Newton search but a closed-form solution of a cubic, carried out
in `int256` with:

* hand-rolled integer cube roots, seeded from a base-2 logarithm and refined by
  exactly seven unrolled Newton steps;
* a divider chosen from the magnitude of an intermediate, to keep the cubic's
  coefficients inside 256 bits;
* a Newton fallback for the case where the cubic's discriminant is not positive.

Two things about the EVM have to be reproduced rather than approximated:

* **`int256` division truncates toward zero; Python's `//` floors.** Several of
  the cubic's coefficients go negative, so the two disagree by one at every such
  step -- and a coefficient wrong by one, cubed and rescaled, is not a rounding
  difference in the answer.
* **Powers and products are unchecked in the source.** The contract's comments
  assert where overflow cannot happen; those assertions are load-bearing and the
  magnitudes here stay inside them, so Python's unbounded integers agree.

Verified against two independent views of the deployed pool: `get_dy` for the
whole quote, and the pool's own `MATH.get_y` for the cubic alone. A single
end-to-end comparison would say the chain of a dozen steps is wrong without
saying where.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isqrt

#: The 1e18 base the invariant works in.
PRECISION = 10**18

#: `A` is quoted pre-multiplied by this.
A_MULTIPLIER = 10_000

#: Curve's fee denominator, as in `curve.py`: 1e10, not 1e6.
FEE_DENOMINATOR = 10**10

N_COINS = 3

MIN_GAMMA = 10**10
MAX_GAMMA = 5 * 10**16
MIN_A = N_COINS**N_COINS * A_MULTIPLIER // 100
MAX_A = N_COINS**N_COINS * A_MULTIPLIER * 1000

#: `_cbrt`'s scaling thresholds, which are `2**256 // 1e36` and `2**256 // 1e18`
#: to the digit. They are what keeps the unchecked multiplication below from
#: overflowing, which is why they are written out rather than computed.
_CBRT_THRESHOLD = 115792089237316195423570985008687907853269

MAX_ITERATIONS = 255


class DidNotConverge(RuntimeError):
    """The Newton fallback ran out of iterations. The contract reverts here."""


class UnsafeValues(ValueError):
    """State outside the band the contract will quote in.

    Not a failure of this code. The contract asserts these bounds and reverts,
    so a quote outside them does not exist to be computed -- and returning one
    anyway would be a number with no counterpart on chain.
    """


class RampInProgress(ValueError):
    """`A` or `gamma` is mid-ramp, so the stored invariant is stale.

    The pool recomputes `D` from scratch while a ramp is running. This module
    does not implement that recomputation, and refuses rather than quoting from
    the stored `D` -- which would be a plausible number drifting further from
    the truth the longer the ramp had left to run.
    """


def _sdiv(numerator: int, denominator: int) -> int:
    """EVM `SDIV`: truncates toward zero, where Python's `//` floors.

    The difference is one, at every division of a negative value that does not
    divide evenly -- and the cubic's coefficients go negative routinely.
    """
    quotient = abs(numerator) // abs(denominator)
    return quotient if (numerator >= 0) == (denominator >= 0) else -quotient


def _log2(value: int) -> int:
    """Floor log base two, which is what the contract's Snekmate helper computes."""
    return value.bit_length() - 1 if value > 0 else 0


def cube_root(x: int) -> int:
    """The contract's `_cbrt`, scaling and seven unrolled Newton steps included.

    Returns `cbrt(x)` scaled by 1e12 -- equivalently `cbrt(x * 1e36)` -- across
    all three of its scaling branches, which exist only to keep the unchecked
    multiplication inside 256 bits.

    Not `round((x * 1e36) ** (1/3))`. The seed comes from a base-2 logarithm
    corrected by the ratio 1260/1000 for the remainder, and seven refinements
    follow, which leaves it a few parts in 1e15 from the true value. The quote is
    built from the contract's answer, so that is the number to reproduce.

    **The seed's correction is load-bearing and the iteration count is not.**
    The source's comment says six refinements would not converge and eight would
    be one too many; measured over two hundred thousand magnitudes, six and eight
    give results identical to seven, so the claim is not reproducible here and
    the count is kept at the contract's seven for fidelity rather than for
    effect. The `1260/1000` correction *is* observable -- there is an input in
    this module's fixture that needs it -- and dropping it moves the sixteenth
    significant digit, which survives a tolerance and fails an equality.
    """
    if x == 0:
        # The contract reaches zero here too, by way of an EVM division by zero
        # yielding zero rather than reverting. Written out, because Python
        # raises instead and the two must agree.
        return 0

    if x >= _CBRT_THRESHOLD * 10**18:
        scaled, unscale = x, 10**12
    elif x >= _CBRT_THRESHOLD:
        scaled, unscale = x * 10**18, 10**6
    else:
        scaled, unscale = x * 10**36, 1

    log2x = _log2(scaled)
    remainder = log2x % 3
    # `int(...)` around the powers, not decoration: Python's `**` is typed as
    # possibly returning a float, and letting that escape makes every integer
    # below it a float by inference -- the exact drift a bit-exact port cannot
    # afford.
    guess = (int(2 ** (log2x // 3)) * int(1260**remainder)) // int(1000**remainder)
    for _ in range(7):
        guess = (2 * guess + scaled // (guess * guess)) // 3
    return guess * unscale


def reduction_coefficient(xp: tuple[int, ...], fee_gamma: int) -> int:
    """How balanced the pool is, from 1e18 (perfectly) toward 0 (not at all).

    `fee_gamma / (fee_gamma + 1 - K)` where `K = prod(x) / (sum(x)/N)**N`. This
    is the whole of Cryptoswap's dynamic fee: the pool charges `mid_fee` when
    balanced and approaches `out_fee` as it is pushed off.
    """
    total = sum(xp)
    k = PRECISION * N_COINS * xp[0] // total
    k = k * N_COINS * xp[1] // total
    k = k * N_COINS * xp[2] // total
    if fee_gamma > 0:
        k = fee_gamma * PRECISION // (fee_gamma + PRECISION - k)
    return k


@dataclass(frozen=True)
class PoolState:
    """A tricrypto-ng pool as of one block.

    `price_scale` is state and not a price: it is the pool's internal scaling,
    which it rebalances toward the oracle over time. Quoting against a spot
    price instead would be a different and wrong number.
    """

    balances: tuple[int, int, int]
    precisions: tuple[int, int, int]
    price_scale: tuple[int, int]
    amplification: int
    gamma: int
    invariant: int
    mid_fee: int
    out_fee: int
    fee_gamma: int
    ramp_ends: int = 0

    def xp_at(self, *, now: int) -> tuple[int, int, int]:
        """Balances scaled the way the maths library sees them.

        Coin 0 is the numeraire and carries only its precision; the others carry
        their precision *and* the pool's price scale. Dropping either gives a
        positive, ordered, believable quote that is wrong by the missing factor.
        """
        if self.ramp_ends > now:
            raise RampInProgress(f"A/gamma ramp ends at {self.ramp_ends}, now {now}")
        return (
            self.balances[0] * self.precisions[0],
            self.balances[1] * self.price_scale[0] * self.precisions[1] // PRECISION,
            self.balances[2] * self.price_scale[1] * self.precisions[2] // PRECISION,
        )

    def fee(self, xp: tuple[int, ...]) -> int:
        coefficient = reduction_coefficient(xp, self.fee_gamma)
        return (self.mid_fee * coefficient + self.out_fee * (PRECISION - coefficient)) // PRECISION


def _check_band(ann: int, gamma: int, invariant: int, xp: tuple[int, ...], i: int) -> None:
    if not MIN_A - 1 < ann < MAX_A + 1:
        raise UnsafeValues(f"A out of band: {ann}")
    if not MIN_GAMMA - 1 < gamma < MAX_GAMMA + 1:
        raise UnsafeValues(f"gamma out of band: {gamma}")
    if not 10**17 - 1 < invariant < 10**15 * PRECISION + 1:
        raise UnsafeValues(f"D out of band: {invariant}")
    for k in range(N_COINS):
        if k == i:
            continue
        frac = xp[k] * PRECISION // invariant
        if not 10**16 - 1 < frac < 10**20 + 1:
            raise UnsafeValues(f"x[{k}] out of band relative to D: {frac}")


def _newton_y(ann: int, gamma: int, xp: tuple[int, ...], invariant: int, i: int) -> int:
    """The fallback the contract falls back to when the cubic has no real root
    it can use. Ported because the contract calls it, not because it is common."""
    _check_band(ann, gamma, invariant, xp, i)

    y = invariant // N_COINS
    k0_i = PRECISION
    s_i = 0

    without_i = list(xp)
    without_i[i] = 0
    descending = sorted(without_i, reverse=True)

    convergence_limit = max(descending[0] // 10**14, invariant // 10**14, 100)

    for j in range(2, N_COINS + 1):
        value = descending[N_COINS - j]
        y = y * invariant // (value * N_COINS)
        s_i += value
    for j in range(N_COINS - 1):
        k0_i = k0_i * descending[j] * N_COINS // invariant

    for _ in range(MAX_ITERATIONS):
        previous = y

        k0 = k0_i * y * N_COINS // invariant
        total = s_i + y

        g1k0 = gamma + PRECISION
        g1k0 = g1k0 - k0 + 1 if g1k0 > k0 else k0 - g1k0 + 1

        mul1 = PRECISION * invariant // gamma * g1k0 // gamma * g1k0 * A_MULTIPLIER // ann
        mul2 = PRECISION + (2 * PRECISION) * k0 // g1k0

        yfprime = PRECISION * y + total * mul2 + mul1
        dyfprime = invariant * mul2
        if yfprime < dyfprime:
            y = previous // 2
            continue
        yfprime -= dyfprime

        fprime = yfprime // y
        y_minus = mul1 // fprime
        y_plus = (yfprime + PRECISION * invariant) // fprime + y_minus * PRECISION // k0
        y_minus += PRECISION * total // fprime

        y = previous // 2 if y_plus < y_minus else y_plus - y_minus

        if abs(y - previous) < max(convergence_limit, y // 10**14):
            frac = y * PRECISION // invariant
            if not 10**16 - 1 < frac < 10**20 + 1:
                raise UnsafeValues(f"y out of band relative to D: {frac}")
            return y

    raise DidNotConverge("newton_y")


def _divider_for(magnitude: int) -> int:
    """The contract's ladder, which keeps the rescaled coefficients in 256 bits."""
    for threshold, divider in (
        (10**48, 10**30),
        (10**44, 10**26),
        (10**40, 10**22),
        (10**36, 10**18),
        (10**32, 10**14),
        (10**28, 10**10),
        (10**24, 10**6),
        (10**20, 10**2),
    ):
        if magnitude > threshold:
            return divider
    return 1


def solve_for(ann: int, gamma: int, xp: tuple[int, ...], invariant: int, i: int) -> tuple[int, int]:
    """`xp[i]` given the others and `D` -- the contract's `get_y`.

    Returns the coin balance and `K0`, both of which the pool uses. A port of
    the closed-form cubic in `CurveCryptoMathOptimized3`, with every division
    truncating toward zero as `SDIV` does.
    """
    _check_band(ann, gamma, invariant, xp, i)

    j, k = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[i]
    x_j, x_k = xp[j], xp[k]
    gamma2 = gamma * gamma

    a = 10**36 // 27
    b = (10**36 // 9 + 2 * PRECISION * gamma // 27) - (
        ((invariant * invariant // x_j) * gamma2 * ann // 27**2) // A_MULTIPLIER // x_k
    )
    c = (10**36 // 9 + gamma * (gamma + 4 * PRECISION) // 27) + (
        _sdiv(_sdiv(_sdiv(gamma2 * (x_j + x_k - invariant), invariant) * ann, 27), A_MULTIPLIER)
    )
    d = (PRECISION + gamma) ** 2 // 27

    d0 = abs(_sdiv(3 * a * c, b) - b)
    divider = _divider_for(d0)

    # Rescale so the cubic's coefficients stay inside 256 bits. The two branches
    # are not symmetric in the source -- one multiplies then divides, the other
    # divides twice -- and making them symmetric changes the answer.
    if abs(a) > abs(b):
        additional_precision = abs(_sdiv(a, b))
        a = _sdiv(a * additional_precision, divider)
        b = _sdiv(b * additional_precision, divider)
        c = _sdiv(c * additional_precision, divider)
        d = _sdiv(d * additional_precision, divider)
    else:
        additional_precision = abs(_sdiv(b, a))
        a = _sdiv(_sdiv(a, additional_precision), divider)
        b = _sdiv(_sdiv(b, additional_precision), divider)
        c = _sdiv(_sdiv(c, additional_precision), divider)
        d = _sdiv(_sdiv(d, additional_precision), divider)

    three_ac = 3 * a * c
    delta0 = _sdiv(three_ac, b) - b
    delta1 = _sdiv(3 * three_ac, b) - 2 * b - _sdiv(_sdiv(27 * a * a, b) * d, b)

    sqrt_arg = delta1**2 + _sdiv(4 * delta0**2, b) * delta0
    if sqrt_arg <= 0:
        # No usable real root. The contract falls back rather than refusing.
        return _newton_y(ann, gamma, xp, invariant, i), 0
    sqrt_val = isqrt(sqrt_arg)

    b_cbrt = cube_root(b) if b >= 0 else -cube_root(-b)
    if delta1 > 0:
        second_cbrt = cube_root((delta1 + sqrt_val) // 2)
    else:
        second_cbrt = -cube_root((sqrt_val - delta1) // 2)

    c1 = _sdiv(_sdiv(b_cbrt * b_cbrt, PRECISION) * second_cbrt, PRECISION)
    root_k0 = _sdiv(b + _sdiv(b * delta0, c1) - c1, 3)
    root = _sdiv(_sdiv(_sdiv(_sdiv(invariant * invariant, 27), x_k) * invariant, x_j) * root_k0, a)

    if root < 0 or root_k0 < 0:
        # `uint256` in the contract, so a negative here reverts on conversion.
        raise UnsafeValues(f"negative root: y={root}, K0={root_k0}")

    frac = root * PRECISION // invariant
    if not 10**16 - 1 < frac < 10**20 + 1:
        raise UnsafeValues(f"y out of band relative to D: {frac}")
    return root, _sdiv(PRECISION * root_k0, a)


def quote(state: PoolState, *, i: int, j: int, dx: int, now: int) -> int:
    """What the pool gives for `dx` of coin `i`, in coin `j`'s units.

    A port of `CurveCryptoViews3Optimized.get_dy`. The fee is evaluated on the
    balances **after** the trade, not before -- so a large trade pays a fee set
    by the imbalance it created, which is the point of a dynamic fee and is easy
    to get backwards.
    """
    if i == j:
        raise UnsafeValues("a coin cannot be exchanged for itself")
    if not (0 <= i < N_COINS and 0 <= j < N_COINS):
        raise IndexError(f"coin index out of range for a {N_COINS}-coin pool: {i}, {j}")
    if dx <= 0:
        raise UnsafeValues("do not exchange 0 coins")

    balances = list(state.balances)
    balances[i] += dx
    after = PoolState(
        balances=(balances[0], balances[1], balances[2]),
        precisions=state.precisions,
        price_scale=state.price_scale,
        amplification=state.amplification,
        gamma=state.gamma,
        invariant=state.invariant,
        mid_fee=state.mid_fee,
        out_fee=state.out_fee,
        fee_gamma=state.fee_gamma,
        ramp_ends=state.ramp_ends,
    )
    xp = list(after.xp_at(now=now))

    y, _ = solve_for(state.amplification, state.gamma, tuple(xp), state.invariant, j)
    dy = xp[j] - y - 1
    xp[j] = y

    if j > 0:
        dy = dy * PRECISION // state.price_scale[j - 1]
    dy //= state.precisions[j]

    return dy - after.fee(tuple(xp)) * dy // FEE_DENOMINATOR
