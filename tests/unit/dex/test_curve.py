"""Curve quotes from its own invariant (REQ-WP-046).

The fixtures are the deployed pools' own answers to the question this module
computes, read at one pinned block from independent RPC endpoints that agreed.
PRD §18.25 asks for the quote curve to match "contract view within tolerance";
integer arithmetic lets this assert equality instead.

The classification fixture is the same kind of thing one level up: what nine
live contracts answered when asked, including one that is not a Curve pool.
"""

from __future__ import annotations

import json
import random
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex.curve import (
    A_PRECISION,
    FEE_DENOMINATOR,
    Capabilities,
    DidNotConverge,
    PoolFamily,
    StableSwapNGState,
    WrongFamily,
    classify,
    depth_by_notional,
    dynamic_fee,
    invariant,
    notional_for_bps,
    quote,
    reference_price,
    solve_for,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "curve"


def _read(name: str) -> list[dict[str, Any]]:
    path = FIXTURES / f"{name}.jsonl"
    assert path.is_file(), f"missing fixture {path}; regenerate with tools.record.curve_capture"
    return [json.loads(line) for line in path.read_text().splitlines()]


POOLS = _read("stableswap_ng")
FAMILIES = _read("families")


def _state(raw: dict[str, Any]) -> StableSwapNGState:
    return StableSwapNGState(
        balances=tuple(int(balance) for balance in raw["balances"]),
        stored_rates=tuple(int(rate) for rate in raw["stored_rates"]),
        amplification=raw["amplification"],
        fee=raw["fee"],
        offpeg_fee_multiplier=raw["offpeg_fee_multiplier"],
    )


def _capabilities(raw: dict[str, Any]) -> Capabilities:
    return Capabilities(
        get_dy_int128=raw["get_dy_int128"],
        get_dy_uint256=raw["get_dy_uint256"],
        offpeg_fee_multiplier=raw["offpeg_fee_multiplier"],
        gamma=raw["gamma"],
        price_scale=raw["price_scale"],
        price_scale_indexed=raw["price_scale_indexed"],
        is_meta=raw["is_meta"],
    )


# --- the port is the contract -------------------------------------------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=[pool["name"] for pool in POOLS])
def test_every_quote_is_the_pool_s_own_answer_exactly(raw: dict[str, Any]) -> None:
    """Exact, not within tolerance. Every intermediate in `get_dy` is integer."""
    state = _state(raw)
    for recorded in raw["quotes"]:
        computed = quote(state, i=recorded["i"], j=recorded["j"], dx=int(recorded["dx"]))
        assert computed == int(recorded["dy"]), (
            f"{raw['name']} {recorded['i']}->{recorded['j']} dx={recorded['dx']}"
        )


@pytest.mark.trace("REQ-WP-046")
def test_a_three_coin_pool_is_quoted_across_every_index_pair() -> None:
    """§18.25 asks for multi-coin indices handled correctly, which a two-coin
    fixture cannot show: with two coins, `i` and `j` are the only pair and a
    module that ignored them both would still pass."""
    three = [pool for pool in POOLS if pool["n_coins"] > 2]
    assert three, "the fixture has no pool with more than two coins"
    pairs = {(quote["i"], quote["j"]) for quote in three[0]["quotes"]}
    assert len(pairs) == 6, f"expected every ordered pair of three coins, got {sorted(pairs)}"


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=[pool["name"] for pool in POOLS])
def test_the_quotes_span_orders_of_magnitude(raw: dict[str, Any]) -> None:
    """A port can be right at one size and wrong at another; that is what a
    curve's shape does to an error."""
    sizes = sorted(int(quote["dx"]) for quote in raw["quotes"])
    assert sizes[-1] >= sizes[0] * 1000


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=[pool["name"] for pool in POOLS])
def test_the_fixture_is_pinned_to_one_block(raw: dict[str, Any]) -> None:
    """Rates, balances and `A` from three different blocks describe no pool."""
    assert isinstance(raw["block"], int)
    assert len({pool["block"] for pool in POOLS}) == 1


# --- the three things a careless port gets plausibly wrong ---------------------


@pytest.mark.trace("REQ-WP-046")
def test_the_fee_denominator_is_not_a_million() -> None:
    """Curve's is 1e10. Every other venue in this project uses 1e6, and getting
    it wrong charges ten thousand times too little -- a number that stays
    positive, ordered and believable."""
    assert FEE_DENOMINATOR == 10**10
    # A pool's recorded fee read against the wrong denominator is nonsense:
    # 0.02% becomes 200%.
    plain = [pool for pool in POOLS if pool["fee"] > 0][0]
    assert Fraction(plain["fee"], 10**10) < Fraction(1, 100)
    assert Fraction(plain["fee"], 10**6) > 1


