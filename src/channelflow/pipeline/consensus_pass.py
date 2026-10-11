"""The worker's consensus pass: a `consensus` row per minute close, refusals too (REQ-WP-096).

# @trace: REQ-WP-096

[[REQ-WP-091]] built the consensus line and the venue-basis pane and left them reading "no data"
because nothing wrote the table they read. [[REQ-WP-095]] writes `quotes`; this writes
`consensus`.

**One row per minute close, because every bar close is one.** A bar of any timeframe closes on a
minute boundary, so a consensus computed at every minute close serves every timeframe the chart
can show, and the API selects by `bar_close_ns`.

**Keyed by the viewed venue's symbol, as the API asks.** The venue-basis and consensus reads are
made with `asset=<the viewed series' symbol>` (`api/repositories.py`), so a group of markets that
are one asset gets one row per symbol its members use: the perpetual BTC consensus is stored under
`BTCUSDT` (Bybit's) and under `BTC-USDT-SWAP` (OKX's), identical in value, so that either chart
finds it. The canonical asset is what the registry groups by; the symbol is how the reader asks.

**A refusal is stored, not skipped.** Fewer than two venues of a market type, or none fresh,
writes a row with no price, the venue count and the reason -- so the Binance spot panes can say
*why* there is no line.

**Point in time.** A quote is used at a close only if its exchange time is at or before it and not
older than the staleness bound; later quotes cannot change an earlier row (the library already
refuses them with a reason, and the test appends later ones to prove it). The pass advances over a
close only once every venue that is alive has quotes up to it: a venue lagging behind the others
holds the pass back rather than being left out of a row it would have joined, and a venue that has
gone quiet for longer than `DEAD_AFTER_NS` stops holding it back (its stale quote is excluded by
the library's own rule)."""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from channelflow.assets import AssetRegistry, VenueKind
from channelflow.crossvenue.consensus import NoConsensus, NotComparable, consensus_mid
from channelflow.crossvenue.deployment import (
    MARKETS,
    ConsensusMarket,
    build_registry,
    groups,
    representation_key,
)
from channelflow.crossvenue.models import VenueQuote
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.tables import consensus as consensus_table
from channelflow.tables import quotes as quotes_table

MINUTE_NS = 60_000_000_000

#: A quote is current for fifteen seconds at a minute close. The library's own default is five,
#: which is right for a stream of quotes and wrong for one quote per minute taken at the minute's
#: last message: that message can precede the boundary by a few seconds on a quiet book.
STALENESS_NS = 15_000_000_000

#: A venue whose newest quote is this far behind the freshest of its group is not waited for.
DEAD_AFTER_NS = 10 * MINUTE_NS


