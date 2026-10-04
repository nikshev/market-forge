"""Price bins collected from the trades, for the volume profile.

# @trace: REQ-WP-089

PRD section 14.1: "Compute true trade-based volume by price bins from exchange trades where
available. Do not infer buy/sell direction from candle color if aggressor-side trades are
available." `profile.build` does that over a list of trades, and no trade is stored; a stored bar
has the aggressor split for the whole bar and no price inside it. So the ingest collects the bins
itself, **from now on**: there is no history to recover them from, and none is invented from bars.

A *block* is five minutes of one symbol's trades (configurable), aggregated per price bin into
buy, sell and unknown base volume from the aggressor side alone, and written once when it closes.
Per trade would be hundreds of millions of rows; per minute and per tick about fifty million a
year per symbol; five minutes of coarse bins is a few thousand a day, and a profile is for windows
of hours, so nothing a profile can show is lost. A block is knowable only at its close, so a
profile as of `t` uses whole blocks closed at or before `t` (Principle I).

The grid is `floor(price / width)` from zero, so a trade on a bin edge falls in the upper bin (the
profile builder's rule) and arrival order cannot change the bins. The width is a number of quote
units per symbol: configured, or derived once from the first trade's price (two basis points,
rounded to 1-2-5). It is written on every row, so a profile never mixes widths.

Windows and the watermark mirror `BarBuilder`'s: a block closes when the highest event time seen
passes its end plus the grace period, a trade for a closed block is discarded and counted, and
nothing is amended. A block whose trade ids show missed trades is **dropped, not flagged** (venues
with sequential ids only, measured on live bars: Binance): a wrong profile is worse than a missing
block.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.domain import TradeEvent

logger = logging.getLogger(__name__)

SECOND_NS = 1_000_000_000

#: Five minutes. A profile is for windows of hours, so this loses nothing it can show.
DEFAULT_BLOCK_NS = 300 * SECOND_NS

#: What the default bin width is, in basis points of the first trade's price.
DEFAULT_WIDTH_BPS = Decimal(2)


@dataclass(frozen=True)
class BinRow:
    """One price bin of one block, by the trade's aggressor side only."""

    index: int
    buy: Decimal
    sell: Decimal
    unknown: Decimal
    trades: int


@dataclass(frozen=True)
class BinBlock:
    """One closed block of one symbol: written once, never amended."""

    venue: str
    symbol: str
    block_open_time_ns: int
    block_ns: int
    bin_width: Decimal
    bins: tuple[BinRow, ...]

    @property
    def close_time_ns(self) -> int:
        return self.block_open_time_ns + self.block_ns


def nice_bin_width(price: Decimal, *, bps: Decimal = DEFAULT_WIDTH_BPS) -> Decimal:
    """A bin width of about `bps` basis points of `price`, rounded to 1, 2 or 5 times a power of 10.

    Nearest in the logarithm, so 17 becomes 20 and 0.03 becomes 0.02: a round number reads on an
    axis, and one within a factor of 1.5 of the target does the job the target was for.
    """
    if price <= 0:
        raise ValueError("a bin width needs a positive price")
    raw = float(price * bps / Decimal(10_000))
    exponent = math.floor(math.log10(raw))
    candidates = [(m, exponent) for m in (1, 2, 5)] + [(1, exponent + 1)]
    mantissa, power = min(candidates, key=lambda c: abs(math.log(raw / (c[0] * 10.0 ** c[1]))))
    return Decimal(mantissa) * Decimal(10) ** power


def parse_bin_widths(text: str) -> dict[tuple[str, str], Decimal]:
    """`venue:SYMBOL=width,...`: the widths configured per symbol, refusing what is wrong by name.

    Empty is valid and means every symbol derives its own. A duplicate is refused, not resolved:
    two widths for one instrument is a configuration somebody should look at.
    """
    widths: dict[tuple[str, str], Decimal] = {}
    for entry in (part.strip() for part in text.split(",") if part.strip()):
        key, separator, raw = entry.partition("=")
        venue, colon, symbol = key.partition(":")
        if not separator or not colon or not venue.strip() or not symbol.strip():
            raise ValueError(f"profile bin width {entry!r}: expected venue:SYMBOL=width")
        try:
            width = Decimal(raw.strip())
        except ArithmeticError:
            raise ValueError(
                f"profile bin width for {symbol.strip()}: {raw.strip()!r} is not a number"
            ) from None
        if not width.is_finite() or width <= 0:
            raise ValueError(
                f"profile bin width for {symbol.strip()} must be positive, got {raw.strip()!r}"
            )
        pair = (venue.strip(), symbol.strip())
        if pair in widths:
            raise ValueError(
                f"profile bin width for {venue.strip()}:{symbol.strip()} is given twice"
            )
        widths[pair] = width
    return widths


