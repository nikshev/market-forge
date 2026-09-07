"""Golden serialization fixtures (REQ-WP-002).

REQ-WP-002's acceptance criterion is literally "serialization fixtures stable".
These files are that criterion: if a model's encoding changes, the change shows
up here as a diff a reviewer must look at, rather than silently reshaping every
stored event.

Regenerate deliberately with `pytest --regenerate-fixtures`, never by hand.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.domain import (
    BookDelta,
    BookSnapshot,
    ChainMeta,
    DerivativesState,
    DexLiquidityEvent,
    DexSwapEvent,
    EventMeta,
    LiquidationEvent,
    PriceLevel,
    TradeEvent,
)
from channelflow.domain.serialization import dumps, loads

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "domain"

# Fixed values, never `now()`: a fixture that changes with the clock is not a
# fixture. The timestamp is deliberately above 2**53 so every regeneration
# re-proves the JavaScript-safety property.
META = EventMeta(
    source="binance-ws",
    venue="binance",
    market_type="perp",
    symbol="BTCUSDT",
    event_time_ns=1788794605256368000,
    ingest_time_ns=1788794605256400123,
    sequence=98765,
    source_event_id="evt-1",
)
CHAIN = ChainMeta(
    chain_id=42161,
    block_number=250000000,
    block_time_ns=1788794605000000000,
    tx_hash="0xdeadbeef",
    tx_index=4,
    log_index=11,
)

CASES: dict[str, object] = {
    "trade": TradeEvent(
        meta=META,
        trade_id="t-1",
        price=Decimal("50123.45678901234567890123"),
        qty_base=Decimal("0.00000001"),
        notional_quote=Decimal("0.0005012345678901234567"),
        aggressor_side="sell",
        is_buyer_maker=True,
    ),
    "book_delta": BookDelta(
        meta=META,
        first_update_id=1,
        final_update_id=3,
        prev_update_id=0,
        bids=(PriceLevel(price=Decimal("50000.1"), qty=Decimal("2.5")),),
        # Zero quantity: the venue removing this rung.
        asks=(PriceLevel(price=Decimal("50001.9"), qty=Decimal("0")),),
    ),
    "book_snapshot": BookSnapshot(
        meta=META,
        update_id=3,
        bids=(PriceLevel(price=Decimal("50000.1"), qty=Decimal("2.5")),),
        asks=(PriceLevel(price=Decimal("50001.9"), qty=Decimal("1.25")),),
    ),
    "derivatives_state": DerivativesState(
        meta=META,
        mark_price=Decimal("50100.5"),
        index_price=Decimal("50099.25"),
        funding_rate=-0.000125,
        next_funding_time_ns=1788800000000000000,
        open_interest_base=12345.678,
        open_interest_usd=618000000.0,
        basis_bps=-3.2,
    ),
    "liquidation": LiquidationEvent(
        meta=META,
        side="long_liquidated",
        price=Decimal("49850.75"),
        qty=Decimal("3.5"),
        notional_usd=Decimal("174477.625"),
    ),
    "dex_swap": DexSwapEvent(
        meta=META,
        chain=CHAIN,
        dex="uniswap-v3",
        pool="0xpool",
        token0="WETH",
        token1="USDC",
        amount0=Decimal("-1.5"),
        amount1=Decimal("4200.123456"),
        price_token1_per_token0=Decimal("2800.082304"),
        notional_usd=Decimal("4200.12"),
        sqrt_price_x96=4295128739000000000000000000,
        tick=-201234,
        liquidity=987654321012345678,
    ),
    "dex_liquidity": DexLiquidityEvent(
        meta=META,
        chain=CHAIN,
        dex="uniswap-v3",
        pool="0xpool",
        event_type="burn",
        tick_lower=-202000,
        tick_upper=-200000,
        liquidity_delta=-123456789,
        amount0=Decimal("0.5"),
        amount1=Decimal("1400.0"),
    ),
}


@pytest.mark.trace("REQ-WP-002")
@pytest.mark.parametrize("name", sorted(CASES))
def test_serialization_matches_the_committed_fixture(
    name: str, request: pytest.FixtureRequest
) -> None:
    """SC-005. A changed encoding must surface as a diff, not as silence."""
    path = FIXTURES / f"{name}.json"
    produced = dumps(CASES[name])  # type: ignore[arg-type]

    if request.config.getoption("--regenerate-fixtures"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(produced + "\n")
        pytest.skip(f"regenerated {path.name}")

    assert path.is_file(), f"missing fixture {path}; regenerate with --regenerate-fixtures"
    assert produced == path.read_text().rstrip("\n"), (
        f"{name} serializes differently than its committed fixture. If this is "
        "intended, regenerate and review the diff -- every stored event changes shape."
    )


@pytest.mark.trace("REQ-WP-002")
@pytest.mark.parametrize("name", sorted(CASES))
def test_every_kind_round_trips(name: str) -> None:
    """SC-001, across all seven kinds rather than one."""
    original = CASES[name]
    assert loads(type(original), dumps(original)) == original  # type: ignore[arg-type]
