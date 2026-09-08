"""Order-independence and the absence of a clock (REQ-WP-005)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from channelflow.bars import Bar, BarBuilder
from tests.unit.bars.conftest import MINUTE_NS, make_trade


@pytest.mark.trace("REQ-WP-005")
def test_shuffled_trades_produce_identical_bars(base_ns: int) -> None:
    """SC-003, FR-013. Out-of-order arrival is the normal case; a builder
    sensitive to it would produce different history on every replay, and
    Principle VII would not hold."""
    trades = [
        make_trade(
            event_time_ns=base_ns + i * 1_000_000_000,
            price=str(100 + (i * 7) % 13),
            qty=str(1 + i % 3),
            side="buy" if i % 2 else "sell",
            trade_id=f"t-{i}",
        )
        for i in range(40)
    ]
    closer = make_trade(event_time_ns=base_ns + 5 * MINUTE_NS, price="1", qty="1")

    def run(sequence: list) -> list[Bar]:
        out: list[Bar] = []
        builder = BarBuilder(timeframe_ns=MINUTE_NS, grace_ns=5_000_000_000, on_final=out.append)
        for trade in sequence:
            builder.add(trade)
        builder.add(closer)
        return out

    in_order = run(list(trades))
    shuffled = list(trades)
    random.Random(1234).shuffle(shuffled)

    assert run(shuffled) == in_order


@pytest.mark.trace("REQ-WP-005")
def test_the_builder_cannot_consult_a_clock() -> None:
    """SC-006. Asserted over the source rather than assumed from the design.

    Closing a bar on wall-clock time would make boundaries depend on our own
    latency, so a replay would produce different bars from identical input.
    'The builder does not use wall-clock time' is the sort of property that
    holds until someone adds a convenience.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "bars"
    for module in package.glob("*.py"):
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
