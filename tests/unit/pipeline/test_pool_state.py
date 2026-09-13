"""PRD §18.7's reconstruction over stored rows (REQ-WP-062).

The rows are built from `tests/fixtures/pool_state/uniswap_v3_events.jsonl` --
real logs of Ethereum's deepest USDC/WETH pool, recorded by
`tools.record.pool_state_capture`. Nothing here reaches the network.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex import PoolState, Provenance, ReconstructionQuality, rebuild
from channelflow.pipeline.pool_state import (
    ContradictoryRow,
    Materialized,
    NotAnchored,
    NothingToReplay,
    PoolIdentity,
    events_for,
    liquidity_event,
    materialize,
)
from channelflow.tables import dex_liquidity, dex_swaps

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "pool_state" / "uniswap_v3_events.jsonl"
)
_LINES = FIXTURE.read_text().splitlines()
HEADER: dict[str, Any] = json.loads(_LINES[0])
CONTRACT: dict[str, Any] = json.loads(_LINES[1])
LOGS: list[dict[str, Any]] = [json.loads(line) for line in _LINES[2:]]

STATE_TIME_NS = 1_700_000_000_000_000_000

IDENTITY = PoolIdentity(
    chain_id=HEADER["chain_id"],
    pool=HEADER["pool"],
    venue="uniswap",
    protocol="uniswap_v3",
    token0=HEADER["token0"],
    token1=HEADER["token1"],
    fee_tier=HEADER["fee_tier"],
    tick_spacing=HEADER["tick_spacing"],
)


def _base(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "block_number": log["block_number"],
        "transaction_index": log["transaction_index"],
        "log_index": log["log_index"],
    }


def _swap_row(log: dict[str, Any]) -> dict[str, Any]:
    return _base(log) | {
        "amount0": Decimal(log["amount0"]),
        "amount1": Decimal(log["amount1"]),
        "sqrt_price_x96": log["sqrt_price_x96"],
        "liquidity": log["liquidity"],
        "tick": log["tick"],
    }


def _liquidity_row(log: dict[str, Any]) -> dict[str, Any]:
    sign = 1 if log["kind"] == "Mint" else -1
    return _base(log) | {
        "event_type": log["kind"].lower(),
        "tick_lower": log.get("tick_lower"),
        "tick_upper": log.get("tick_upper"),
        "liquidity_delta": str(sign * int(log["amount"])) if "amount" in log else "0",
        "amount0": Decimal(log.get("amount0", "0")),
        "amount1": Decimal(log.get("amount1", "0")),
    }


def _rows(span: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    floor = HEADER["to_block"] - span
    inside = [log for log in LOGS if log["block_number"] >= floor]
    swaps = [_swap_row(log) for log in inside if log["kind"] == "Swap"]
    liquidity = [
        _liquidity_row(log) for log in inside if log["kind"] in {"Mint", "Burn", "Collect"}
    ]
    return swaps, liquidity


def _provenance(span: int, *, contiguous: bool = True) -> Provenance:
    return Provenance(
        from_block=HEADER["to_block"] - span, to_block=HEADER["to_block"], contiguous=contiguous
    )


def _materialize(span: int = 100, **overrides: Any) -> Materialized:
    swaps, liquidity = _rows(span)
    arguments: dict[str, Any] = {
        "identity": IDENTITY,
        "swaps": swaps,
        "liquidity": liquidity,
        "provenance": _provenance(span),
        "state_time_ns": STATE_TIME_NS,
    }
    arguments.update(overrides)
    return materialize(**arguments)


# --------------------------------------------------------------------------
# The plane's rows become a state
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-062")
def test_stored_rows_rebuild_the_pool_the_contract_reports() -> None:
    built = _materialize()

    assert str(int(built.state.active_liquidity)) == CONTRACT["liquidity"]
    assert built.state.current_tick == CONTRACT["tick"]
    assert built.reference_price > 0


@pytest.mark.trace("REQ-WP-062")
def test_the_row_records_the_quality_the_state_earned() -> None:
    """A recent window cannot have a complete tick map, and the honest row says
    so. Skipping it would leave the table as empty as it was."""
    built = _materialize()

    assert built.quality is ReconstructionQuality.PARTIAL_TICKS
    assert built.row["reconstruction_quality"] == "partial_ticks"
    assert built.row["implied_active_liquidity"] == "0"
    assert built.row["active_liquidity"] == CONTRACT["liquidity"]
    assert built.row["from_block"] == HEADER["to_block"] - 100


@pytest.mark.trace("REQ-WP-062")
def test_the_same_rows_twice_give_the_same_row() -> None:
    assert _materialize().row == _materialize().row


@pytest.mark.trace("REQ-WP-062")
def test_arrival_order_does_not_change_the_answer() -> None:
    """§18.7's order is applied by `rebuild`, so a caller who hands over rows as
    they arrived gets what one who sorted first gets."""
    swaps, liquidity = _rows(100)
    shuffled = materialize(
        identity=IDENTITY,
        swaps=list(reversed(swaps)),
        liquidity=list(reversed(liquidity)),
        provenance=_provenance(100),
        state_time_ns=STATE_TIME_NS,
    )

    assert shuffled.row == _materialize().row


@pytest.mark.trace("REQ-WP-062")
def test_the_transaction_index_decides_before_the_log_index() -> None:
    """Synthetic, because the chain never produces it: EVM log indices are
    block-scoped and rise with transaction index, measured over 803 blocks. The
    rule §18.7 states is still the rule, and only a case the chain cannot
    produce can tell the two orderings apart."""
    early_tx_late_log = {
        "block_number": 100,
        "transaction_index": 2,
        "log_index": 9,
        "amount0": Decimal(-1),
        "amount1": Decimal(1),
        "sqrt_price_x96": "79228162514264337593543950336",
        "liquidity": "1000",
        "tick": 0,
    }
    late_tx_early_log = {
        **early_tx_late_log,
        "transaction_index": 5,
        "log_index": 1,
        "liquidity": "2000",
        "tick": 7,
    }

    events = events_for(swaps=[late_tx_early_log, early_tx_late_log], liquidity=[])
    ordered = sorted(events, key=lambda event: event.position.key)

    # Canonical order puts transaction 2 first even though its log index is
    # higher; a sort on log index alone would reverse them.
    assert [event.position.transaction_index for event in ordered] == [2, 5]
    assert [event.position.log_index for event in ordered] == [9, 1]


# --------------------------------------------------------------------------
# Rows that cannot be believed
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-062")
def test_a_row_that_contradicts_itself_is_refused() -> None:
    """The type and the sign state the same fact. The tick map is built from the
    sign, so resolving the disagreement either way produces a plausible map that
    is not the pool's."""
    for event_type, delta in (("burn", "500"), ("mint", "-500")):
        row = {
            "block_number": 1,
            "transaction_index": 0,
            "log_index": 0,
            "event_type": event_type,
            "tick_lower": -60,
            "tick_upper": 60,
            "liquidity_delta": delta,
            "amount0": Decimal(0),
            "amount1": Decimal(0),
        }
        with pytest.raises(ContradictoryRow, match="disagree"):
            liquidity_event(row)