@dataclass(frozen=True)
class Series:
    """One market's quotes, oldest first, with their times kept apart for a bisect per close.

    `ingests` is when each quote was stored: a minute's quote is written when the minute is
    finalised, a moment after its end, which is what says the venue's data is complete up to there.
    """

    times: tuple[int, ...]
    mids: tuple[Decimal, ...]
    ingests: tuple[int, ...]

    @classmethod
    def of(cls, quotes: Sequence[tuple[int, Decimal] | tuple[int, Decimal, int]]) -> Series:
        """From `(exchange time, mid)` or `(exchange time, mid, ingest time)`.

        Without an ingest time the quote is taken to have been stored at the end of its minute,
        which is when the collector writes it.
        """
        filled = [
            (q[0], q[1], q[2] if len(q) == 3 else -(-q[0] // MINUTE_NS) * MINUTE_NS) for q in quotes
        ]
        ordered = sorted(filled)
        return cls(
            tuple(t for t, _, _ in ordered),
            tuple(m for _, m, _ in ordered),
            tuple(i for _, _, i in ordered),
        )


QuoteSeries = Series


@dataclass(frozen=True)
class ClosedConsensus:
    """The consensus of one group at one minute close, as stored under each of its symbols."""

    asset_id: str
    market_type: str
    bar_close_ns: int
    consensus_mid: Decimal | None
    venue_count: int
    refusal_reason: str


def _fresh(series: Series | None, close_ns: int) -> tuple[int, Decimal] | None:
    """The newest quote at or before the close, or nothing."""
    if series is None:
        return None
    i = bisect_right(series.times, close_ns)
    return (series.times[i - 1], series.mids[i - 1]) if i else None


def consensus_at(
    group: Sequence[ConsensusMarket],
    series: Mapping[tuple[str, str], QuoteSeries],
    *,
    close_ns: int,
    registry: AssetRegistry,
    staleness_ns: int = STALENESS_NS,
) -> ClosedConsensus:
    """One group's consensus at one close, or a refusal carrying its reason and its venue count."""
    quotes: list[VenueQuote] = []
    for market in group:
        found = _fresh(series.get((market.venue, market.symbol)), close_ns)
        if found is None:
            continue
        ts, mid = found
        quotes.append(
            VenueQuote(
                venue_id=market.venue,
                kind=VenueKind.ORDER_BOOK,
                representation_key=representation_key(market),
                mid=mid,
                observed_at_ns=ts,
            )
        )
    asset_id, market_type = group[0].asset_id, group[0].market_type
    fresh = [q for q in quotes if 0 <= close_ns - q.observed_at_ns <= staleness_ns]
    try:
        result = consensus_mid(quotes, registry=registry, at_ns=close_ns, staleness_ns=staleness_ns)
    except (NoConsensus, NotComparable) as refusal:
        return ClosedConsensus(asset_id, market_type, close_ns, None, len(fresh), str(refusal))
    return ClosedConsensus(
        asset_id, market_type, close_ns, result.mid, result.contributor_count, ""
    )


def horizon_ns(
    group: Sequence[ConsensusMarket], series: Mapping[tuple[str, str], QuoteSeries]
) -> int | None:
    """The last close this group can be computed for without leaving out a venue that is alive.

    The minimum, over the venues with quotes, of each one's newest quote's *storage* time -- a
    minute's quote is stored when the minute ends, so that is how far the venue's data is known to
    be complete -- except that a venue more than `DEAD_AFTER_NS` behind the freshest is not waited
    for.
    """
    newest = {
        (m.venue, m.symbol): series[(m.venue, m.symbol)].ingests[-1]
        for m in group
        if series.get((m.venue, m.symbol)) is not None and series[(m.venue, m.symbol)].times
    }
    if not newest:
        return None
    freshest = max(newest.values())
    waiting = [t for t in newest.values() if freshest - t <= DEAD_AFTER_NS]
    return (min(waiting) // MINUTE_NS) * MINUTE_NS


def latest_closes(table: IcebergTable) -> dict[tuple[str, str], int]:
    """The latest stored close per `(asset key, market type)`: the pass's watermark."""
    rows = table.read()
    if rows.num_rows == 0:
        return {}
    grouped = rows.group_by(["asset", "market_type"]).aggregate([("bar_close_ns", "max")])
    keys = zip(grouped["asset"].to_pylist(), grouped["market_type"].to_pylist(), strict=True)
    return {k: int(v) for k, v in zip(keys, grouped["bar_close_ns_max"].to_pylist(), strict=True)}


def quote_series(table: IcebergTable) -> dict[tuple[str, str], QuoteSeries]:
    """Every stored quote as `(exchange time, mid)` by `(venue, symbol)`, oldest first."""
    rows = table.read()
    raw: dict[tuple[str, str], list[tuple[int, Decimal, int]]] = defaultdict(list)
    if rows.num_rows == 0:
        return {}
    for venue, symbol, mid, ts, ingest in zip(
        rows["venue"].to_pylist(),
        rows["symbol"].to_pylist(),
        rows["mid"].to_pylist(),
        rows["ts_ns"].to_pylist(),
        rows["ingest_ns"].to_pylist(),
        strict=True,
    ):
        raw[(str(venue), str(symbol))].append((int(ts), Decimal(str(mid)), int(ingest)))
    return {key: Series.of(items) for key, items in raw.items()}


def compute_rows(
    series: Mapping[tuple[str, str], QuoteSeries],
    watermark: Mapping[tuple[str, str], int],
    *,
    markets: tuple[ConsensusMarket, ...] = MARKETS,
    registry: AssetRegistry | None = None,
    staleness_ns: int = STALENESS_NS,
) -> list[dict[str, object]]:
    """The consensus rows past the watermark, one per close per symbol alias of each group."""
    registry = registry or build_registry(markets)
    rows: list[dict[str, object]] = []
    for (_, market_type), group in sorted(groups(markets).items()):
        horizon = horizon_ns(group, series)
        if horizon is None:
            continue
        aliases = sorted({m.symbol for m in group})
        start_of = {alias: watermark.get((alias, market_type)) for alias in aliases}
        first_quote = min(
            series[(m.venue, m.symbol)].times[0]
            for m in group
            if series.get((m.venue, m.symbol)) is not None and series[(m.venue, m.symbol)].times
        )
        first_close = ((first_quote // MINUTE_NS) + 1) * MINUTE_NS
        resume = min(
            (w + MINUTE_NS for w in start_of.values() if w is not None), default=first_close
        )
        if any(w is None for w in start_of.values()):
            resume = first_close
        close = max(first_close, resume)
        while close <= horizon:
            closed = consensus_at(
                group, series, close_ns=close, registry=registry, staleness_ns=staleness_ns
            )
            for alias in aliases:
                done = start_of[alias]
                if done is not None and close <= done:
                    continue
                rows.append(
                    consensus_table.to_row(
                        consensus_table.Consensus(
                            asset=alias,
                            market_type=market_type,  # type: ignore[arg-type]
                            bar_close_ns=close,
                            consensus_mid=closed.consensus_mid,
                            venue_count=closed.venue_count,
                            refusal_reason=closed.refusal_reason,
                        )
                    )
                )
            close += MINUTE_NS
    return rows


def write_consensus(catalog: Catalog) -> int:
    """Store the consensus for every minute close not yet stored; returns the rows written."""
    try:
        quotes = quote_series(quotes_table.table_for(catalog))
        table = consensus_table.table_for(catalog)
        watermark = latest_closes(table)
        rows = compute_rows(quotes, watermark)
    except Exception as cause:  # noqa: BLE001 -- the channel step must still run
        print(f"  consensus: could not compute -- {type(cause).__name__}: {cause}", flush=True)
        return 0
    written = 0
    if rows:
        try:
            table.append(rows)
            written = len(rows)
        except Exception as cause:  # noqa: BLE001 -- the channel step must still run
            print(
                f"  consensus: could not write {len(rows)} row(s) -- "
                f"{type(cause).__name__}: {cause}",
                flush=True,
            )
    print(f"  consensus rows written: {written}", flush=True)
    return written
