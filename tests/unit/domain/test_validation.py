"""Construction-time rejection and immutability (REQ-WP-002).

Failing at the boundary is the difference between a bad message and a corrupted
dataset. PRD section 0.4 forbids conflating the timestamp kinds, and a model
that lets `ingest_time_ns` be omitted makes that rule uncheckable.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from channelflow.domain import EventMeta, PriceLevel, TradeEvent


def _meta_fields() -> dict[str, object]:
    return {
        "source": "binance-ws",
        "venue": "binance",
        "market_type": "perp",
        "symbol": "BTCUSDT",
        "event_time_ns": 1788794605256368000,
        "ingest_time_ns": 1788794605256400000,
        "sequence": 1,
        "source_event_id": "x",
    }


@pytest.mark.trace("REQ-WP-002")
def test_omitting_ingest_time_is_rejected_and_the_field_is_named() -> None:
    """SC-007. The field cannot be optional, or PRD section 9's rule that no
    feature may use ingest_time as market information becomes uncheckable."""
    fields = _meta_fields()
    del fields["ingest_time_ns"]
    with pytest.raises(ValidationError, match="ingest_time_ns"):
        EventMeta(**fields)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-002")
def test_an_unknown_field_is_rejected() -> None:
    """A venue that adds a field must not have it silently swallowed."""
    with pytest.raises(ValidationError, match="event_time"):
        EventMeta(**{**_meta_fields(), "event_time": 1})  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-002")
def test_an_aggressor_side_outside_the_permitted_set_is_rejected() -> None:
    with pytest.raises(ValidationError, match="aggressor_side"):
        TradeEvent(
            meta=EventMeta(**_meta_fields()),  # type: ignore[arg-type]
            trade_id="t",
            price=Decimal("1"),
            qty_base=Decimal("1"),
            notional_quote=Decimal("1"),
            aggressor_side="sideways",  # type: ignore[arg-type]
        )


@pytest.mark.trace("REQ-WP-002")
def test_a_constructed_event_cannot_be_mutated() -> None:
    """SC-006. Constitution Principle III: history is immutable."""
    meta = EventMeta(**_meta_fields())  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        meta.event_time_ns = 0  # type: ignore[misc]


@pytest.mark.trace("REQ-WP-002")
def test_a_book_level_may_have_zero_quantity() -> None:
    """FR-012. In a delta, zero quantity is how a venue removes a rung.
    Rejecting it would make removals unrepresentable."""
    level = PriceLevel(price=Decimal("50000.5"), qty=Decimal("0"))
    assert level.is_removal


@pytest.mark.trace("REQ-WP-002")
def test_a_negative_trade_price_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeEvent(
            meta=EventMeta(**_meta_fields()),  # type: ignore[arg-type]
            trade_id="t",
            price=Decimal("-1"),
            qty_base=Decimal("1"),
            notional_quote=Decimal("1"),
            aggressor_side="buy",
        )
