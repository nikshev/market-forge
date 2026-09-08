"""Rebuilding pool state from events (REQ-WP-015).

PRD section 18.7: "Do not reconstruct state by sorting only on timestamp.
Canonical event ordering is block_number, transaction_index, log_index."
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.dex import (
    Collect,
    DuplicateLog,
    NegativeLiquidity,
    compare_with_contract,
    rebuild,
)

from .conftest import burn, mint, pool, position, swap


@pytest.mark.trace("REQ-WP-015")
def test_events_are_applied_in_canonical_order_not_arrival_order() -> None:
    """SC-002, FR-005, ADR-035.

    Three swaps in one block, handed over backwards. Every log in a block
    shares its timestamp, so a timestamp sort would leave them in whatever
    order they arrived -- and the pool's final tick would be the first swap's
    rather than the last's.
    """
    state = pool()
    events = [
        swap(block=100, tx=0, log=2, price="1.03", tick=300, liquidity="3000"),
        swap(block=100, tx=0, log=0, price="1.01", tick=100, liquidity="1000"),
        swap(block=100, tx=0, log=1, price="1.02", tick=200, liquidity="2000"),
    ]

    result = rebuild(state, events)

    assert result.current_tick == 300, "log index 2 is last, whatever order they arrived"
    assert result.active_liquidity == Decimal("3000")


@pytest.mark.trace("REQ-WP-015")
def test_transaction_index_breaks_a_tie_within_a_block() -> None:
    """SC-002, FR-005. The middle key, which a block-then-log sort would miss."""
    state = pool()
    events = [
        swap(block=100, tx=5, log=0, price="1.05", tick=500, liquidity="5000"),
        swap(block=100, tx=1, log=9, price="1.01", tick=100, liquidity="1000"),
    ]

    result = rebuild(state, events)

    assert result.current_tick == 500, "transaction 5 is after transaction 1"


@pytest.mark.trace("REQ-WP-015")
def test_a_duplicate_log_is_refused() -> None:
    """FR-006, ADR-035, the spec's third edge case.

    That triple is unique on a chain, so a repeat is the same log ingested
    twice -- two providers, or a backfill overlapping live ingestion.
    Deduplicating silently would hide the bug and double a mint.
    """
    state = pool()
    events = [
        mint(block=100, tx=0, log=0, lower=-60, upper=60, amount="500"),
        mint(block=100, tx=0, log=0, lower=-60, upper=60, amount="500"),
    ]

    with pytest.raises(DuplicateLog, match="ingested twice"):
        rebuild(state, events)


@pytest.mark.trace("REQ-WP-015")
def test_a_mint_adds_at_the_lower_tick_and_subtracts_at_the_upper() -> None:
    """SC-003, FR-007.

    `liquidity_net` is what a traversal adds crossing upward, so the signs are
    what make the depth walk work at all.
    """
    result = rebuild(pool(), [mint(block=100, lower=-60, upper=60, amount="500")])

    assert result.tick_liquidity_net[-60] == Decimal("500")
    assert result.tick_liquidity_net[60] == Decimal("-500")


@pytest.mark.trace("REQ-WP-015")
def test_a_burn_reverses_a_mint_exactly() -> None:
    """SC-003, FR-007. A mint-then-burn pair leaves no trace."""
    state = pool()
    before = dict(state.tick_liquidity_net)

    result = rebuild(
        state,
        [
            mint(block=100, log=0, lower=-60, upper=60, amount="500"),
            burn(block=101, log=0, lower=-60, upper=60, amount="500"),
        ],
    )

    assert {t: n for t, n in result.tick_liquidity_net.items() if n != 0} == before
    assert result.active_liquidity == state.active_liquidity


@pytest.mark.trace("REQ-WP-015")
def test_a_range_spanning_the_current_tick_changes_active_liquidity() -> None:
    """SC-004, FR-008. The pool sits at tick 0."""
    result = rebuild(pool(), [mint(block=100, lower=-60, upper=60, amount="500")])

    assert result.active_liquidity == Decimal("1000500")


@pytest.mark.trace("REQ-WP-015")
def test_a_range_away_from_the_current_tick_does_not() -> None:
    """SC-004, FR-008. The distinction the whole concentrated-liquidity model
    rests on: liquidity out of range is not liquidity you can trade against."""
    result = rebuild(pool(), [mint(block=100, lower=600, upper=1200, amount="500")])

    assert result.active_liquidity == Decimal("1000000")
    assert result.tick_liquidity_net[600] == Decimal("500")


@pytest.mark.trace("REQ-WP-015")
def test_the_upper_tick_is_exclusive() -> None:
    """FR-008. A range `[lower, upper)` is active when the tick is inside it;
    a pool sitting exactly on the upper tick has moved past the range."""
    at_upper = pool(current_tick=60)

    result = rebuild(at_upper, [mint(block=100, lower=-60, upper=60, amount="500")])

    assert result.active_liquidity == Decimal("1000000")


@pytest.mark.trace("REQ-WP-015")
def test_a_burn_that_exceeds_the_liquidity_is_refused() -> None:
    """FR-009, the spec's second edge case.

    Negative liquidity is impossible on-chain, so seeing it means the event
    sequence is incomplete -- worth stopping for rather than clamping to zero
    and carrying on with a pool that no longer matches.
    """
    with pytest.raises(NegativeLiquidity, match="incomplete"):
        rebuild(pool(), [burn(block=100, lower=-60, upper=60, amount="500")])


@pytest.mark.trace("REQ-WP-015")
def test_collect_leaves_liquidity_untouched() -> None:
    """SC-005, FR-010, PRD section 18.7:

        "optional Collect for LP economics, not for liquidity state itself"

    Decoding it into the tick map would corrupt state it is not part of.
    """
    state = pool()
    before = dict(state.tick_liquidity_net)

    result = rebuild(
        state,
        [Collect(position=position(100), amount0=Decimal("9999"), amount1=Decimal("9999"))],
    )

    assert result.tick_liquidity_net == before
    assert result.active_liquidity == state.active_liquidity


@pytest.mark.trace("REQ-WP-015")
def test_rebuild_does_not_mutate_the_state_it_was_given() -> None:
    """A rebuild returns a new state, so a caller holding the previous one for
    comparison still has it -- which US5's integrity check depends on."""
    state = pool()

    rebuild(state, [mint(block=100, lower=-60, upper=60, amount="500")])

    assert state.tick_liquidity_net == {}
    assert state.active_liquidity == Decimal("1000000")