@pytest.mark.trace("REQ-WP-046")
def test_the_dynamic_fee_is_not_the_base_fee_on_a_real_pool() -> None:
    """So a fee read once and cached is wrong exactly where it matters most."""
    scaled = []
    for raw in POOLS:
        state = _state(raw)
        xp = state.xp
        for i in range(state.n_coins):
            for j in range(state.n_coins):
                if i != j:
                    effective = dynamic_fee(xp[i], xp[j], state.fee, state.offpeg_fee_multiplier)
                    if effective != state.fee:
                        scaled.append((raw["name"], i, j, state.fee, effective))
    assert scaled, "no pool in the fixture had an off-peg fee; recapture off peg"


@pytest.mark.trace("REQ-WP-046")
def test_a_multiplier_at_or_below_the_denominator_leaves_the_base_fee_alone() -> None:
    """A configuration, not a special case, and the contract checks it first."""
    assert dynamic_fee(100, 100, 3_000_000, FEE_DENOMINATOR) == 3_000_000
    assert dynamic_fee(100, 100, 3_000_000, 0) == 3_000_000
    assert dynamic_fee(100, 100, 3_000_000, FEE_DENOMINATOR + 1) == 3_000_000


@pytest.mark.trace("REQ-WP-046")
def test_the_further_off_peg_the_larger_the_fee() -> None:
    """The scaling's whole purpose, asserted as a direction rather than a value."""
    balanced = dynamic_fee(1_000_000, 1_000_000, 3_000_000, 5 * FEE_DENOMINATOR)
    lopsided = dynamic_fee(1_900_000, 100_000, 3_000_000, 5 * FEE_DENOMINATOR)
    assert lopsided > balanced


@pytest.mark.trace("REQ-WP-046")
def test_balances_are_not_xp() -> None:
    """Each coin's stored rate folds in its decimals and its accrual.

    Quoting on raw balances is the same class of error as reading a venue's
    contract sizes as base units -- and this fixture contains a pool where the
    rate is not 1e18, so the distinction is not hypothetical.
    """
    moved = [pool for pool in POOLS if any(int(rate) != 10**18 for rate in pool["stored_rates"])]
    assert moved, "no pool in the fixture carries a rate other than 1e18"
    state = _state(moved[0])
    assert state.xp != state.balances


@pytest.mark.trace("REQ-WP-046")
def test_a_rate_per_coin_or_the_indices_no_longer_line_up() -> None:
    with pytest.raises(ValueError, match="rate per coin"):
        StableSwapNGState(
            balances=(1, 2, 3),
            stored_rates=(10**18, 10**18),
            amplification=100,
            fee=0,
            offpeg_fee_multiplier=0,
        )


# --- the invariant itself -----------------------------------------------------


@pytest.mark.trace("REQ-WP-046")
def test_an_empty_pool_has_no_invariant() -> None:
    """Zero, and the contract returns it rather than dividing by nothing."""
    assert invariant((0, 0), 100 * A_PRECISION) == 0


@pytest.mark.trace("REQ-WP-046")
def test_the_invariant_is_the_sum_when_the_pool_is_balanced() -> None:
    """Stableswap's whole design: at the peg the curve is a straight line."""
    xp = (1_000 * 10**18, 1_000 * 10**18)
    assert invariant(xp, 1000 * A_PRECISION) == sum(xp)


@pytest.mark.trace("REQ-WP-046")
def test_the_invariant_falls_below_the_sum_off_peg() -> None:
    """And that gap is the slippage the whole depth curve is made of."""
    balanced = (1_000 * 10**18, 1_000 * 10**18)
    lopsided = (1_900 * 10**18, 100 * 10**18)
    amp = 1000 * A_PRECISION
    assert invariant(balanced, amp) == sum(balanced)
    assert invariant(lopsided, amp) < sum(lopsided)


#: Balances and an `A` for which `get_D` never lands on the same integer twice,
#: settling only because the contract accepts a difference of one. Found by
#: searching four hundred thousand random pools: every pool in the fixture
#: converges exactly, so nothing else in this file tells the contract's
#: tolerance apart from strict equality.
OSCILLATES = ((8_160_433_416_068_537, 785_897_992_899_963_386_435_412, 669_079_082), 492)


