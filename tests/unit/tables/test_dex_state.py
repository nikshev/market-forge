"""PRD §18.12.2's `LiquidityState` as a canonical table (REQ-WP-060)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.dex import PoolState, Provenance, ReconstructionQuality
from channelflow.lakehouse import Catalog
from channelflow.tables import dex_state

FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "pool_state" / "uniswap_v3_events.jsonl"
)
HEADER: dict[str, Any] = json.loads(FIXTURE.read_text().splitlines()[0])
CONTRACT: dict[str, Any] = json.loads(FIXTURE.read_text().splitlines()[1])

STATE_TIME_NS = 1_700_000_000_000_000_000


def _state(**overrides: object) -> PoolState:
    fields: dict[str, object] = {
        "address": HEADER["pool"],
        "token0": HEADER["token0"],
        "token1": HEADER["token1"],
        "fee_tier": HEADER["fee_tier"],
        "tick_spacing": HEADER["tick_spacing"],
        "current_tick": CONTRACT["tick"],
        "sqrt_price_x96": int(CONTRACT["sqrt_price_x96"]),
        "active_liquidity": Decimal(CONTRACT["liquidity"]),
        "tick_liquidity_net": {
            CONTRACT["tick"] - 100: Decimal(CONTRACT["liquidity"]),
            CONTRACT["tick"] + 100: -Decimal(CONTRACT["liquidity"]),
        },
    }
    fields.update(overrides)
    return PoolState(**fields)  # type: ignore[arg-type]


def _row(state: PoolState, quality: ReconstructionQuality) -> dict[str, object]:
    return dex_state.to_row(
        state,
        chain_id=HEADER["chain_id"],
        venue="uniswap",
        protocol="uniswap_v3",
        reference_price=Decimal("3000.1666"),
        state_time_ns=STATE_TIME_NS,
        quality=quality,
        provenance=Provenance(
            from_block=HEADER["from_block"], to_block=HEADER["to_block"], contiguous=True
        ),
    )


@pytest.mark.trace("REQ-WP-060")
def test_a_state_survives_the_round_trip(catalog: Catalog) -> None:
    table = dex_state.table_for(catalog)
    row = _row(_state(), ReconstructionQuality.REPLAYED)

    sink = dex_state.DexStateSink(table=table)
    sink(row)
    assert sink.pending == 1
    assert sink.flush() is not None
    read = dex_state.from_row(table.read().to_pylist()[0])

    assert read["reconstruction_quality"] == "replayed"
    assert read["active_liquidity"] == CONTRACT["liquidity"]
    assert read["reference_price"] == Decimal("3000.1666")
    assert read["model_type"] == dex_state.CONCENTRATED_LIQUIDITY


@pytest.mark.trace("REQ-WP-060")
def test_liquidity_beyond_int64_survives(catalog: Catalog) -> None:
    """A `uint128` does not fit in an `int64`, and 5.48e18 is already past it."""
    assert int(CONTRACT["liquidity"]) > 2**62
    table = dex_state.table_for(catalog)

    table.append([_row(_state(), ReconstructionQuality.REPLAYED)])
    read = dex_state.from_row(table.read().to_pylist()[0])

    assert read["active_liquidity"] == CONTRACT["liquidity"]
    assert read["implied_active_liquidity"] == CONTRACT["liquidity"]


@pytest.mark.trace("REQ-WP-060")
def test_the_row_carries_the_evidence_for_its_own_quality(catalog: Catalog) -> None:
    """A row stating `partial_ticks` without the two numbers behind it would
    have to be taken on trust. With them a reader recomputes the verdict."""
    partial = _state(tick_liquidity_net={})
    table = dex_state.table_for(catalog)

    table.append([_row(partial, ReconstructionQuality.PARTIAL_TICKS)])
    read = dex_state.from_row(table.read().to_pylist()[0])

    assert read["reconstruction_quality"] == "partial_ticks"
    assert read["implied_active_liquidity"] == "0"
    assert read["active_liquidity"] == CONTRACT["liquidity"]
    assert read["initialized_ticks"] == 0
    assert read["implied_active_liquidity"] != read["active_liquidity"]


@pytest.mark.trace("REQ-WP-060")
def test_the_replayed_range_is_on_the_row(catalog: Catalog) -> None:
    """Without it the quality is unauditable: §18.7.2's comparison only means
    anything at the state's own block."""
    table = dex_state.table_for(catalog)

    table.append([_row(_state(), ReconstructionQuality.ANCHORED)])
    read = dex_state.from_row(table.read().to_pylist()[0])

    assert read["from_block"] == HEADER["from_block"]
    assert read["to_block"] == HEADER["to_block"]


@pytest.mark.trace("REQ-WP-060")
def test_a_negative_implied_liquidity_keeps_its_sign(catalog: Catalog) -> None:
    """A map missing its lower ticks can imply negative liquidity. Clamping it
    to zero would erase the evidence the column exists for."""
    upside_down = _state(
        tick_liquidity_net={CONTRACT["tick"] - 100: -Decimal(CONTRACT["liquidity"])}
    )
    table = dex_state.table_for(catalog)

    table.append([_row(upside_down, ReconstructionQuality.PARTIAL_TICKS)])
    read = dex_state.from_row(table.read().to_pylist()[0])

    assert str(read["implied_active_liquidity"]).startswith("-")


@pytest.mark.trace("REQ-WP-060")
def test_the_models_without_a_producer_are_null_not_empty() -> None:
    """§18.12.2 marks `reserve_state` and `invariant_state` nullable, and a
    concentrated-liquidity pool has neither. `model_type` says which to expect."""
    row = _row(_state(), ReconstructionQuality.REPLAYED)

    assert row["reserve_state"] is None
    assert row["invariant_state"] is None
    assert row["model_type"] == dex_state.CONCENTRATED_LIQUIDITY


@pytest.mark.trace("REQ-WP-060")
def test_the_columns_with_no_producer_are_absent_rather_than_null() -> None:
    """§18.12.2 lists `available_at` and `finality_status`; both live on
    REQ-WP-014's `ChainRecord` and are joined to a state, not carried by one.
    A column null on every row is a promise nothing keeps ([[REQ-WP-053]])."""
    assert "available_at_ns" not in dex_state.SCHEMA.names
    assert "finality_status" not in dex_state.SCHEMA.names
    assert "reconstruction_quality" in dex_state.SCHEMA.names


@pytest.mark.trace("REQ-WP-060")
def test_every_quality_is_writable_as_a_string() -> None:
    """The column is a string, so a new class cannot need a migration -- and
    each value has to round-trip as its own name rather than as an ordinal."""
    for quality in ReconstructionQuality:
        row = _row(_state(), quality)
        assert row["reconstruction_quality"] == quality.value
