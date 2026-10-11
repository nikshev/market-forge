"""One row per minute of each order book the collector watches, and the quotes it implies.

# @trace: REQ-WP-095

The raw book is not archived (ADR-070: at 20-1000 ms across five markets it is the largest data in
the system and nothing required needs it); what is stored is what each minute amounted to,
computed in event time by `context.minute_book.MinuteBook`. The same finalised minute also writes
a row to the existing `quotes` table -- the venue's top of book at the minute's end, which is what
the cross-venue consensus ([[REQ-WP-091]], [[REQ-WP-096]]) is a median of.

Two times, never conflated (Principle II): `minute_close_ns` is event time -- the instant the
minute describes -- and `ingest_time_ns` is when this system finalised it, which can be a few
seconds later. `quote_time_ns` is the venue's own time of the last message behind the quote.

A minute with no frame is stored with `frames == 0` and nothing else: a thin minute is not a
balanced one, and the worker writes no feature for it. Prices are `decimal`, not `float64`; absent
is null."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from channelflow.context.minute_book import MinuteSummary
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema
from channelflow.tables import quotes as quotes_table

TABLE_NAME = "book_minutes"

SCHEMA = Schema(
    columns=(
        Column(name="minute_close_ns", type="timestamp_ns"),
        Column(name="ingest_time_ns", type="int64"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="market_type", type="string"),
        Column(name="source", type="string"),
        Column(name="frames", type="int64"),
        Column(name="observations", type="int64"),
        Column(name="ofi", type="decimal"),
        Column(name="depth_imbalance_10", type="float64"),
        Column(name="bid", type="decimal"),
        Column(name="ask", type="decimal"),
        Column(name="mid", type="decimal"),
        Column(name="quote_time_ns", type="int64"),
    ),
    event_time_column="minute_close_ns",
)


@dataclass(frozen=True)
class BookMinute:
    """A stored minute, as the worker reads it."""

    minute_close_ns: int
    ingest_time_ns: int
    frames: int
    observations: int
    ofi: Decimal | None
    depth_imbalance_10: float | None
    mid: Decimal | None


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


def to_row(summary: MinuteSummary, *, ingest_time_ns: int, market_type: str) -> dict[str, object]:
    return {
        "minute_close_ns": summary.minute_close_ns,
        "ingest_time_ns": ingest_time_ns,
        "venue": summary.venue,
        "symbol": summary.symbol,
        "market_type": market_type,
        "source": f"{summary.venue}-ws-book",
        "frames": summary.frames,
        "observations": summary.observations,
        "ofi": summary.ofi,
        "depth_imbalance_10": summary.depth_imbalance_10,
        "bid": summary.bid,
        "ask": summary.ask,
        "mid": summary.mid,
        "quote_time_ns": summary.quote_time_ns,
    }


def quote_of(summary: MinuteSummary, *, ingest_time_ns: int) -> quotes_table.Quote | None:
    """The quote a minute implies, or nothing for a minute with no honest top of book."""
    if summary.mid is None or summary.bid is None or summary.ask is None:
        return None
    return quotes_table.Quote(
        venue=summary.venue,
        symbol=summary.symbol,
        bid=summary.bid,
        ask=summary.ask,
        mid=summary.mid,
        ts_ns=summary.quote_time_ns or summary.minute_close_ns,
        ingest_ns=ingest_time_ns,
    )


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def from_row(row: Mapping[str, Any]) -> BookMinute:
    return BookMinute(
        minute_close_ns=int(row["minute_close_ns"]),
        ingest_time_ns=int(row["ingest_time_ns"]),
        frames=int(row["frames"]),
        observations=int(row["observations"]),
        ofi=_decimal(row["ofi"]),
        depth_imbalance_10=row["depth_imbalance_10"],
        mid=_decimal(row["mid"]),
    )


@dataclass
class BookMinuteSink:
    """Collects finalised minutes and writes them, and their quotes, in batches, each once."""

    table: IcebergTable
    quotes: IcebergTable
    _minutes: list[dict[str, object]] = field(default_factory=list)
    _quotes: list[dict[str, object]] = field(default_factory=list)
    _known: set[tuple[str, str, int]] | None = None

    def _seen(self) -> set[tuple[str, str, int]]:
        if self._known is None:
            rows = self.table.read()
            self._known = set()
            if rows.num_rows:
                self._known = {
                    (str(v), str(s), int(m))
                    for v, s, m in zip(
                        rows["venue"].to_pylist(),
                        rows["symbol"].to_pylist(),
                        rows["minute_close_ns"].to_pylist(),
                        strict=True,
                    )
                }
        return self._known

    def __call__(self, summary: MinuteSummary, *, ingest_time_ns: int, market_type: str) -> None:
        key = (summary.venue, summary.symbol, summary.minute_close_ns)
        known = self._seen()
        if key in known:
            return
        known.add(key)
        self._minutes.append(
            to_row(summary, ingest_time_ns=ingest_time_ns, market_type=market_type)
        )
        quote = quote_of(summary, ingest_time_ns=ingest_time_ns)
        if quote is not None:
            self._quotes.append(quotes_table.to_row(quote))

    @property
    def pending(self) -> int:
        return len(self._minutes) + len(self._quotes)

    def flush(self) -> str | None:
        snapshot = None
        if self._minutes:
            snapshot = self.table.append(self._minutes).content_hash
            self._minutes.clear()
        if self._quotes:
            self.quotes.append(self._quotes)
            self._quotes.clear()
        return snapshot


def read_minutes(table: IcebergTable) -> dict[tuple[str, str], list[BookMinute]]:
    """Every stored minute by `(venue, symbol)`, oldest first."""
    grouped: dict[tuple[str, str], list[BookMinute]] = defaultdict(list)
    for row in table.read().to_pylist():
        grouped[(str(row["venue"]), str(row["symbol"]))].append(from_row(row))
    for rows in grouped.values():
        rows.sort(key=lambda r: r.minute_close_ns)
    return dict(grouped)
