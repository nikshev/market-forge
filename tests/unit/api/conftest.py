"""A populated repository and a client over it (REQ-API-001, REQ-STORE-002).

The repository fixture is parametrised over both implementations, so every
endpoint test in this package runs twice: once against the in-memory repository
and once against the canonical plane. [[ADR-019]] promised the durable one would
arrive "without any endpoint changing", and this is what turns that from a
promise into something the suite fails on.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from channelflow.api import InMemoryRepository, LakehouseRepository, create_app
from channelflow.bars import Bar
from channelflow.channels import ChannelQuality, ChannelSnapshot
from channelflow.lakehouse import InMemoryObjectStore
from channelflow.signals import Candidate, CandidateState, Transition

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1788838800000000000


def bar(index: int, close: float, *, timeframe_ns: int = MINUTE_NS) -> Bar:
    price = Decimal(str(round(close, 8)))
    open_ns = BASE_NS + index * timeframe_ns
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=timeframe_ns,
        open_time_ns=open_ns,
        close_time_ns=open_ns + timeframe_ns,
        open=price,
        high=price,
        low=price,
        close=price,
        volume_base=Decimal("1"),
        volume_quote=price,
        trade_count=1,
        aggressive_buy_base=Decimal("1"),
        aggressive_sell_base=Decimal("0"),
        delta_base=Decimal("1"),
        vwap=price,
        high_time_ns=open_ns,
        low_time_ns=open_ns,
        first_trade_id=f"t-{index}",
        last_trade_id=f"t-{index}",
        is_final=True,
    )


def snapshot(*, as_of_ns: int, center: float, slope: float = -0.01) -> ChannelSnapshot:
    return ChannelSnapshot(
        as_of_ns=as_of_ns,
        model_name="rolling_ols_log_price",
        model_version="1.0.0",
        lookback=60,
        center_now=center,
        upper_now=center + 500.0,
        lower_now=center - 500.0,
        slope_normalized=slope,
        width_pct=0.02,
        quality=ChannelQuality(
            score=0.8,
            submetrics={"r_squared": 0.9},
            contributing=("r_squared",),
            unavailable=("age",),
        ),
        source_max_event_time_ns=as_of_ns,
    )


def candidate(*, opened_at_ns: int = BASE_NS) -> Candidate:
    return Candidate(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        direction="short",
        boundary="upper",
        state=CandidateState.CONFIRMED,
        opened_at_ns=opened_at_ns,
        bars_since_open=3,
        history=(
            Transition(
                from_state=CandidateState.NONE,
                to_state=CandidateState.APPROACH,
                bar_close_time_ns=opened_at_ns,
                reason="price entered the upper zone",
            ),
        ),
    )


Repository = InMemoryRepository | LakehouseRepository


@pytest.fixture(params=["in_memory", "lakehouse"])
def repository(request: pytest.FixtureRequest) -> Repository:
    """Ten minutes of bars, one stored snapshot, one signal.

    Built twice, once per implementation. A test that passes against one and not
    the other is the divergence [[ADR-019]]'s port exists to prevent.
    """
    repo: Repository = (
        InMemoryRepository()
        if request.param == "in_memory"
        else LakehouseRepository(store=InMemoryObjectStore())
    )
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="spot")
    repo.add_market(venue="binance", symbol="ETHUSDT", market_type="spot")
    repo.add_market(venue="bybit", symbol="BTCUSDT", market_type="perp")
    for i in range(10):
        repo.add_bar(bar(i, 112000.0 + i))
    repo.add_channel_snapshot(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        snapshot=snapshot(as_of_ns=BASE_NS + 5 * MINUTE_NS, center=112000.0),
    )
    repo.add_signal(candidate())
    return repo


@pytest.fixture
def client(repository: Repository) -> TestClient:
    return TestClient(create_app(repository=repository))