@pytest.mark.trace("REQ-WP-046")
def test_the_invariant_settles_within_one_and_not_only_on_equality() -> None:
    """The contract's tolerance is a rounding fact, not a loose comparison.

    Integer division lets the iteration land on two values one apart and
    alternate between them forever. Requiring exact equality would turn a pool
    that quotes perfectly well into one that refuses -- not a wrong number, but
    a wrong refusal, and the fixture cannot show the difference because every
    pool in it converges exactly.
    """
    xp, amp = OSCILLATES
    settled = invariant(xp, amp * A_PRECISION)
    assert settled > 0

    # It really does oscillate: one more step moves by exactly one.
    n_coins = len(xp)
    d_p = settled
    for x in xp:
        d_p = d_p * settled // x
    d_p //= n_coins**n_coins
    ann = amp * A_PRECISION * n_coins
    once_more = (
        (ann * sum(xp) // A_PRECISION + d_p * n_coins)
        * settled
        // ((ann - A_PRECISION) * settled // A_PRECISION + (n_coins + 1) * d_p)
    )
    assert abs(once_more - settled) == 1


#: Three balances and an `A` for which `get_D` cannot settle inside the
#: contract's 255-round budget. The contract's own comment calls this state
#: "borked" and says convergence normally takes four rounds; found by searching
#: two hundred thousand random pools, because no assumed input reached it and
#: guessing at one produced a test that passed for the wrong reason.
BORKED = (
    (41_771_082_961_215_391_131_887_672, 1_092_923_427_116_723, 782_332_127_414_021_201_918_775),
    75_753,
)


@pytest.mark.trace("REQ-WP-046")
def test_an_invariant_that_cannot_settle_refuses_rather_than_approximating() -> None:
    """The contract raises here and lets LPs withdraw; it does not quote.

    Returning the last estimate would hand back a number that looks like an
    invariant, and every depth figure built on it would be wrong by an amount
    nobody can reconstruct.
    """
    xp, amp = BORKED
    with pytest.raises(DidNotConverge):
        invariant(xp, amp * A_PRECISION)


@pytest.mark.trace("REQ-WP-046")
def test_the_coin_solve_never_divides_by_zero_however_lopsided_the_pool() -> None:
    """Which is why it carries no underflow guard.

    The contract's `2y + b - D` is `uint256` and would revert on an underflow.
    It cannot underflow: the search starts at `y = D`, where the denominator is
    `D + b > 0`, and every later iterate sits above the positive root. A guard
    would be a branch nothing can reach, and a test for such a branch can only
    pass by lying.

    So the claim is tested as the property it is, over two thousand pools
    spanning thirty orders of magnitude in balance and five in `A`. The only
    permitted outcome besides an answer is a refusal to converge.
    """
    generator = random.Random(20260911)
    refused = 0
    for _ in range(2_000):
        n_coins = generator.choice([2, 2, 3, 4])
        xp = tuple(generator.randrange(1, 10 ** generator.randrange(1, 30)) for _ in range(n_coins))
        amp = generator.randrange(1, 100_000) * A_PRECISION
        try:
            d = invariant(xp, amp)
        except DidNotConverge:
            refused += 1
            continue
        if d == 0:
            continue
        try:
            y = solve_for(0, 1, xp[0] + generator.randrange(1, 10**30), xp, amp, d)
        except DidNotConverge:
            refused += 1
            continue
        # Zero is a legitimate answer, not a failure: a trade astronomically
        # larger than the pool drains it, and the contract says so the same way.
        assert y >= 0
    assert refused > 0, "no pool was extreme enough to refuse; widen the sweep"


@pytest.mark.trace("REQ-WP-046")
def test_a_coin_cannot_be_exchanged_for_itself() -> None:
    state = _state(POOLS[0])
    with pytest.raises(WrongFamily):
        quote(state, i=0, j=0, dx=10**6)


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize(("i", "j"), [(0, 7), (7, 0), (0, -1), (-1, 0), (-2, 1)])
def test_an_index_outside_the_pool_is_refused(i: int, j: int) -> None:
    """Not clamped, and not wrapped.

    An index past the end would raise on its own; a *negative* one would not.
    Python would read -1 as the last coin and quote it happily, which on a
    three-coin pool is a real quote for a pair the caller did not ask about --
    positive, ordered, believable. The bounds check exists for that half.
    """
    state = _state(next(pool for pool in POOLS if pool["n_coins"] > 2))
    with pytest.raises(IndexError):
        quote(state, i=i, j=j, dx=10**6)


# --- depth by simulation, never from a tick map -------------------------------


@pytest.mark.trace("REQ-WP-046")
def test_depth_deepens_monotonically_with_size() -> None:
    raw = POOLS[0]
    state = _state(raw)
    probe = 10**6
    grid = [probe * 10**k for k in (3, 4, 5, 6, 7)]
    points = depth_by_notional(state, i=0, j=1, notionals=grid, probe=probe)
    assert [point.notional for point in points] == grid
    slippage = [point.slippage_bps for point in points]
    assert slippage == sorted(slippage)
    assert slippage[-1] > slippage[0]


@pytest.mark.trace("REQ-WP-046")
def test_the_depth_curve_is_exact_arithmetic_not_floating_point() -> None:
    """Slippage of a few basis points on a stable pool is the entire signal, and
    it is the first thing binary floating point rounds away."""
    raw = POOLS[0]
    state = _state(raw)
    point = depth_by_notional(state, i=0, j=1, notionals=[10**10], probe=10**6)[0]
    assert isinstance(point.slippage_bps, Fraction)
    assert isinstance(point.effective_price, Fraction)


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("bps", [5, 10, 25, 50, 100])
def test_the_inverse_solve_lands_on_the_target(bps: int) -> None:
    """§18.9.1's other direction: the notional that moves price by N bps."""
    raw = POOLS[0]
    state = _state(raw)
    target = notional_for_bps(
        state, i=0, j=1, bps=bps, ceiling=int(raw["balances"][0]), probe=10**6
    )
    assert target.reached
    assert target.slippage_bps >= bps
    # The reported numbers describe the reported notional, and not some other
    # one: a search that answered with the notional it found and the slippage
    # it measured at the search bound would still satisfy the line above.
    assert target.received == quote(state, i=0, j=1, dx=target.notional)
    reference_at = reference_price(state, i=0, j=1, probe=10**6)
    assert (
        target.slippage_bps
        == (1 - Fraction(target.received, target.notional) / reference_at) * 10_000
    )
    # And it is the *smallest* such notional: one step less does not reach it.
    smaller = quote(state, i=0, j=1, dx=target.notional - 1)
    reference = reference_price(state, i=0, j=1, probe=10**6)
    assert (1 - Fraction(smaller, target.notional - 1) / reference) * 10_000 < bps


@pytest.mark.trace("REQ-WP-046")
def test_an_unreachable_target_says_so_rather_than_returning_the_largest_tried() -> None:
    """ADR-036's distinction, for the invariant curve: a notional that exhausted
    the search is a different fact from a notional that reached the target."""
    raw = POOLS[0]
    state = _state(raw)
    target = notional_for_bps(state, i=0, j=1, bps=5, ceiling=10**7, probe=10**6)
    assert not target.reached
    assert target.notional == 10**7
    assert target.slippage_bps < 5


@pytest.mark.trace("REQ-WP-046")
def test_a_search_needs_a_ceiling_and_a_probe_the_caller_chose() -> None:
    """Neither has a default: the right bound is a fact about the pool's
    balances and the coin's decimals, and a default would be a guess that
    silently reports "unreachable" for a pool it was too small for."""
    state = _state(POOLS[0])
    with pytest.raises(ValueError, match="ceiling"):
        notional_for_bps(state, i=0, j=1, bps=10, ceiling=0, probe=10**6)
    with pytest.raises(ValueError, match="basis points"):
        notional_for_bps(state, i=0, j=1, bps=0, ceiling=10**12, probe=10**6)
    # Not merely "some ValueError": a probe of nothing would otherwise fall
    # through to the "bought nothing" branch, whose message also mentions the
    # probe, and a *negative* probe would fall through to a negative price with
    # no error at all.
    with pytest.raises(ValueError, match="prices nothing"):
        reference_price(state, i=0, j=1, probe=0)
    with pytest.raises(ValueError, match="prices nothing"):
        reference_price(state, i=0, j=1, probe=-(10**6))


@pytest.mark.trace("REQ-WP-046")
def test_a_notional_of_nothing_is_not_a_trade() -> None:
    state = _state(POOLS[0])
    with pytest.raises(ValueError, match="not a trade"):
        depth_by_notional(state, i=0, j=1, notionals=[0], probe=10**6)


# --- what a pool is -----------------------------------------------------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize(
    ("name", "family"),
    [
        ("stableswap-3pool", PoolFamily.STABLESWAP),
        ("stableswap-steth", PoolFamily.STABLESWAP),
        ("metapool-usd", PoolFamily.META_POOL),
        ("stableswap-ng-plain", PoolFamily.STABLESWAP_NG),
        ("stableswap-ng-three", PoolFamily.STABLESWAP_NG),
        ("cryptoswap-factory", PoolFamily.CRYPTOSWAP),
        ("cryptoswap-twocrypto", PoolFamily.CRYPTOSWAP),
        ("cryptoswap-tricrypto", PoolFamily.CRYPTOSWAP),
        ("not-a-pool-weth", PoolFamily.UNKNOWN),
    ],
)
def test_every_shape_is_classified_from_a_live_instance(name: str, family: PoolFamily) -> None:
    """§18.25 asks for implementation classification tested. Against real
    contracts: a constructed capability set only tests the test."""
    raw = next(entry for entry in FAMILIES if entry["name"] == name)
    assert classify(_capabilities(raw)) is family


