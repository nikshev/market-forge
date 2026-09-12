"""Curve tricrypto-ng, quoted from its own cubic (REQ-WP-046).

Two independent oracles, both the deployed contract's, both at one pinned block:
`get_dy` for the whole quote and the pool's own `MATH.get_y` for the closed-form
cubic at the centre of it. The quote is a chain of a dozen steps -- precisions,
price scales, a cubic with hand-rolled cube roots, then a fee interpolated by how
balanced the pool is -- and an end-to-end comparison alone would say the chain is
wrong without saying where.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex.cryptoswap import (
    _CBRT_THRESHOLD,
    A_MULTIPLIER,
    FEE_DENOMINATOR,
    MAX_A,
    MAX_GAMMA,
    MAX_ITERATIONS,
    MIN_A,
    PRECISION,
    DidNotConverge,
    PoolState,
    RampInProgress,
    UnsafeValues,
    _sdiv,
    cube_root,
    quote,
    reduction_coefficient,
    solve_for,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "curve" / "tricrypto_ng.jsonl"

#: Any timestamp past every pool's ramp. The fixture records `future_A_gamma_time`
#: and all three are in the past, so this is "no ramp is running".
AFTER_EVERY_RAMP = 10**12


def _pools() -> list[dict[str, Any]]:
    assert FIXTURE.is_file(), (
        f"missing fixture {FIXTURE}; regenerate with tools.record.cryptoswap_capture"
    )
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


POOLS = _pools()
IDS = [pool["name"] for pool in POOLS]


def _state(raw: dict[str, Any], **overrides: Any) -> PoolState:
    fields: dict[str, Any] = {
        "balances": tuple(int(value) for value in raw["balances"]),
        "precisions": tuple(int(value) for value in raw["precisions"]),
        "price_scale": tuple(int(value) for value in raw["price_scale"]),
        "amplification": int(raw["amplification"]),
        "gamma": int(raw["gamma"]),
        "invariant": int(raw["invariant"]),
        "mid_fee": raw["mid_fee"],
        "out_fee": raw["out_fee"],
        "fee_gamma": raw["fee_gamma"],
        "ramp_ends": raw["future_a_gamma_time"],
    }
    return PoolState(**{**fields, **overrides})


def _xp(raw: dict[str, Any]) -> tuple[int, int, int]:
    values = [int(value) for value in raw["xp"]]
    return (values[0], values[1], values[2])


# --- the first oracle: the whole quote ----------------------------------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_every_quote_is_the_pool_s_own_answer_exactly(raw: dict[str, Any]) -> None:
    state = _state(raw)
    recorded = [entry for entry in raw["quotes"] if "dy" in entry]
    assert recorded, f"{raw['name']} recorded no successful quotes"
    for entry in recorded:
        computed = quote(
            state, i=entry["i"], j=entry["j"], dx=int(entry["dx"]), now=AFTER_EVERY_RAMP
        )
        assert computed == int(entry["dy"]), (
            f"{raw['name']} {entry['i']}->{entry['j']} dx={entry['dx']}"
        )


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_every_ordered_index_pair_of_three_coins_is_covered(raw: dict[str, Any]) -> None:
    """§18.25 asks for multi-coin indices handled correctly, and three coins have
    six ordered pairs -- five more than a two-coin fixture can show."""
    pairs = {(entry["i"], entry["j"]) for entry in raw["quotes"]}
    assert len(pairs) == 6, f"{raw['name']}: {sorted(pairs)}"


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_quotes_span_orders_of_magnitude(raw: dict[str, Any]) -> None:
    sizes = sorted(int(entry["dx"]) for entry in raw["quotes"])
    assert sizes[-1] >= sizes[0] * 1000


# --- the second oracle: the cubic alone ---------------------------------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_cubic_alone_is_the_maths_library_s_own_answer(raw: dict[str, Any]) -> None:
    """A different contract from the one `get_dy` goes through, answering a
    question with no fee and no scaling around it.

    This is what localises a failure. Agreement here and disagreement above
    means the scaling or the fee; disagreement here means the cubic.
    """
    recorded = [entry for entry in raw["solved"] if "y" in entry]
    assert len(recorded) == 3, f"{raw['name']} solved only {len(recorded)} of 3"
    for entry in recorded:
        computed = solve_for(
            int(raw["amplification"]),
            int(raw["gamma"]),
            _xp(raw),
            int(raw["invariant"]),
            entry["i"],
        )
        assert computed == (int(entry["y"]), int(entry["k0"])), f"{raw['name']} i={entry['i']}"


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_two_oracles_are_different_contracts(raw: dict[str, Any]) -> None:
    """Otherwise they are one oracle recorded twice."""
    assert raw["math"].lower() != raw["pool"].lower()


# --- the scaling, which is where a silent factor goes missing -----------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_scaled_balances_are_the_pool_s_own(raw: dict[str, Any]) -> None:
    """Recorded from the chain rather than derived, so a wrong scaling is caught
    before the quote is even reached."""
    assert _state(raw).xp_at(now=AFTER_EVERY_RAMP) == _xp(raw)


@pytest.mark.trace("REQ-WP-046")
def test_the_fixture_holds_coins_of_several_decimals() -> None:
    """A precision dropped from a pool of 18-decimal coins changes nothing, so a
    fixture of only those could not show it was dropped."""
    scales = {tuple(pool["precisions"]) for pool in POOLS}
    assert any(len(set(precisions)) > 1 for precisions in scales), (
        f"every pool's coins share a precision: {scales}"
    )


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_price_scale_is_not_one_and_dropping_it_changes_the_quote(
    raw: dict[str, Any],
) -> None:
    """`price_scale` is the pool's internal scaling, not a spot price, and it is
    nowhere near 1e18 for a pool holding BTC against a dollar."""
    state = _state(raw)
    assert all(scale != PRECISION for scale in state.price_scale)
    flattened = _state(raw, price_scale=(PRECISION, PRECISION))
    assert flattened.xp_at(now=AFTER_EVERY_RAMP) != state.xp_at(now=AFTER_EVERY_RAMP)


# --- the dynamic fee ----------------------------------------------------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_fee_sits_between_the_two_configured_ends(raw: dict[str, Any]) -> None:
    state = _state(raw)
    charged = state.fee(state.xp_at(now=AFTER_EVERY_RAMP))
    assert state.mid_fee <= charged <= state.out_fee
    assert state.out_fee > state.mid_fee, "the fixture's pool has no fee range to interpolate"


@pytest.mark.trace("REQ-WP-046")
def test_a_balanced_pool_pays_the_mid_fee_and_a_lopsided_one_more() -> None:
    state = PoolState(
        balances=(1, 1, 1),
        precisions=(1, 1, 1),
        price_scale=(PRECISION, PRECISION),
        amplification=MIN_A,
        gamma=MAX_GAMMA,
        invariant=PRECISION,
        mid_fee=3_000_000,
        out_fee=30_000_000,
        fee_gamma=10**15,
    )
    balanced = state.fee((10**18, 10**18, 10**18))
    lopsided = state.fee((10**20, 10**18, 10**18))
    assert balanced == state.mid_fee
    assert lopsided > balanced
    assert lopsided < state.out_fee


@pytest.mark.trace("REQ-WP-046")
def test_fee_gamma_regulates_the_slope_and_zero_switches_it_off() -> None:
    """`fee_gamma` does not push the fee one way; it sets how fast imbalance
    moves it.

    A larger `fee_gamma` keeps the pool nearer `mid_fee` for the same imbalance,
    monotonically. Asserting a *direction* against the unsmoothed value instead
    would be wrong in both directions depending on the value chosen -- at 1e15
    the smoothed coefficient is below the raw one and at 1e16 it is above, which
    is how this test was wrong the first time.
    """
    balanced = (10**18, 10**18, 10**18)
    lopsided = (10**20, 10**18, 10**18)

    # A balanced pool is at the top of the range whatever the smoothing.
    assert reduction_coefficient(balanced, 0) == PRECISION
    assert reduction_coefficient(balanced, 10**15) == PRECISION

    # Zero means the branch is skipped entirely: the raw balance ratio stands.
    unsmoothed = reduction_coefficient(lopsided, 0)
    assert unsmoothed < PRECISION

    smoothed = [reduction_coefficient(lopsided, gamma) for gamma in (10**13, 10**15, 10**17)]
    assert smoothed == sorted(smoothed)
    assert smoothed[0] < unsmoothed < smoothed[-1]


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_fee_is_charged_on_the_balances_the_trade_leaves_behind(
    raw: dict[str, Any],
) -> None:
    """Not the ones it started from. A large trade pays a fee set by the
    imbalance it created, which is the point of a dynamic fee and reverses
    cleanly if the two are swapped."""
    state = _state(raw)
    before = state.xp_at(now=AFTER_EVERY_RAMP)
    biggest = max(
        (entry for entry in raw["quotes"] if "dy" in entry), key=lambda entry: int(entry["dx"])
    )
    i, j, dx = biggest["i"], biggest["j"], int(biggest["dx"])

    balances = list(state.balances)
    balances[i] += dx
    moved = _state(raw, balances=(balances[0], balances[1], balances[2]))
    xp = list(moved.xp_at(now=AFTER_EVERY_RAMP))
    xp[j] = solve_for(state.amplification, state.gamma, tuple(xp), state.invariant, j)[0]

    assert state.fee(tuple(xp)) != state.fee(before), (
        "the largest recorded trade moved the fee by nothing; the assertion cannot bite"
    )


# --- the arithmetic the EVM does and Python does not --------------------------


@pytest.mark.trace("REQ-WP-046")
def test_division_truncates_toward_zero_as_the_evm_does() -> None:
    """Python floors. The cubic's coefficients go negative, so the two disagree
    by one at every such step -- and a coefficient wrong by one, cubed and
    rescaled, is not a rounding difference in the answer."""
    assert _sdiv(-7, 2) == -3
    assert -7 // 2 == -4
    assert _sdiv(7, -2) == -3
    assert _sdiv(-7, -2) == 3
    assert _sdiv(7, 2) == 3


@pytest.mark.trace("REQ-WP-046")
def test_the_cube_root_is_the_contract_s_and_not_a_correctly_rounded_one() -> None:
    """Seven unrolled Newton steps from a log-2 seed, and the source's own
    comment says six do not converge. It is not `round(x ** (1/3))`, and the
    quote is built from the contract's answer rather than the true one."""
    # It returns cbrt(x) scaled by 1e12 -- equivalently cbrt(x * 1e36) -- and
    # that is true across all three of its scaling branches, which exist only to
    # keep the unchecked multiplication inside 256 bits.
    for value in (1, 8, 10**12, 10**42, _CBRT_THRESHOLD + 1, _CBRT_THRESHOLD * 10**18 + 1):
        root = cube_root(value)
        true_scaled = round((value * 10**36) ** (1 / 3))
        assert abs(root - true_scaled) <= max(1, true_scaled // 10**14)

    # And it is not that number. The seed and the seven steps leave it a few
    # parts in 1e15 away, and the quote is built from the contract's answer
    # rather than the true one.
    disagreements = [
        value
        for value in (10**12, 10**18, 10**42, _CBRT_THRESHOLD + 1)
        if cube_root(value) != round((value * 10**36) ** (1 / 3))
    ]
    assert disagreements, "the contract's cube root agreed with a float everywhere tried"


@pytest.mark.trace("REQ-WP-046")
def test_the_cube_root_of_nothing_is_nothing() -> None:
    """The contract reaches zero here by an EVM division by zero yielding zero;
    Python raises instead, so the case is written out."""
    assert cube_root(0) == 0


# --- what the contract refuses -----------------------------------------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amplification", 1),
        ("amplification", MAX_A + 1),
        ("gamma", 1),
        ("gamma", MAX_GAMMA + 1),
        ("invariant", 10**16),
    ],
)
def test_state_outside_the_contract_s_band_is_refused(field: str, value: int) -> None:
    """The contract asserts these and reverts, so a quote outside them does not
    exist to be computed. Returning one anyway would be a number with no
    counterpart on chain."""
    raw = POOLS[0]
    state = _state(raw, **{field: value})
    with pytest.raises(UnsafeValues):
        quote(state, i=0, j=1, dx=int(raw["balances"][0]) // 10**4, now=AFTER_EVERY_RAMP)


@pytest.mark.trace("REQ-WP-046")
def test_a_ramp_in_progress_refuses_rather_than_using_a_stale_invariant() -> None:
    """The pool recomputes `D` from scratch while `A` or `gamma` is ramping. This
    module does not, and says so: quoting from the stored `D` would drift further
    from the truth the longer the ramp had left to run."""
    raw = POOLS[0]
    state = _state(raw, ramp_ends=AFTER_EVERY_RAMP + 1)
    with pytest.raises(RampInProgress):
        quote(state, i=0, j=1, dx=10**6, now=AFTER_EVERY_RAMP)
    # And every pool in the fixture has its ramp behind it, or the quotes above
    # would be comparing against a `D` the pool no longer uses.
    assert all(pool["future_a_gamma_time"] < AFTER_EVERY_RAMP for pool in POOLS)


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize(("i", "j"), [(0, 3), (3, 0), (0, -1), (-1, 0)])
def test_an_index_outside_the_pool_is_refused(i: int, j: int) -> None:
    """Not wrapped. Python would read -1 as the last coin and quote a pair the
    caller did not ask about."""
    with pytest.raises(IndexError):
        quote(_state(POOLS[0]), i=i, j=j, dx=10**6, now=AFTER_EVERY_RAMP)


@pytest.mark.trace("REQ-WP-046")
def test_a_coin_cannot_be_exchanged_for_itself_and_nothing_is_not_a_trade() -> None:
    state = _state(POOLS[0])
    with pytest.raises(UnsafeValues, match="itself"):
        quote(state, i=1, j=1, dx=10**6, now=AFTER_EVERY_RAMP)
    with pytest.raises(UnsafeValues, match="0 coins"):
        quote(state, i=0, j=1, dx=0, now=AFTER_EVERY_RAMP)


@pytest.mark.trace("REQ-WP-046")
def test_the_newton_fallback_refuses_rather_than_approximating() -> None:
    """The contract raises "Did not converge"; it does not return its estimate."""
    assert MAX_ITERATIONS == 255
    with pytest.raises((DidNotConverge, UnsafeValues)):
        # Balances wildly outside any real pool's shape, so the search cannot
        # settle inside the contract's budget.
        solve_for(MIN_A, MAX_GAMMA, (10**18, 10**36, 10**18), 10**18, 0)


# --- provenance ---------------------------------------------------------------


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("raw", POOLS, ids=IDS)
def test_the_fixture_records_the_version_the_port_was_written_from(
    raw: dict[str, Any],
) -> None:
    """The sibling `twocrypto-ng` deployment reports a version its repository's
    `main` does not declare, so the obvious source there is the wrong contract.
    This asserts that the same trap was not walked into here."""
    assert raw["version"] == "v2.0.0"


@pytest.mark.trace("REQ-WP-046")
def test_the_fixture_is_pinned_to_one_block() -> None:
    """Balances from one block with an invariant from another describe no pool."""
    assert len({pool["block"] for pool in POOLS}) == 1


@pytest.mark.trace("REQ-WP-046")
def test_the_fee_denominator_is_curve_s_not_everyone_else_s() -> None:
    assert FEE_DENOMINATOR == 10**10
    assert A_MULTIPLIER == 10_000


# --- the third oracle: the maths library, asked about states no pool is in -----


MATH_FIXTURE = FIXTURE.with_name("tricrypto_math.jsonl")


def _library(kind: str) -> list[dict[str, Any]]:
    assert MATH_FIXTURE.is_file(), (
        f"missing fixture {MATH_FIXTURE}; regenerate with tools.record.cryptoswap_capture"
    )
    rows = [json.loads(line) for line in MATH_FIXTURE.read_text().splitlines()]
    return [row for row in rows if row["kind"] == kind]


CBRT_ROWS = _library("cbrt")
GET_Y_ROWS = _library("get_y")
REDUCTION_ROWS = _library("reduction_coefficient")


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("row", CBRT_ROWS, ids=[f"1e{len(row['x']) - 1}" for row in CBRT_ROWS])
def test_the_cube_root_is_the_deployed_library_s_to_the_wei(row: dict[str, Any]) -> None:
    """Seventeen inputs across all three of the library's scaling branches.

    This is what a fixture of live pool states cannot do. The pools only ever
    feed `cbrt` a narrow range, so a port with the wrong number of Newton steps
    or a seed missing its remainder correction agreed with the chain on every
    quote -- three mutants survived exactly there. The library takes its
    argument, not a pool's, so it can be asked directly.
    """
    assert cube_root(int(row["x"])) == int(row["root"])


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("row", REDUCTION_ROWS, ids=range(len(REDUCTION_ROWS)))
def test_the_fee_coefficient_is_the_deployed_library_s(row: dict[str, Any]) -> None:
    computed = reduction_coefficient(
        tuple(int(value) for value in row["xp"]), int(row["fee_gamma"])
    )
    assert computed == int(row["k"])


@pytest.mark.trace("REQ-WP-046")
@pytest.mark.parametrize("row", GET_Y_ROWS, ids=[row["name"] for row in GET_Y_ROWS])
def test_the_cubic_agrees_with_the_library_on_states_no_pool_is_in(
    row: dict[str, Any],
) -> None:
    """Including where the contract refuses, and where it falls back.

    Two branches of the closed form are unreachable from any live pool: a
    negative `b`, and a discriminant that is not positive and sends the contract
    to its Newton fallback. Both were found by searching the input space and then
    *asked of the chain* -- so "the contract reverts here" and "the contract
    returns this" are recorded facts rather than a reading of the source.
    """
    arguments = (
        int(row["A"]),
        int(row["gamma"]),
        tuple(int(value) for value in row["xp"]),
        int(row["D"]),
        row["i"],
    )
    if row.get("reverted"):
        with pytest.raises((UnsafeValues, DidNotConverge)):
            solve_for(*arguments)
    else:
        assert solve_for(*arguments)[0] == int(row["y"])


@pytest.mark.trace("REQ-WP-046")
def test_the_library_fixture_covers_both_a_refusal_and_the_fallback() -> None:
    """Otherwise the parametrised test above could be all of one kind."""
    assert any(row.get("reverted") for row in GET_Y_ROWS)
    assert any("y" in row for row in GET_Y_ROWS)
    named = {row["name"] for row in GET_Y_ROWS}
    assert {"b_negative", "negative_b_and_delta1", "sqrt_nonpositive"} <= named
    # Each band has a row that violates only it, so a missing check cannot hide
    # behind a different one firing first. The `x_far_from_D` row exists twice
    # over in spirit: the first attempt put the outlier at index `i`, which the
    # contract skips, and the call went through proving nothing.
    assert {
        "A_below_band",
        "A_above_band",
        "gamma_below_band",
        "gamma_above_band",
        "D_below_band",
        "D_above_band",
        "x_far_from_D",
    } <= named


@pytest.mark.trace("REQ-WP-046")
def test_the_library_fixture_is_the_same_block_and_the_same_contract() -> None:
    rows = [json.loads(line) for line in MATH_FIXTURE.read_text().splitlines()]
    assert len({row["block"] for row in rows}) == 1
    assert len({row["math"] for row in rows}) == 1
    assert {row["math"] for row in rows} == {pool["math"] for pool in POOLS}