@pytest.mark.trace("REQ-WP-062")
def test_a_modify_row_is_applied_by_its_sign() -> None:
    """§18.8's v4 `ModifyLiquidity` has no counterpart in `PoolEventKind`, and
    its effect on the tick map is exactly its signed delta."""
    row = {
        "block_number": 1,
        "transaction_index": 0,
        "log_index": 0,
        "event_type": "modify",
        "tick_lower": -60,
        "tick_upper": 60,
        "liquidity_delta": "-500",
        "amount0": Decimal(0),
        "amount1": Decimal(0),
    }

    event = liquidity_event(row)

    assert event.signed_amount == Decimal(-500)  # type: ignore[union-attr]


@pytest.mark.trace("REQ-WP-062")
def test_a_collect_moves_no_liquidity_and_keeps_its_place() -> None:
    row = {
        "block_number": 1,
        "transaction_index": 0,
        "log_index": 3,
        "event_type": "collect",
        "tick_lower": -60,
        "tick_upper": 60,
        "liquidity_delta": "0",
        "amount0": Decimal("1.5"),
        "amount1": Decimal("2.5"),
    }

    event = liquidity_event(row)

    assert not hasattr(event, "signed_amount")
    assert event.position.log_index == 3


@pytest.mark.trace("REQ-WP-062")
def test_a_range_with_no_rows_writes_nothing_and_says_so() -> None:
    with pytest.raises(NothingToReplay, match="claim about the pool"):
        materialize(
            identity=IDENTITY,
            swaps=[],
            liquidity=[],
            provenance=_provenance(100),
            state_time_ns=STATE_TIME_NS,
        )


