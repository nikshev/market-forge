"""Deduplication identity (REQ-WP-002, PRD section 11.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import ChainMeta, DexSwapEvent, EventMeta, TradeEvent


def _meta(ingest: int = 1788794605256400000) -> EventMeta:
    return EventMeta(
        source="s",
        venue="binance",
        market_type="perp",
        symbol="BTCUSDT",
        event_time_ns=1788794605256368000,
        ingest_time_ns=ingest,
        sequence=1,
        source_event_id="x",
    )


def _trade(ingest: int, trade_id: str = "t-1") -> TradeEvent:
    return TradeEvent(
        meta=_meta(ingest),
        trade_id=trade_id,
        price=Decimal("50000"),
        qty_base=Decimal("1"),
        notional_quote=Decimal("50000"),
        aggressor_side="buy",
    )


@pytest.mark.trace("REQ-WP-002")
def test_the_same_trade_received_twice_has_one_identity() -> None:
    """A websocket replay and a backfill see the same trade at different times.
    Arrival time must not make them look like two trades."""
    assert _trade(1).identity == _trade(999).identity


@pytest.mark.trace("REQ-WP-002")
def test_a_different_trade_id_is_a_different_identity() -> None:
    assert _trade(1, "t-1").identity != _trade(1, "t-2").identity


@pytest.mark.trace("REQ-WP-002")
def test_a_dex_log_is_identified_by_chain_tx_and_log_index() -> None:
    def swap(log_index: int) -> DexSwapEvent:
        return DexSwapEvent(
            meta=_meta(),
            chain=ChainMeta(
                chain_id=42161,
                block_number=100,
                block_time_ns=1788794605000000000,
                tx_hash="0xabc",
                tx_index=3,
                log_index=log_index,
            ),
            dex="uniswap-v3",
            pool="0xpool",
            token0="WETH",
            token1="USDC",
            amount0=Decimal("-1.5"),
            amount1=Decimal("4200"),
            price_token1_per_token0=Decimal("2800"),
        )

    assert swap(7).identity == (42161, "0xabc", 7)
    assert swap(7).identity != swap(8).identity
