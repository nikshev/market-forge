"""Derivatives states and liquidations built by hand (REQ-WP-013)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import DerivativesState, EventMeta, LiquidationEvent

MINUTE_NS = 60 * 1_000_000_000
HOUR_NS = 60 * MINUTE_NS
BASE_NS = 1788838800000000000


#: A tolerance wide enough to be irrelevant, for tests about something else.
#:
#: [[REQ-WP-026]] gave every state reader a maximum age with a five-minute
#: default. Most tests here place their states minutes or hours apart because
#: they are about point-in-time joins, settled intervals or z-scores -- not
#: about freshness. Passing this says so out loud, rather than letting a test
#: pass because its fixture happened to stay inside a window it never meant to
#: be inside.
NOT_ABOUT_FRESHNESS = 365 * 24 * 60 * MINUTE_NS


def meta(at: int, *, ingest_offset: int = 1) -> EventMeta:
    return EventMeta(
        source="test",
        venue="binance",
        market_type="perp",
        symbol="BTCUSDT",
        event_time_ns=BASE_NS + at * MINUTE_NS,
        ingest_time_ns=BASE_NS + at * MINUTE_NS + ingest_offset,
    )


def state(
    *,
    at: int,
    funding: float | None = None,
    next_funding_at: int | None = None,
    oi_usd: float | None = None,
    oi_base: float | None = None,
    mark: str | None = None,
    index: str | None = None,
    ingest_offset: int = 1,
) -> DerivativesState:
    return DerivativesState(
        meta=meta(at, ingest_offset=ingest_offset),
        mark_price=None if mark is None else Decimal(mark),
        index_price=None if index is None else Decimal(index),
        funding_rate=funding,
        next_funding_time_ns=None
        if next_funding_at is None
        else BASE_NS + next_funding_at * MINUTE_NS,
        open_interest_base=oi_base,
        open_interest_usd=oi_usd,
    )


def liquidation(*, at: int, side: str, notional: str, price: str = "112000") -> LiquidationEvent:
    return LiquidationEvent(
        meta=meta(at),
        side=side,  # type: ignore[arg-type]
        price=Decimal(price),
        qty=Decimal("1"),
        notional_usd=Decimal(notional),
    )


@pytest.fixture
def settled_history() -> list[DerivativesState]:
    """Eight funding intervals, each settling an hour apart, plus one still open.

    Rates: 0.0001 .. 0.0008 settled; the last state's interval ends in the
    future relative to the queries below.
    """
    states = [
        state(at=i * 60, funding=0.0001 * (i + 1), next_funding_at=(i + 1) * 60) for i in range(8)
    ]
    states.append(state(at=8 * 60, funding=0.0099, next_funding_at=9 * 60))
    return states
