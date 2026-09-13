"""PRD §18.12.2's `reconstruction_quality` (REQ-WP-060).

The numbers here were measured from Ethereum mainnet and live in
`tests/fixtures/pool_state/uniswap_v3_events.jsonl`, recorded by
`tools.record.pool_state_capture` over blocks 25964304-25966304 of the deepest
USDC/WETH pool. Nothing here reaches the network.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex import (
    DEPTH_CAPABLE,
    Collect,
    DepthNotSupported,
    LiquidityChange,
    PoolEventKind,
    PoolState,
    Position,
    Provenance,
    Reconciliation,
    ReconstructionQuality,
    Swap,
    compare_with_contract,
    depth_curve,
    depth_to_bps,
    implied_active_liquidity,
    quality,
    rebuild,
    require_depth_capable,
    require_tick_map_complete,
    tick_map_accounts_for_liquidity,
)
from channelflow.dex.pool import NegativeLiquidity

from .conftest import pool

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "pool_state" / "uniswap_v3_events.jsonl"
)


def _rows() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
    return rows[0], rows[1], rows[2:]


HEADER, CONTRACT, EVENTS = _rows()


def _events(rows: list[dict[str, Any]]) -> list[Any]:
    built: list[Any] = []
    for row in rows:
        position = Position(row["block_number"], row["transaction_index"], row["log_index"])
        if row["kind"] == "Swap":
            built.append(
                Swap(
                    position,
                    Decimal(row["amount0"]),
                    Decimal(row["amount1"]),
                    int(row["sqrt_price_x96"]),
                    Decimal(row["liquidity"]),
                    row["tick"],
                )
            )
        elif row["kind"] in {"Mint", "Burn"}:
            built.append(
                LiquidityChange(
                    position,
                    row["tick_lower"],
                    row["tick_upper"],
                    Decimal(row["amount"]),
                    PoolEventKind.MINT if row["kind"] == "Mint" else PoolEventKind.BURN,
                )
            )
        else:
            built.append(Collect(position, Decimal(row["amount0"]), Decimal(row["amount1"])))
    return built


def _empty_state() -> PoolState:
    return PoolState(
        address=HEADER["pool"],
        token0=HEADER["token0"],
        token1=HEADER["token1"],
        fee_tier=HEADER["fee_tier"],
        tick_spacing=HEADER["tick_spacing"],
    )


def _replay(span: int) -> PoolState:
    floor = HEADER["to_block"] - span
    return rebuild(_empty_state(), _events([r for r in EVENTS if r["block_number"] >= floor]))


def _provenance(span: int, *, contiguous: bool = True) -> Provenance:
    return Provenance(
        from_block=HEADER["to_block"] - span, to_block=HEADER["to_block"], contiguous=contiguous
    )


# --------------------------------------------------------------------------
# The state that looks right
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-060")
def test_a_hundred_block_replay_matches_the_contract_on_every_scalar() -> None:
    """Which is what makes it dangerous rather than obviously broken."""
    state = _replay(100)

    assert str(int(state.active_liquidity)) == CONTRACT["liquidity"]
    assert state.current_tick == CONTRACT["tick"]
    # And the contract's own reading agreed with the last swap, so the fixture's
    # right-hand side is the chain's, not an assumption about it.
    assert HEADER["contract_agrees_with_last_swap"] is True


@pytest.mark.trace("REQ-WP-060")
def test_and_its_tick_map_explains_none_of_that_liquidity() -> None:
    state = _replay(100)

    assert state.initialized_ticks == []
    assert implied_active_liquidity(state) == 0
    assert state.active_liquidity == Decimal(CONTRACT["liquidity"])
    assert not tick_map_accounts_for_liquidity(state)
    # The size of the hole: the traversal would have run over nothing at all.
    assert implied_active_liquidity(state) / state.active_liquidity == 0


@pytest.mark.trace("REQ-WP-060")
def test_the_recovery_check_cannot_see_it() -> None:
    """§18.7.2 compares the three scalars a swap already reports.

    Two match exactly. The third differs by 1.4e-8 relative -- under a
    thousandth of a basis point of price, drift over the blocks between the last
    swap and the read -- which a reader would call noise, correctly. The empty
    tick map is invisible to it, because it never looks there.
    """
    state = _replay(100)

    incident = compare_with_contract(
        state,
        current_tick=CONTRACT["tick"],
        sqrt_price_x96=int(CONTRACT["sqrt_price_x96"]),
        active_liquidity=Decimal(CONTRACT["liquidity"]),
    )

    assert set(incident.mismatches) == {"sqrt_price_x96"}
    ours, theirs = incident.mismatches["sqrt_price_x96"]
    relative = abs(Decimal(ours) - Decimal(theirs)) / Decimal(theirs)
    # Under a thousandth of a basis point once squared into a price.
    assert relative < Decimal("1e-7"), "the only thing it reports is noise"


@pytest.mark.trace("REQ-WP-060")
def test_the_quality_does_see_it() -> None:
    state = _replay(100)

    assert quality(state, provenance=_provenance(100)) is ReconstructionQuality.PARTIAL_TICKS


@pytest.mark.trace("REQ-WP-060")
def test_a_curve_is_refused_rather_than_reported_as_a_thin_pool() -> None:
    """Before this refusal existed, `depth_curve` over that state returned eight
    bands, every one `reachable=False` with `reached_bps=0` and zero notional --
    for the deepest pool on the chain. [[REQ-WP-059]] draws that as "exhausted
    at 0 bps", which is a statement about the market."""
    state = _replay(100)

    with pytest.raises(DepthNotSupported, match="the map is incomplete"):
        depth_to_bps(state, bps=Decimal(50), upward=True)
    with pytest.raises(DepthNotSupported) as raised:
        depth_curve(state)

    # The refusal carries both sides of the comparison, so a reader can see how
    # much of the pool was missing rather than being told it was some.
    assert "0" in str(raised.value)
    assert CONTRACT["liquidity"] in str(raised.value)