@pytest.mark.trace("REQ-WP-046")
def test_the_two_families_do_not_share_a_signature_on_any_live_pool() -> None:
    """Which is why a caller that assumes the wrong one gets a revert -- loud.
    It is assuming the wrong *invariant* that is quiet, and that is what the
    classification exists to prevent."""
    for raw in FAMILIES:
        assert not (raw["get_dy_int128"] and raw["get_dy_uint256"]), raw["name"]


@pytest.mark.trace("REQ-WP-046")
def test_a_contract_the_registry_does_not_know_is_not_a_pool_that_is_not_a_metapool() -> None:
    """`None` is a third state and must survive. Flattening it to False reads as
    "a Curve pool that happens not to be a metapool", which WETH is not."""
    weth = next(entry for entry in FAMILIES if entry["name"] == "not-a-pool-weth")
    assert weth["is_meta"] is None
    assert classify(Capabilities(is_meta=None)) is PoolFamily.UNKNOWN
    assert classify(Capabilities(is_meta=False)) is PoolFamily.UNKNOWN


@pytest.mark.trace("REQ-WP-046")
def test_a_contract_that_swallows_every_selector_answers_none_of_them() -> None:
    """WETH's payable fallback accepts any calldata and returns nothing, so a
    probe that only caught reverts would report it implements all of Curve."""
    weth = next(entry for entry in FAMILIES if entry["name"] == "not-a-pool-weth")
    probes = [key for key, value in weth.items() if isinstance(value, bool)]
    assert probes, "the fixture recorded no capability probes"
    assert not any(weth[key] for key in probes)


