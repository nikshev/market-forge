"""Schemas, stores and tables for the canonical data plane (REQ-STORE-001)."""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

SECOND = 1_000_000_000


def trades_schema() -> Schema:
    """A slice of PRD §29.B's `cex_trades`, with an event time."""
    return Schema(
        columns=(
            Column(name="event_time_ns", type="timestamp_ns"),
            Column(name="symbol", type="string"),
            Column(name="price", type="float64"),
            Column(name="size", type="float64"),
            Column(name="buyer_is_maker", type="bool"),
        ),
        event_time_column="event_time_ns",
    )


def config_schema() -> Schema:
    """A table with no event time -- PRD §30's `market_config` is one."""
    return Schema(
        columns=(
            Column(name="key", type="string"),
            Column(name="value", type="string"),
        )
    )


def trade(index: int, *, symbol: str = "BTCUSDT", price: float = 50_000.0) -> dict[str, object]:
    return {
        "event_time_ns": index * SECOND,
        "symbol": symbol,
        "price": price,
        "size": 0.5,
        "buyer_is_maker": index % 2 == 0,
    }


@pytest.fixture
def trades(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)


@pytest.fixture
def config(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name="market_config", schema=config_schema(), catalog=catalog)