@pytest.mark.trace("REQ-WP-060")
def test_whether_the_old_guard_catches_a_partial_replay_is_luck() -> None:
    """[[REQ-WP-015]]'s `NegativeLiquidity` fires when a burn happens to touch a
    range minted before the window, and not otherwise. Both behaviours are in
    this one fixture, which is why the quality cannot be left to it: an
    exception is also not a value a row can carry."""
    for span in (100, 200):
        _replay(span)  # builds, silently

    for span in (400, 800, 2000):
        with pytest.raises(NegativeLiquidity, match="sequence is incomplete"):
            _replay(span)


# --------------------------------------------------------------------------
# The five classes
# --------------------------------------------------------------------------


def _complete() -> PoolState:
    """A pool whose map accounts for its liquidity, as a real one's does."""
    state = pool()
    state.tick_liquidity_net = {-5000: Decimal("1000000"), 5000: Decimal("-1000000")}
    return state


def _reconciliation(*, aligned: bool, diverged: bool) -> Reconciliation:
    state = _complete()
    incident = compare_with_contract(
        state,
        current_tick=state.current_tick + (1 if diverged else 0),
        sqrt_price_x96=state.sqrt_price_x96,
        active_liquidity=state.active_liquidity,
    )
    return Reconciliation(incident=incident, read_at_block=100 if aligned else 101, state_block=100)


@pytest.mark.trace("REQ-WP-060")
def test_a_balanced_map_with_no_reconciliation_is_replayed() -> None:
    assert quality(_complete(), provenance=_provenance(100)) is ReconstructionQuality.REPLAYED


@pytest.mark.trace("REQ-WP-060")
def test_an_agreeing_reconciliation_at_the_states_own_block_anchors_it() -> None:
    verdict = quality(
        _complete(),
        provenance=_provenance(100),
        reconciliation=_reconciliation(aligned=True, diverged=False),
    )

    assert verdict is ReconstructionQuality.ANCHORED


@pytest.mark.trace("REQ-WP-060")
def test_a_reconciliation_at_another_block_is_not_evidence() -> None:
    """A contract read later than the state disagrees with a correct
    reconstruction whenever anything traded in between. Counting it either way
    is how a real check becomes noise."""
    agreeing = quality(
        _complete(),
        provenance=_provenance(100),
        reconciliation=_reconciliation(aligned=False, diverged=False),
    )
    disagreeing = quality(
        _complete(),
        provenance=_provenance(100),
        reconciliation=_reconciliation(aligned=False, diverged=True),
    )

    assert agreeing is ReconstructionQuality.REPLAYED
    assert disagreeing is ReconstructionQuality.REPLAYED


@pytest.mark.trace("REQ-WP-060")
def test_a_disagreement_at_the_states_own_block_is_a_divergence() -> None:
    verdict = quality(
        _complete(),
        provenance=_provenance(100),
        reconciliation=_reconciliation(aligned=True, diverged=True),
    )

    assert verdict is ReconstructionQuality.DIVERGED


@pytest.mark.trace("REQ-WP-060")
def test_a_gap_outranks_a_map_that_happens_to_balance() -> None:
    """Missing events are missing whatever the remaining ones add up to."""
    verdict = quality(_complete(), provenance=_provenance(100, contiguous=False))

    assert verdict is ReconstructionQuality.GAPPED


