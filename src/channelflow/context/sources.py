"""What the collector watches, for how long a reading stays current, and who it is shown to.

# @trace: REQ-WP-093

Three things live here because three other places must agree on them and none may own them:

* **Which perpetual a series is shown.** The Binance series are spot markets; their derivatives
  are the same venue's perpetual of the same pair (spec 145, FR-012). Bybit's and OKX's series are
  the perpetuals themselves. The association is declared once, here, and the collector and the
  worker both read it.
* **How old a reading may be and still be called current.** The derivatives library's default is
  five minutes, which is right for a figure polled every minute and wrong for two others:
  Binance's USD open interest is a five-minute bucket that lands late, and funding *settles* every
  eight hours, so with the default `funding_z` would exist for five minutes in eight hours. Each
  bound is stated with its reason, as Principle X asks.
* **The cadences.**
"""

from __future__ import annotations

from collections.abc import Mapping

MINUTE_NS = 60_000_000_000
HOUR_NS = 60 * MINUTE_NS
SECOND_NS = 1_000_000_000

#: How often each symbol is polled. Two calls a minute per symbol on Binance, one on Bybit and four
#: on OKX -- far below every venue's published limits.
POLL_INTERVAL_S = 60

#: How often the settled-funding history is re-read, so each new settlement enters as it happens.
HISTORY_REFRESH_S = 3600

#: How often buffered rows are committed, and the size that commits them early.
FLUSH_INTERVAL_S = 300
FLUSH_ROWS = 50

#: A polled state is current for three poll intervals: one missed poll is tolerated, three are not.
POLLED_STALENESS_NS = 3 * MINUTE_NS

#: Binance's USD open interest is a five-minute bucket dated at its own time and visible some
#: minutes after it, so it is current for longer than a polled state: the bucket's width, the lag it
#: arrives with, and slack.
OPEN_INTEREST_STALENESS_NS = 15 * MINUTE_NS

#: A settled funding rate stays the *latest* settlement for one funding interval (8 hours on every
#: venue the deployment watches; some symbols settle every 4) plus a margin for the venue publishing
#: the settlement late. Past it the venue has missed a settlement and the figure is not the rate
#: now.
FUNDING_INTERVAL_NS = 8 * HOUR_NS
FUNDING_MARGIN_NS = HOUR_NS
FUNDING_STALENESS_NS = FUNDING_INTERVAL_NS + FUNDING_MARGIN_NS

#: The number of settled rates `funding_z` needs (PRD §16.1's window; ADR-026 refuses on fewer).
FUNDING_WINDOW = 24

#: Every series the deployment ingests: `(venue, symbol, market type)`. The one list. The perpetual
#: each is shown, the symbols a venue's collector polls, and the symbols whose books it keeps all
#: derive from or are checked against it, so adding a market is a line here and not a hunt
#: (REQ-WP-098).
SERIES: tuple[tuple[str, str, str], ...] = (
    ("binance", "BTCUSDT", "spot"),
    ("binance", "ETHUSDT", "spot"),
    ("binance", "SOLUSDT", "spot"),
    ("bybit", "BTCUSDT", "perp"),
    ("bybit", "HYPEUSDT", "perp"),
    ("okx", "BTC-USDT-SWAP", "perp"),
    ("okx", "BTC-USDT", "spot"),
    ("okx", "ETH-USDT", "spot"),
    ("okx", "SOL-USDT", "spot"),
)

#: `(venue, series symbol)` -> the venue's perpetual symbol that series' derivatives come from.
#: Named, not derived from the symbol's spelling: that a spot pair's perpetual is `<pair>-SWAP` on
#: OKX is a fact about OKX, and a rule in code that guessed it would be wrong for the next venue.
PERPETUALS: Mapping[tuple[str, str], str] = {
    ("binance", "BTCUSDT"): "BTCUSDT",
    ("binance", "ETHUSDT"): "ETHUSDT",
    ("binance", "SOLUSDT"): "SOLUSDT",
    ("bybit", "BTCUSDT"): "BTCUSDT",
    ("bybit", "HYPEUSDT"): "HYPEUSDT",
    ("okx", "BTC-USDT-SWAP"): "BTC-USDT-SWAP",
    ("okx", "BTC-USDT"): "BTC-USDT-SWAP",
    ("okx", "ETH-USDT"): "ETH-USDT-SWAP",
    ("okx", "SOL-USDT"): "SOL-USDT-SWAP",
}


def perpetual_for(venue: str, symbol: str) -> str | None:
    """The perpetual a series' derivatives come from, or `None` for a series that has none."""
    return PERPETUALS.get((venue, symbol))


def symbols_for(venue: str) -> tuple[str, ...]:
    """The perpetual symbols the collector of one venue polls, each once, in a stable order."""
    return tuple(sorted({perp for (v, _), perp in PERPETUALS.items() if v == venue}))


def book_symbols_for(venue: str) -> tuple[str, ...]:
    """The symbols whose order books the collector of one venue keeps: its own series.

    A book is of the market a series is -- a spot series' book is the spot book, never its
    perpetual's -- so these are the series' symbols and not `symbols_for`'s.
    """
    return tuple(sorted(symbol for v, symbol, _ in SERIES if v == venue))


def market_type_of(venue: str, symbol: str) -> str:
    """`spot` or `perp` for a series; a series the deployment does not ingest is a `KeyError`."""
    for v, s, market_type in SERIES:
        if (v, s) == (venue, symbol):
            return market_type
    raise KeyError(f"{venue} {symbol} is not a series this deployment ingests")
