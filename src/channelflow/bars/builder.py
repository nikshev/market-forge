"""Aggregate trades into event-time bars.

# @trace: REQ-WP-005

Two properties here are the whole point, and both are absences rather than
features.

**There is no clock.** The builder takes no clock argument and imports no time
module, so wall-clock time cannot influence a bar boundary even by accident.
Closing a bar on local time would make boundaries depend on our own latency, and
a replay would then produce different bars from identical input -- breaking
Principle VII, which is what the backtest rests on.

**There is no amendment.** Once a bar finalizes it is published and forgotten.
A trade arriving for a closed window is discarded and counted, per ADR-005. PRD
section 0.5 forbids rewriting finalized snapshots and section 0.3 forbids a
value computed at `t` changing afterwards; a self-amending bar is both.

Time advances only by watermark: the highest `event_time_ns` seen so far.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, localcontext

from channelflow.bars.models import Bar
from channelflow.domain import TradeEvent


@dataclass
class _Accumulator:
    """Mutable state for one open window. Becomes an immutable Bar at close."""

    open_time_ns: int
    first_event_ns: int
    last_event_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    high_time_ns: int
    low_time_ns: int
    volume_base: Decimal
    volume_quote: Decimal
    trade_count: int
    aggressive_buy_base: Decimal
    aggressive_sell_base: Decimal
    first_trade_id: str
    last_trade_id: str

    def add(self, trade: TradeEvent) -> None:
        event_ns = trade.meta.event_time_ns
        price = trade.price
        qty = trade.qty_base

        # Open and close follow event time, not arrival order: a trade that
        # arrives late but happened first is still the open.
        if event_ns < self.first_event_ns:
            self.first_event_ns = event_ns
            self.open = price
            self.first_trade_id = trade.trade_id
        if event_ns >= self.last_event_ns:
            self.last_event_ns = event_ns
            self.close = price
            self.last_trade_id = trade.trade_id

        # On a tie, the EARLIEST event time wins -- not the first to arrive.
        # Using a strict comparison made these two fields depend on arrival
        # order whenever a price repeated, so a replay produced different
        # timestamps from identical input. Caught by the shuffle test, which is
        # what SC-003 exists for.
        if price > self.high or (price == self.high and event_ns < self.high_time_ns):
            self.high = price
            self.high_time_ns = event_ns
        if price < self.low or (price == self.low and event_ns < self.low_time_ns):
            self.low = price
            self.low_time_ns = event_ns

        self.volume_base += qty
        self.volume_quote += trade.notional_quote
        self.trade_count += 1
        if trade.aggressor_side == "buy":
            self.aggressive_buy_base += qty
        elif trade.aggressor_side == "sell":
            self.aggressive_sell_base += qty


@dataclass
class BarBuilder:
    """One symbol, one timeframe. Composition of several is the caller's."""

    timeframe_ns: int
    grace_ns: int = 5_000_000_000
    on_final: Callable[[Bar], None] | None = None

    #: Discarded trades whose window had already closed. Rising means the grace
    #: period is too short -- visible rather than inferred from missing volume.
    late_trade_count: int = 0

    _open: dict[int, _Accumulator] = field(default_factory=dict)
    _watermark_ns: int = 0
    _finalized_before_ns: int = 0

    def window_start(self, event_time_ns: int) -> int:
        """A trade exactly on a boundary belongs to the window that opens there."""
        return (event_time_ns // self.timeframe_ns) * self.timeframe_ns

    def add(self, trade: TradeEvent) -> None:
        event_ns = trade.meta.event_time_ns
        start = self.window_start(event_ns)

        if start < self._finalized_before_ns:
            # ADR-005: the bar is published; it is not amended.
            self.late_trade_count += 1
            return

        accumulator = self._open.get(start)
        if accumulator is None:
            accumulator = _Accumulator(
                open_time_ns=start,
                first_event_ns=event_ns,
                last_event_ns=event_ns,
                open=trade.price,
                high=trade.price,
                low=trade.price,
                close=trade.price,
                high_time_ns=event_ns,
                low_time_ns=event_ns,
                volume_base=Decimal(0),
                volume_quote=Decimal(0),
                trade_count=0,
                aggressive_buy_base=Decimal(0),
                aggressive_sell_base=Decimal(0),
                first_trade_id=trade.trade_id,
                last_trade_id=trade.trade_id,
            )
            self._open[start] = accumulator
        accumulator.add(trade)

        self._venue = trade.meta.venue
        self._symbol = trade.meta.symbol

        if event_ns > self._watermark_ns:
            self._watermark_ns = event_ns
            self._finalize_ready()

    def _finalize_ready(self) -> None:
        """Close every window whose end plus grace the watermark has passed.

        In event-time order, so a watermark jump across several windows
        publishes them in the order they happened.
        """
        ready = sorted(
            start
            for start in self._open
            if self._watermark_ns >= start + self.timeframe_ns + self.grace_ns
        )
        for start in ready:
            accumulator = self._open.pop(start)
            bar = self._to_bar(accumulator)
            self._finalized_before_ns = max(self._finalized_before_ns, start + self.timeframe_ns)
            if self.on_final is not None:
                self.on_final(bar)

    def _to_bar(self, acc: _Accumulator) -> Bar:
        # Decimal's default context rounds at 28 significant digits, which
        # silently truncates a venue price carrying more -- caught by a test
        # rather than by review. A wider context makes the division exact for
        # any price a venue plausibly sends. Division is not exact in general
        # (a third of a unit never terminates), so this reduces loss rather
        # than eliminating it, and the width is stated rather than assumed.
        with localcontext() as ctx:
            ctx.prec = 60
            vwap = acc.volume_quote / acc.volume_base if acc.volume_base > 0 else acc.close
        return Bar(
            venue=self._venue,
            symbol=self._symbol,
            timeframe_ns=self.timeframe_ns,
            open_time_ns=acc.open_time_ns,
            close_time_ns=acc.open_time_ns + self.timeframe_ns,
            open=acc.open,
            high=acc.high,
            low=acc.low,
            close=acc.close,
            volume_base=acc.volume_base,
            volume_quote=acc.volume_quote,
            trade_count=acc.trade_count,
            aggressive_buy_base=acc.aggressive_buy_base,
            aggressive_sell_base=acc.aggressive_sell_base,
            delta_base=acc.aggressive_buy_base - acc.aggressive_sell_base,
            vwap=vwap,
            high_time_ns=acc.high_time_ns,
            low_time_ns=acc.low_time_ns,
            first_trade_id=acc.first_trade_id,
            last_trade_id=acc.last_trade_id,
            is_final=True,
        )