@pytest.mark.trace("REQ-WP-046")
def test_cryptoswap_needs_both_its_marks_not_either() -> None:
    """No live pool separates them, so this is asserted on constructed sets.

    A pool that answered `gamma()` but took `int128` indices is not a shape
    Curve ships; treating either mark alone as sufficient would classify a
    plain Stableswap as a Cryptoswap the first time Curve added a `gamma()` to
    one, and price it with an invariant it does not have.
    """
    assert classify(Capabilities(get_dy_uint256=True, gamma=True)) is PoolFamily.CRYPTOSWAP
    assert classify(Capabilities(get_dy_uint256=True)) is PoolFamily.UNKNOWN
    assert classify(Capabilities(gamma=True, get_dy_int128=True)) is PoolFamily.STABLESWAP


@pytest.mark.trace("REQ-WP-046")
def test_a_metapool_is_a_metapool_whatever_curve_it_runs() -> None:
    """The registry's answer is read before the pool's own, so a Stableswap-NG
    metapool does not classify as a plain Stableswap-NG."""
    ng_metapool = Capabilities(get_dy_int128=True, offpeg_fee_multiplier=True, is_meta=True)
    assert classify(ng_metapool) is PoolFamily.META_POOL


@pytest.mark.trace("REQ-WP-046")
def test_the_discriminators_that_did_not_survive_measurement_are_not_used() -> None:
    """`base_pool()` identifies no metapool and `get_dy_underlying` identifies
    every Stableswap, so neither is in `Capabilities` at all. Asserted, because
    the natural instinct is to add them back."""
    fields = set(Capabilities.__dataclass_fields__)
    assert "base_pool" not in fields
    assert "get_dy_underlying" not in fields


@pytest.mark.trace("REQ-WP-046")
def test_the_classification_fixture_is_one_block() -> None:
    assert len({entry["block"] for entry in FAMILIES}) == 1
