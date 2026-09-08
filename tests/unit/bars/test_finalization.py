"""Finalization and the late-event policy (REQ-WP-005, ADR-005)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.bars import Bar, BarBuilder
from tests.unit.bars.conftest import MINUTE_NS, make_trade

GRACE_NS = 5_000_000_000


def _builder(finalized: list[Bar]) -> BarBuilder:
    return BarBuilder(timeframe_ns=MINUTE_NS, grace_ns=GRACE_NS, on_final=finalized.append)


@pytest.mark.trace("REQ-WP-005")
def test_a_trade_for_a_finalized_bar_is_discarded_and_counted(base_ns: int) -> None:
    """SC-002. PRD section 0.5 forbids rewriting a finalized snapshot, and a bar
    that amends itself after publication is exactly that."""
    finalized: list[Bar] = []
    builder = _builder(finalized)

    builder.add(make_trade(event_time_ns=base_ns + 1_000_000_000, price="100", qty="1"))
    builder.add(make_trade(event_time_ns=base_ns + 3 * MINUTE_NS, price="999", qty="1"))
    assert len(finalized) == 1
    published = finalized[0]

    builder.add(make_trade(event_time_ns=base_ns + 2_000_000_000, price="1", qty="50"))
    # Push the watermark on, so a phantom re-opened window would have a chance
    # to finalize and be seen.
    builder.add(make_trade(event_time_ns=base_ns + 20 * MINUTE_NS, price="1", qty="1"))

    assert builder.late_trade_count == 1
    for_that_window = [b for b in finalized if b.open_time_ns == base_ns]
    assert for_that_window == [published], (
        "a finalized window must produce exactly one bar, ever. Emitting a second "
        "one for the same window is the amendment ADR-005 forbids, wearing a "
        "different shape: the first bar is untouched but the history is not."
    )


@pytest.mark.trace("REQ-WP-005")
def test_a_trade_inside_the_grace_period_is_included(base_ns: int) -> None:
    """SC-005. The window is closed to new time, not to late arrivals, until
    the grace expires -- otherwise ordinary out-of-order delivery is lost."""
    finalized: list[Bar] = []
    builder = _builder(finalized)

    builder.add(make_trade(event_time_ns=base_ns + 30_000_000_000, price="100", qty="1"))
    # Watermark moves past the window end but not past the grace.
    builder.add(make_trade(event_time_ns=base_ns + MINUTE_NS + 1_000_000_000, price="200", qty="1"))
    # A straggler still belonging to the first window.
    builder.add(make_trade(event_time_ns=base_ns + 45_000_000_000, price="300", qty="1"))

    assert not finalized, "the grace period has not expired"
    builder.add(make_trade(event_time_ns=base_ns + 3 * MINUTE_NS, price="1", qty="1"))

    first = next(b for b in finalized if b.open_time_ns == base_ns)
    assert first.trade_count == 2, "the straggler belongs to this bar"
    assert first.high == Decimal("300")


@pytest.mark.trace("REQ-WP-005")
def test_a_watermark_jump_finalizes_every_window_in_order(base_ns: int) -> None:
    """SC-004, FR-012. One trade can advance time past several windows."""
    finalized: list[Bar] = []
    builder = _builder(finalized)

    for i in range(3):
        builder.add(
            make_trade(event_time_ns=base_ns + i * MINUTE_NS + 1_000_000_000, price="100", qty="1")
        )
    builder.add(make_trade(event_time_ns=base_ns + 10 * MINUTE_NS, price="1", qty="1"))

    assert [b.open_time_ns for b in finalized] == [
        base_ns,
        base_ns + MINUTE_NS,
        base_ns + 2 * MINUTE_NS,
    ], "windows must publish in event-time order"


@pytest.mark.trace("REQ-WP-005")
def test_a_window_with_no_trades_produces_no_bar(base_ns: int) -> None:
    """An empty window is absence of data, not a bar of zeroes."""
    finalized: list[Bar] = []
    builder = _builder(finalized)
    builder.add(make_trade(event_time_ns=base_ns + 1_000_000_000, price="100", qty="1"))
    builder.add(make_trade(event_time_ns=base_ns + 5 * MINUTE_NS, price="100", qty="1"))

    assert [b.open_time_ns for b in finalized] == [base_ns]
