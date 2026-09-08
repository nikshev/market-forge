"""Positions, anchors and price paths (REQ-WP-020)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from channelflow.stops import AnchorKind, PositionState, PricePoint, StopAnchor

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1788838800000000000
POSITION_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


def long_position(**overrides: object) -> PositionState:
    """Entry 100, initial stop 95, target 115. R0 = 5."""
    fields = {
        "position_id": POSITION_ID,
        "instrument_id": "BTCUSDT",
        "venue": "binance",
        "side": "LONG",
        "quantity": Decimal("1"),
        "entry_time_ns": at(0),
        "average_entry_price": Decimal("100"),
        "initial_stop_price": Decimal("95"),
        "current_strategy_stop": Decimal("95"),
        "original_target_price": Decimal("115"),
    }
    fields.update(overrides)
    return PositionState(**fields)  # type: ignore[arg-type]


def short_position(**overrides: object) -> PositionState:
    """Entry 100, initial stop 105, target 85. R0 = 5."""
    fields = {
        "position_id": POSITION_ID,
        "instrument_id": "BTCUSDT",
        "venue": "binance",
        "side": "SHORT",
        "quantity": Decimal("1"),
        "entry_time_ns": at(0),
        "average_entry_price": Decimal("100"),
        "initial_stop_price": Decimal("105"),
        "current_strategy_stop": Decimal("105"),
        "original_target_price": Decimal("85"),
    }
    fields.update(overrides)
    return PositionState(**fields)  # type: ignore[arg-type]


def anchor(
    price: str, *, known_at: int, kind: AnchorKind = AnchorKind.CONFIRMED_SWING
) -> StopAnchor:
    return StopAnchor(
        kind=kind,
        price=Decimal(price),
        known_at_ns=at(known_at),
        description=f"test anchor at {price}",
    )


def point(
    minute: int,
    price: str,
    *,
    noise: str = "0.5",
    anchors: tuple[StopAnchor, ...] = (),
    data_ok: bool = True,
) -> PricePoint:
    return PricePoint(
        at_ns=at(minute),
        price=Decimal(price),
        noise_distance=Decimal(noise),
        anchors=anchors,
        data_quality_ok=data_ok,
    )


@pytest.fixture
def rising_path() -> list[PricePoint]:
    """Price walks from 101 to 112, with a swing low confirmed at minute 5."""
    low = anchor("99", known_at=5)
    return [point(i, str(101 + i), anchors=(low,) if i >= 5 else ()) for i in range(12)]
