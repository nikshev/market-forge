"""Round-trip guarantees for the canonical domain model (REQ-WP-002).

The acceptance criterion is "serialization fixtures stable", and these are the
tests that give that phrase teeth: an event must come back exactly as it went
out, including through a consumer that cannot hold a nanosecond in a double.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal

import pytest

from channelflow.domain import EventMeta
from channelflow.domain.serialization import dumps, loads


def _meta() -> EventMeta:
    return EventMeta(
        source="binance-ws",
        venue="binance",
        market_type="perp",
        symbol="BTCUSDT",
        event_time_ns=time.time_ns(),
        ingest_time_ns=time.time_ns(),
        sequence=42,
        source_event_id="abc-123",
    )


@pytest.mark.trace("REQ-WP-002")
def test_event_meta_round_trips_exactly() -> None:
    meta = _meta()
    assert loads(EventMeta, dumps(meta)) == meta


@pytest.mark.trace("REQ-WP-002")
def test_a_nanosecond_timestamp_survives_a_double_parsing_consumer() -> None:
    """SC-002. This is the finding the spec was written around.

    A current-epoch nanosecond timestamp is about 1.79e18, which exceeds
    JavaScript's Number.MAX_SAFE_INTEGER by more than two orders of magnitude.
    Emitted as a bare JSON number it drifts by ~128ns when a double-based
    consumer reads it -- and PRD sections 27 and 28 put a React UI on exactly
    this boundary.

    Parsing with `parse_int=float` simulates that consumer. If the encoding
    emits the timestamp as a number, this test fails.
    """
    meta = _meta()
    payload = dumps(meta)

    as_a_javascript_consumer_sees_it = json.loads(payload, parse_int=float)
    recovered = as_a_javascript_consumer_sees_it["event_time_ns"]

    assert int(recovered) == meta.event_time_ns, (
        f"timestamp drifted by {int(recovered) - meta.event_time_ns} ns; "
        "it must not be encoded as a JSON number"
    )


@pytest.mark.trace("REQ-WP-002")
def test_serializing_twice_is_byte_identical() -> None:
    """SC-004. Without this, 'the output changed' and 'it was written twice'
    are indistinguishable, and a fixture proves nothing."""
    meta = _meta()
    assert dumps(meta) == dumps(meta)


@pytest.mark.trace("REQ-WP-002")
def test_a_decimal_beyond_double_precision_survives() -> None:
    """SC-003. 28 significant digits; a double holds about 15."""
    from channelflow.domain import TradeEvent

    price = Decimal("12345.678901234567890123456789")
    trade = TradeEvent(
        meta=_meta(),
        trade_id="t-1",
        price=price,
        qty_base=Decimal("0.00000001"),
        notional_quote=Decimal("0.00012345678901234567890123"),
        aggressor_side="buy",
        is_buyer_maker=False,
    )
    assert loads(TradeEvent, dumps(trade)).price == price
