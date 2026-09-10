"""What a venue will let you trade, and under what rules.

# @trace: REQ-WP-021

PRD §45's Phase 1 asks for "basic market metadata;" and says nothing more
anywhere, so "basic" is derived from what breaks without it rather than from
what an exchange happens to publish. Each field is here because something
downstream cannot be correct without it:

- **`tick_size`** — a fill at a price the venue cannot quote is a fill at a
  price that does not exist.
- **`step_size`** and **`min_notional`** — a position off the venue's size grid,
  or under its minimum, is not a trade anybody could place, and counting it
  inflates a result. PRD §41 rule 9 governs any economic evaluation.
- **`base_asset`, `quote_asset`, `contract_size`** — without them a perp's
  quantity is a number with no unit.
- **`status`** — an instrument that is halted is not one a signal can open on,
  and its absence and its halt are different facts.

**A bad rule is refused rather than defaulted.** An absent tick size stops a
calculation; a guessed one produces a number that looks like a measurement, and
that survives review.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class InstrumentRejected(ValueError):
    """A venue described an instrument in a way nothing downstream could use."""


@dataclass(frozen=True)
class Instrument:
    """One tradeable instrument and the rules the venue will enforce on it."""

    venue: str
    symbol: str
    market_type: str
    base_asset: str
    quote_asset: str
    #: The smallest price increment the venue quotes.
    tick_size: Decimal
    #: The smallest quantity increment the venue fills.
    step_size: Decimal
    #: The smallest order value the venue accepts.
    min_notional: Decimal
    #: What one contract is denominated in, or `None` for an instrument that has
    #: no contracts. Absent rather than `1`: a spot instrument with a contract
    #: size of one would let a later calculation multiply by it and be right by
    #: accident, which survives review in a way that being wrong does not.
    contract_size: Decimal | None
    status: str

    def __post_init__(self) -> None:
        for name in ("venue", "symbol", "market_type", "base_asset", "quote_asset", "status"):
            if not str(getattr(self, name)).strip():
                raise InstrumentRejected(
                    f"{self.venue}/{self.symbol}: {name} is empty; an instrument without "
                    "one cannot be told apart from another"
                )
        for name in ("tick_size", "step_size", "min_notional"):
            _require_positive(getattr(self, name), name=name, symbol=self.symbol)
        if self.contract_size is not None:
            # `None` is a fact about the instrument. Zero is a quantity nothing
            # can be denominated in, so it is a malformed payload either way.
            _require_positive(self.contract_size, name="contract_size", symbol=self.symbol)


def _require_positive(value: object, *, name: str, symbol: str) -> None:
    if not isinstance(value, Decimal):
        raise InstrumentRejected(
            f"{symbol}: {name} is a {type(value).__name__} and must be a Decimal; a rule "
            "that went through binary floating point is not the venue's rule"
        )
    if value <= 0:
        raise InstrumentRejected(
            f"{symbol}: {name} is {value} and must be positive; a zero increment is not a "
            "smaller increment, it is a missing one"
        )