@pytest.mark.trace("REQ-WP-062")
def test_a_replay_with_no_swap_has_no_price_and_is_refused() -> None:
    """A swap is what anchors a reconstruction to the chain. Without one the
    price stays zero, which reads as a price rather than as an absence."""
    _, liquidity = _rows(2000)
    assert liquidity, "the fixture has liquidity events"

    with pytest.raises(NotAnchored, match="none was a swap"):
        materialize(
            identity=IDENTITY,
            swaps=[],
            liquidity=liquidity[:1],
            provenance=_provenance(2000),
            state_time_ns=STATE_TIME_NS,
        )


# --------------------------------------------------------------------------
# The tables carry what the ordering names
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-062")
def test_both_tables_store_the_transaction_index() -> None:
    """§18.7's canonical order names it, `ChainMeta` has always carried it, and
    until this requirement neither table stored it."""
    for schema in (dex_swaps.SCHEMA, dex_liquidity.SCHEMA):
        assert "transaction_index" in schema.names

    for order in (dex_swaps.ORDER, dex_liquidity.ORDER):
        assert order[-3:] == ("block_number", "transaction_index", "log_index")


@pytest.mark.trace("REQ-WP-062")
def test_a_zero_amount_burn_does_not_refuse_a_partial_replay() -> None:
    """Four of the fifteen mint/burn logs in the fixture are burns of zero --
    the poke that settles fees before a collect.

    Applied as a burn, REQ-WP-015's guard refuses any sequence whose range has
    gone negative, which is what a partial replay looks like when the matching
    mint is older than the window. The row moved nothing; the refusal would be
    about the window.
    """
    zero_burns = [log for log in LOGS if log["kind"] == "Burn" and int(log.get("amount", "1")) == 0]
    assert len(zero_burns) == 4, "the fixture's own count, so a re-record is noticed"

    state = PoolState(
        address=IDENTITY.pool,
        token0=IDENTITY.token0,
        token1=IDENTITY.token1,
        fee_tier=IDENTITY.fee_tier,
        tick_spacing=IDENTITY.tick_spacing,
        current_tick=0,
        sqrt_price_x96=1,
        # A range whose mint predates the window: exactly the state a recent
        # replay is in.
        tick_liquidity_net={-60: Decimal(-1000)},
    )
    poke = liquidity_event(
        {
            "block_number": 1,
            "transaction_index": 0,
            "log_index": 0,
            "event_type": "burn",
            "tick_lower": -60,
            "tick_upper": 60,
            "liquidity_delta": "0",
            "amount0": Decimal(0),
            "amount1": Decimal(0),
        }
    )

    rebuilt = rebuild(state, [poke])

    assert rebuilt.tick_liquidity_net[-60] == Decimal(-1000), "nothing moved"
