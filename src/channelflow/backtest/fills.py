"""PRD section 25.4's fill models.

# @trace: REQ-BT-001

    Phase 1:
    - market-at-next-bar-open;
    - market-at-signal-close + configurable slippage.

    Phase 2:
    - trade-through limit fill approximation;
    - L2-aware simulation.

**The phase-2 models are not built.** A trade-through limit approximation and an
L2-aware simulation both need the book state at the fill instant, which a bar
series does not carry. Naming them here is what keeps this module honest about
which half of section 25.4 it is.

The difference between the two phase-1 models is most of the difference between
a backtest and a fantasy: a fill at the signal's own close is a fill at a price
that was already gone when the decision was made.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.bars import Bar


class NoFillAvailable(LookupError):
    """No price this model would accept, and the reason is named."""


@dataclass(frozen=True)
class Fill:
    """A price someone could have got, and what says so."""

    price: float
    model: str
    at_ns: int


def market_at_next_open(bars: list[Bar], *, signal_index: int) -> Fill:
    """Section 25.4's first phase-1 model.

    Refuses when there is no next bar rather than falling back to the close.
    The fallback would fill the last signal of every dataset at a better price
    than any other, and the bias grows with how recently the backtest ends.
    """
    if signal_index + 1 >= len(bars):
        raise NoFillAvailable(
            f"no bar after index {signal_index}, so there is no next open to fill at; "
            "falling back to the signal's own close would fill this trade better than "
            "every other one in the run"
        )
    following = bars[signal_index + 1]
    return Fill(
        price=float(following.open),
        model="market_at_next_bar_open",
        at_ns=following.open_time_ns,
    )


def market_at_signal_close(
    bars: list[Bar], *, signal_index: int, direction: str, slippage_bps: float
) -> Fill:
    """Section 25.4's second phase-1 model, with slippage against the trade.

    Slippage that helps is not slippage: a long pays above the close and a short
    receives below it, whatever the sign of the configured figure.
    """
    if not 0 <= signal_index < len(bars):
        raise NoFillAvailable(f"no bar at index {signal_index}")
    signal_bar = bars[signal_index]
    close = float(signal_bar.close)
    against = abs(slippage_bps) / 10_000.0
    price = close * (1.0 + against) if direction == "long" else close * (1.0 - against)
    return Fill(
        price=price,
        model="market_at_signal_close",
        at_ns=signal_bar.close_time_ns,
    )