@dataclass
class _Block:
    """Mutable state for one open block. Becomes an immutable `BinBlock` at close."""

    open_time_ns: int
    bins: dict[int, list[Decimal | int]] = field(default_factory=dict)
    trades: int = 0
    id_min: int = 0
    id_max: int = 0
    ids_numeric: bool = True


@dataclass
class PriceBinBuilder:
    """One symbol's price bins, in blocks. Composition of several symbols is the caller's."""

    block_ns: int = DEFAULT_BLOCK_NS
    #: Quote units per bin; `None` derives it once from the first trade's price and keeps it.
    bin_width: Decimal | None = None
    #: Whether this venue's trade ids are sequential per symbol
    #: (`VenueConfig.sequential_trade_ids`).
    sequential_ids: bool = False
    on_final: Callable[[BinBlock], None] | None = None
    grace_ns: int = 5 * SECOND_NS

    #: Trades for a block already closed: discarded and counted, never folded in.
    late_trades: int = 0
    #: Blocks dropped because their trade ids show missed trades.
    incomplete_blocks: int = 0

    _open: dict[int, _Block] = field(default_factory=dict)
    _watermark_ns: int = 0
    _finalized_before_ns: int = 0
    _venue: str = ""
    _symbol: str = ""

    def window_start(self, event_time_ns: int) -> int:
        """A trade exactly on a boundary belongs to the block that opens there."""
        return (event_time_ns // self.block_ns) * self.block_ns

    def add(self, trade: TradeEvent) -> None:
        event_ns = trade.meta.event_time_ns
        start = self.window_start(event_ns)
        if start < self._finalized_before_ns:
            self.late_trades += 1
            return

        if self.bin_width is None:
            self.bin_width = nice_bin_width(trade.price)
            logger.info(
                "price bin width for %s %s: %s", trade.meta.venue, trade.meta.symbol, self.bin_width
            )

        block = self._open.get(start)
        if block is None:
            block = _Block(open_time_ns=start)
            self._open[start] = block

        index = int(trade.price // self.bin_width)
        cell = block.bins.setdefault(index, [Decimal(0), Decimal(0), Decimal(0), 0])
        side = {"buy": 0, "sell": 1}.get(trade.aggressor_side, 2)
        cell[side] = cell[side] + trade.qty_base
        cell[3] = int(cell[3]) + 1

        block.trades += 1
        try:
            number = int(trade.trade_id)
        except ValueError:
            block.ids_numeric = False
        else:
            block.id_min = number if block.trades == 1 else min(block.id_min, number)
            block.id_max = number if block.trades == 1 else max(block.id_max, number)

        self._venue = trade.meta.venue
        self._symbol = trade.meta.symbol
        if event_ns > self._watermark_ns:
            self._watermark_ns = event_ns
            self._finalize_ready()

    def _finalize_ready(self) -> None:
        """Close every block whose end plus grace the watermark has passed, in event-time order."""
        ready = sorted(
            s for s in self._open if self._watermark_ns >= s + self.block_ns + self.grace_ns
        )
        for start in ready:
            block = self._open.pop(start)
            self._finalized_before_ns = max(self._finalized_before_ns, start + self.block_ns)
            if self.sequential_ids and block.ids_numeric and block.trades > 0:
                if block.id_max - block.id_min + 1 != block.trades:
                    self.incomplete_blocks += 1
                    logger.warning(
                        "price bins: block %s of %s %s dropped: ids %s..%s but %s trades",
                        start,
                        self._venue,
                        self._symbol,
                        block.id_min,
                        block.id_max,
                        block.trades,
                    )
                    continue
            assert self.bin_width is not None
            done = BinBlock(
                venue=self._venue,
                symbol=self._symbol,
                block_open_time_ns=start,
                block_ns=self.block_ns,
                bin_width=self.bin_width,
                bins=tuple(
                    BinRow(
                        index=index,
                        buy=Decimal(cell[0]),
                        sell=Decimal(cell[1]),
                        unknown=Decimal(cell[2]),
                        trades=int(cell[3]),
                    )
                    for index, cell in sorted(block.bins.items())
                ),
            )
            if self.on_final is not None:
                self.on_final(done)