@pytest.mark.trace("REQ-WP-060")
def test_a_pool_with_no_liquidity_is_not_a_partial_reconstruction() -> None:
    """Nothing to explain, so nothing unexplained. The invariant holds at zero
    and a dead pool is honestly depth-capable: its depth is nothing."""
    dead = pool(active_liquidity=Decimal(0))

    assert tick_map_accounts_for_liquidity(dead)
    assert quality(dead, provenance=_provenance(100)) is ReconstructionQuality.REPLAYED
    assert depth_to_bps(dead, bps=Decimal(10), upward=True).reachable is False


@pytest.mark.trace("REQ-WP-060")
def test_a_range_backwards_is_refused() -> None:
    with pytest.raises(ValueError, match="runs backwards"):
        Provenance(from_block=200, to_block=100, contiguous=True)


# --------------------------------------------------------------------------
# §18.25 item 4
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-060")
def test_replaying_in_two_halves_reaches_the_same_state() -> None:
    """§18.25's checkpoint-to-replay equivalence, on the real event sequence.

    The 200-block slice is used because it is the longest this fixture replays
    without the negative-liquidity guard firing -- which is itself the point of
    the test above.
    """
    rows = [r for r in EVENTS if r["block_number"] >= HEADER["to_block"] - 200]
    midpoint = HEADER["to_block"] - 100

    whole = rebuild(_empty_state(), _events(rows))
    first = rebuild(_empty_state(), _events([r for r in rows if r["block_number"] < midpoint]))
    resumed = rebuild(first, _events([r for r in rows if r["block_number"] >= midpoint]))

    assert (resumed.current_tick, resumed.sqrt_price_x96) == (
        whole.current_tick,
        whole.sqrt_price_x96,
    )
    assert resumed.active_liquidity == whole.active_liquidity
    assert resumed.tick_liquidity_net == whole.tick_liquidity_net


# --------------------------------------------------------------------------
# What the sweep found nothing asserting
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-060")
def test_liquidity_minted_exactly_at_spot_counts() -> None:
    """A range `[lower, upper)` is active at `tick == lower`, so its
    `liquidity_net` at that tick is part of the liquidity at spot. Excluding the
    boundary makes every pool whose range opens exactly at the current tick look
    like a partial reconstruction -- and no other test has a tick there."""
    state = pool()
    state.tick_liquidity_net = {0: Decimal("1000000"), 5000: Decimal("-1000000")}

    assert state.current_tick == 0
    assert implied_active_liquidity(state) == Decimal("1000000")
    assert tick_map_accounts_for_liquidity(state)
    assert depth_to_bps(state, bps=Decimal(10), upward=True).reachable


@pytest.mark.trace("REQ-WP-060")
def test_a_gap_is_reported_even_when_the_map_is_also_partial() -> None:
    """The case that decides the order. A state that is both gapped and partial
    is labelled by its cause, not its symptom: the gap says events are missing,
    and the unbalanced map is what that looks like from the inside.

    A state that is gapped while its map balances cannot tell the two orders
    apart, which is why the earlier test could not."""
    partial = pool()
    partial.tick_liquidity_net = {}

    assert not tick_map_accounts_for_liquidity(partial)
    assert (
        quality(partial, provenance=_provenance(100, contiguous=False))
        is ReconstructionQuality.GAPPED
    )


@pytest.mark.trace("REQ-WP-060")
def test_the_two_guards_cover_different_ground() -> None:
    """A `PoolState` carries no provenance, so the traversal cannot see a gap.

    A gapped reconstruction whose surviving events happen to balance passes the
    traversal's own check and is refused by the quality gate. Without the second
    guard that state would have produced a curve -- the hole the sweep found,
    because nothing used `DEPTH_CAPABLE` at all.
    """
    balanced_but_gapped = _complete()
    verdict = quality(balanced_but_gapped, provenance=_provenance(100, contiguous=False))
    assert verdict is ReconstructionQuality.GAPPED

    # The traversal has no objection: what it can check is fine.
    require_tick_map_complete(balanced_but_gapped)
    assert depth_to_bps(balanced_but_gapped, bps=Decimal(10), upward=True).reachable

    # The gate that knows the provenance refuses.
    with pytest.raises(DepthNotSupported, match="gapped"):
        require_depth_capable(verdict)


@pytest.mark.trace("REQ-WP-060")
def test_only_anchored_and_replayed_may_be_traversed() -> None:
    for permitted in (ReconstructionQuality.ANCHORED, ReconstructionQuality.REPLAYED):
        require_depth_capable(permitted)

    for refused in (
        ReconstructionQuality.PARTIAL_TICKS,
        ReconstructionQuality.GAPPED,
        ReconstructionQuality.DIVERGED,
    ):
        with pytest.raises(DepthNotSupported, match=refused.value):
            require_depth_capable(refused)

    assert DEPTH_CAPABLE == {ReconstructionQuality.ANCHORED, ReconstructionQuality.REPLAYED}