@pytest.mark.trace("REQ-WP-015")
def test_a_matching_contract_read_raises_no_incident() -> None:
    """SC-009, FR-015, PRD section 18.7.2."""
    state = pool()

    incident = compare_with_contract(
        state,
        current_tick=state.current_tick,
        sqrt_price_x96=state.sqrt_price_x96,
        active_liquidity=state.active_liquidity,
    )

    assert not incident.diverged


@pytest.mark.trace("REQ-WP-015")
def test_a_divergence_names_the_fields_and_leaves_the_state_alone() -> None:
    """SC-009, FR-015, PRD section 18.7.2: "never silently patch historical
    derived rows".

    The incident carries no corrected state, because a correction is a new
    observation rather than an edit -- the same rule ADR-033 applies to reorgs.
    """
    state = pool()

    incident = compare_with_contract(
        state,
        current_tick=999,
        sqrt_price_x96=state.sqrt_price_x96,
        active_liquidity=Decimal("42"),
    )

    assert incident.diverged
    assert set(incident.mismatches) == {"current_tick", "active_liquidity"}
    assert incident.mismatches["current_tick"] == ("0", "999")
    assert state.current_tick == 0, "the reconstruction is not patched"


@pytest.mark.trace("REQ-WP-015")
def test_the_dex_package_cannot_consult_a_clock_or_open_a_socket() -> None:
    """SC-010, FR-016."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "dex"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "time.monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
        for forbidden in ("import requests", "import httpx", "web3", "aiohttp"):
            assert forbidden not in source, f"{module.name} opens a socket: {forbidden!r}"
