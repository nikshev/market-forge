"""Where the API reads from.

# @trace: REQ-API-001
# @trace: REQ-US-001
# @trace: REQ-US-004
# @trace: REQ-WP-089
# @trace: REQ-WP-091

PRD section 29 defines the storage -- Iceberg on object storage, Pinot for HOT
serving, PostgreSQL for metadata. None of it is built, and REQ-WP-009's chart
cannot wait for it (ADR-019).

So the API depends on a protocol. The in-memory implementation below serves it
now; the durable one arrives with section 29 and replaces it without any
endpoint changing.

The protocol is also where the point-in-time rule lives. Every read takes its
bounds explicitly, so "never return data later than the instant asked for"
(FR-017) is a signature rather than something each route handler remembers.
The two consensus reads ([[REQ-WP-091]]) are the sharpest case of it: a
consensus or a basis after the instant asked for is hindsight drawn onto an
earlier chart, so both take their bounds on the signature and are computed
below over rows rather than over whatever the store happens to hold now.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from channelflow.alerting import signal_id_for
from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.domain import Instrument
from channelflow.extrema.models import ConfirmedExtremum, ExtremumCandidate
from channelflow.features.crossvenue_basis import venue_basis_bps
from channelflow.scoring import SignalScore
from channelflow.signals import Candidate

#: Namespace for signal ids. Shared with REQ-WP-008 so an alert's deep link and
#: the API name the same signal -- a different namespace here would make every
#: link a 404 while looking entirely correct.
from channelflow.tables.consensus import Consensus
from channelflow.tables.consensus import to_row as consensus_to_row
from channelflow.tables.dex_depth import DepthBand
from channelflow.tables.quotes import Quote
from channelflow.tables.quotes import to_row as quote_to_row
from channelflow.tables.rows import RowShape, as_int
from channelflow.tables.volume_bins import BinsRead, select_bins, to_rows
from channelflow.volume.bins import BinBlock


@dataclass(frozen=True)
class Market:
    venue: str
    symbol: str
    market_type: str
    #: [[REQ-WP-021]]'s trading rules, or nothing for a market nobody has
    #: ingested rules for. Absent rather than a zeroed instrument: an unknown
    #: tick size and a tick size of zero must never read alike.
    instrument: Instrument | None = None


@dataclass(frozen=True)
class Extrema:
    """What the chart may draw about turns, as of an instant.

    Two lists rather than one: a candidate and a confirmation are different
    claims, and a caller that had to tell them apart by a flag would eventually
    forget to ([[REQ-WP-028]]).
    """

    confirmed: list[ConfirmedExtremum]
    candidates: list[ExtremumCandidate]


@dataclass(frozen=True)
class ScoredSetup:
    """A market's latest score, and what PRD section 43 ranks it by.

    The three ranking factors live here rather than being computed on read:
    section 43 has them penalize staleness, illiquidity and repetition, and each
    needs state the API does not hold. The API ranks; it does not measure.
    """

    venue: str
    symbol: str
    score: SignalScore
    #: Section 22.4's "raw feature snapshot", stored with the score it explains.
    feature_snapshot: dict[str, float]
    model_version: str
    liquidity_factor: float = 1.0
    novelty_factor: float = 1.0


@dataclass(frozen=True)
class FeaturePoint:
    at_ns: int
    values: dict[str, float]


class Repository(Protocol):
    """What the API needs to be able to read."""

    def markets(self, *, venue: str | None, market_type: str | None) -> list[Market]: ...

    def extrema(
        self,
        *,
        instrument_id: str,
        timeframe_ns: int,
        as_of_ns: int | None,
    ) -> Extrema: ...

    def bars(
        self,
        *,
        venue: str,
        symbol: str,
        timeframe_ns: int,
        start_ns: int | None,
        end_ns: int | None,
        limit: int | None,
    ) -> list[Bar]: ...

    def channel_snapshot_at(
        self, *, venue: str, symbol: str, timeframe_ns: int, at_ns: int
    ) -> ChannelSnapshot | None: ...

    def feature_points(
        self, *, venue: str, symbol: str, timeframe_ns: int, start_ns: int, end_ns: int
    ) -> list[FeaturePoint]: ...

    def signals(
        self,
        *,
        symbol: str | None,
        timeframe_ns: int | None,
        status: str | None,
        start_ns: int | None,
        end_ns: int | None,
    ) -> list[Candidate]: ...

    def signal(self, signal_id: uuid.UUID) -> Candidate | None: ...

    def setup_score(self, *, venue: str, symbol: str) -> ScoredSetup | None: ...

    def dex_depth_at(self, *, chain_id: int, pool: str, at_ns: int) -> list[DepthBand]: ...

    def volume_bins(
        self, *, venue: str, symbol: str, as_of_ns: int | None, window_ns: int
    ) -> BinsRead: ...

    def get_consensus(
        self,
        *,
        asset: str,
        market_type: str,
        timeframe_ns: int,
        window_ns: int,
        at_ns: int | None,
    ) -> list[dict[str, object]]: ...

    def get_venue_basis(
        self,
        *,
        asset: str,
        market_type: str,
        venue: str,
        timeframe_ns: int,
        start_ns: int,
        end_ns: int,
    ) -> list[dict[str, object]]: ...


# --- the consensus reads, over rows -------------------------------------
#
# Both are functions over stored rows rather than methods bound to one
# implementation, the way `select_bins` is (`tables/volume_bins.py`): "one
# function, so the table and the in-memory repository cannot disagree about
# it". The plane's read and this process's rows differ only in where the rows
# came from, and the point-in-time rule must not be one of those differences.


def _stored_price(row: Mapping[str, object], field: str) -> Decimal | None:
    """A decimal column as a price, or `None` where the row holds none.

    Two shapes, deliberately. The plane stores a decimal as its exact text
    (`lakehouse/schema.py` -- a price is money and float64 cannot hold 0.1),
    while a row this process built with `to_row` still holds the `Decimal`
    itself; one reader taking both is what lets two implementations of one
    protocol answer the same question the same way. `None` is a refusal rather
    than a zero: `consensus_mid` is null where fewer than two venues
    contributed, and a zero there would read as agreement.
    """
    value = row.get(field)
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        return Decimal(value)
    raise RowShape(f"{field!r} is {value!r}; a decimal column holds a price")


def select_consensus(
    rows: Sequence[dict[str, object]],
    *,
    asset: str,
    market_type: str,
    window_ns: int,
    at_ns: int | None,
) -> list[dict[str, object]]:
    """One asset's and market type's consensus rows in `(at - window, at]`.

    `at_ns` is the instant the chart asks about, and a bar whose consensus
    closes after it had not happened yet -- returning one would put the answer
    to a later question on an earlier chart (Principle I: no look-ahead, even
    where the later row exists and the earlier chart would rather have it).
    The window is left-open and right-closed, so a consensus taken exactly at
    the instant belongs to it; the same edge case the bars table reads.

    With no instant asked for, the effective one is the close of the latest
    stored bar, which is what "the latest closed bar" means for a table whose
    only clock is `bar_close_ns`.

    Refusal rows come back like any other. A bar with fewer than two venues is
    a row carrying its reason, because the chart's gap has to be able to say
    *why* there is no line there, and only the stored reason can say it.

    Ordered by the bar's close: a series the chart draws left to right.
    """
    series = [row for row in rows if row["asset"] == asset and row["market_type"] == market_type]
    if not series:
        return []
    if at_ns is None:
        at_ns = max(as_int(row, "bar_close_ns") for row in series)
    floor = at_ns - window_ns
    windowed = [row for row in series if floor < as_int(row, "bar_close_ns") <= at_ns]
    return sorted(windowed, key=lambda row: as_int(row, "bar_close_ns"))


def _mid_at_or_before(
    rows: Sequence[dict[str, object]], *, venue: str, symbol: str, at_ns: int
) -> Decimal | None:
    """The newest quote of one venue at or before `at_ns`, or none.

    Newest by `ts_ns` -- exchange time, the event a point-in-time read filters
    on. `ingest_ns` says when this process saw the quote and never decides what
    was knowable then (Principle II), which is the whole difference between
    "the venue's mid at the bar's close" and "the mid this path happened to
    have by the time the chart was drawn". A quote taken exactly at the close
    is available at it (`<=`), the spec's own edge case.
    """
    eligible = [
        row
        for row in rows
        if row["venue"] == venue and row["symbol"] == symbol and as_int(row, "ts_ns") <= at_ns
    ]
    if not eligible:
        return None
    latest = max(eligible, key=lambda row: as_int(row, "ts_ns"))
    return _stored_price(latest, "mid")


def select_venue_basis(
    consensus_rows: Sequence[dict[str, object]],
    quote_rows: Sequence[dict[str, object]],
    *,
    asset: str,
    market_type: str,
    venue: str,
    start_ns: int,
    end_ns: int,
) -> list[dict[str, object]]:
    """PRD §17.3's basis of the viewed venue to its own consensus, one point per bar.

        venue_basis_bps = 10000 * (mid_i / consensus_mid - 1)

    The arithmetic is `crossvenue_basis.venue_basis_bps`, the function the
    `FeatureSpec` registered under that name -- the formula is the PRD's and
    neither this read nor the route gets to restate it, least of all as
    `basis_bps`, which is the *derivatives* basis of a perpetual against spot
    ([[REQ-WP-030]], a different quantity answering to a different name).

    **Per market type.** The consensus filtered here is the consensus of the
    market type the viewed venue belongs to: spot venues against spot, perps
    against perps, never blended (FR-006), or the number would move with the
    spot-perp basis for a reason that has nothing to do with the venue.

    **Silence, not zero.** A bar with no consensus row, a refused consensus
    (`consensus_mid` null), or no quote of this venue at or before its close is
    skipped: zero is the reading for a venue sitting exactly on the consensus,
    and a line drawn through zero across an hour of missing quotes would claim
    agreement where there was nothing to agree with. Absent points are how the
    pane knows to draw nothing there.

    Ordered by the bar's close, the way the series is drawn.
    """
    points: list[dict[str, object]] = []
    for row in consensus_rows:
        if row["asset"] != asset or row["market_type"] != market_type:
            continue
        bar_close_ns = as_int(row, "bar_close_ns")
        if not start_ns <= bar_close_ns <= end_ns:
            continue
        consensus_mid = _stored_price(row, "consensus_mid")
        if consensus_mid is None:
            continue
        # The consensus table is keyed by the asset and the quotes table by
        # the venue's symbol; for every market this API serves the two are the
        # same string (`BTCUSDT`), which is why the asset is what the viewed
        # venue's quote is looked up under.
        mid = _mid_at_or_before(quote_rows, venue=venue, symbol=asset, at_ns=bar_close_ns)
        if mid is None:
            continue
        points.append(
            {
                "bar_close_ns": bar_close_ns,
                "venue_basis_bps": venue_basis_bps(mid, consensus_mid),
            }
        )
    points.sort(key=lambda point: as_int(point, "bar_close_ns"))
    return points


@dataclass
class InMemoryRepository:
    """Everything the process has seen, and nothing from before it started.

    Not a deployable store and should not be mistaken for one: a restart loses
    all of it. That is acceptable only while nothing else persists either --
    ADR-019 is the record that storage is owed, not optional.
    """

    _markets: dict[tuple[str, str], Market] = field(default_factory=dict)
    _confirmed: list[ConfirmedExtremum] = field(default_factory=list)
    _candidates: list[ExtremumCandidate] = field(default_factory=list)
    _bars: list[Bar] = field(default_factory=list)
    _snapshots: dict[tuple[str, str, int], list[ChannelSnapshot]] = field(default_factory=dict)
    _features: dict[tuple[str, str, int], list[FeaturePoint]] = field(default_factory=dict)
    _signals: list[Candidate] = field(default_factory=list)
    _depth_bands: list[DepthBand] = field(default_factory=list)
    _bin_rows: list[dict[str, object]] = field(default_factory=list)
    #: The consensus table's rows, one per (asset, market type, bar close),
    #: written by the consensus pass and read by the chart's consensus layer
    #: ([[REQ-WP-091]]).
    _consensus_rows: list[dict[str, object]] = field(default_factory=list)
    #: The quotes table's rows: a venue's top-of-book, one per observation.
    _quote_rows: list[dict[str, object]] = field(default_factory=list)
    #: One score per market, its latest. A history of scores is section 29's
    #: storage work; overwriting is honest about what this holds.
    _scores: dict[tuple[str, str], ScoredSetup] = field(default_factory=dict)

    # --- writing, for the pipeline and the tests ---

    def add_market(
        self,
        *,
        venue: str,
        symbol: str,
        market_type: str,
        instrument: Instrument | None = None,
    ) -> None:
        # Keyed rather than appended: a market described twice is one market
        # described twice, and the lakehouse repository reads it the same way.
        self._markets[venue, symbol] = Market(
            venue=venue, symbol=symbol, market_type=market_type, instrument=instrument
        )

    def add_bar(self, bar: Bar) -> None:
        self._bars.append(bar)

    def add_confirmed_extremum(self, extremum: ConfirmedExtremum) -> None:
        self._confirmed.append(extremum)

    def add_extremum_candidate(self, candidate: ExtremumCandidate) -> None:
        self._candidates.append(candidate)

    def add_channel_snapshot(
        self, *, venue: str, symbol: str, timeframe_ns: int, snapshot: ChannelSnapshot
    ) -> None:
        self._snapshots.setdefault((venue, symbol, timeframe_ns), []).append(snapshot)

    def add_feature_snapshot(
        self,
        *,
        venue: str,
        symbol: str,
        timeframe_ns: int,
        at_ns: int,
        values: dict[str, float],
    ) -> None:
        self._features.setdefault((venue, symbol, timeframe_ns), []).append(
            FeaturePoint(at_ns=at_ns, values=values)
        )

    def add_signal(self, candidate: Candidate) -> None:
        self._signals.append(candidate)

    def add_setup_score(
        self,
        *,
        venue: str,
        symbol: str,
        score: SignalScore,
        feature_snapshot: dict[str, float],
        model_version: str,
        liquidity_factor: float = 1.0,
        novelty_factor: float = 1.0,
    ) -> None:
        self._scores[(venue, symbol)] = ScoredSetup(
            venue=venue,
            symbol=symbol,
            score=score,
            feature_snapshot=dict(feature_snapshot),
            model_version=model_version,
            liquidity_factor=liquidity_factor,
            novelty_factor=novelty_factor,
        )

    # --- reading ---

    def extrema(
        self,
        *,
        instrument_id: str,
        timeframe_ns: int,
        as_of_ns: int | None = None,
    ) -> Extrema:
        """Turns knowable as of `as_of_ns`, in the shape the chart draws them.

        `as_of_ns` filters on when each became knowable -- `known_at_ns` for a
        confirmation, `observed_at_ns` for a candidate -- never on when the turn
        itself happened. That is PRD section 45's Phase 1A acceptance, and it is
        a knowledge filter rather than a window.
        """
        confirmed = [
            e
            for e in self._confirmed
            if e.instrument_id == instrument_id
            and e.timeframe_ns == timeframe_ns
            and (as_of_ns is None or e.known_at_ns <= as_of_ns)
        ]
        candidates = [
            c
            for c in self._candidates
            if c.instrument_id == instrument_id
            and c.timeframe_ns == timeframe_ns
            and (as_of_ns is None or c.observed_at_ns <= as_of_ns)
        ]
        return Extrema(
            confirmed=sorted(confirmed, key=lambda e: e.extremum_time_ns),
            candidates=sorted(candidates, key=lambda c: c.candidate_time_ns),
        )

    def markets(self, *, venue: str | None = None, market_type: str | None = None) -> list[Market]:
        return [
            m
            for m in self._markets.values()
            if (venue is None or m.venue == venue)
            and (market_type is None or m.market_type == market_type)
        ]

    def setup_score(self, *, venue: str, symbol: str) -> ScoredSetup | None:
        return self._scores.get((venue, symbol))

    def bars(
        self,
        *,
        venue: str,
        symbol: str,
        timeframe_ns: int,
        start_ns: int | None = None,
        end_ns: int | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        matched = sorted(
            (
                b
                for b in self._bars
                if b.venue == venue
                and b.symbol == symbol
                and b.timeframe_ns == timeframe_ns
                and (start_ns is None or b.close_time_ns >= start_ns)
                and (end_ns is None or b.close_time_ns <= end_ns)
            ),
            key=lambda b: b.close_time_ns,
        )
        # The most recent that fit, not the first: a chart opening on a symbol
        # wants the end of the series, and the oldest N would look like a
        # stalled feed.
        return matched[-limit:] if limit is not None else matched

    def channel_snapshot_at(
        self, *, venue: str, symbol: str, timeframe_ns: int, at_ns: int
    ) -> ChannelSnapshot | None:
        """The latest snapshot at or before `at_ns` -- never a later one.

        FR-017 lives here. A snapshot taken after the requested instant is
        exactly the hindsight PRD section 27.5 exists to keep out of the view.
        """
        stored = self._snapshots.get((venue, symbol, timeframe_ns), [])
        eligible = [s for s in stored if s.as_of_ns <= at_ns]
        return max(eligible, key=lambda s: s.as_of_ns) if eligible else None

    def feature_points(
        self, *, venue: str, symbol: str, timeframe_ns: int, start_ns: int, end_ns: int
    ) -> list[FeaturePoint]:
        stored = self._features.get((venue, symbol, timeframe_ns), [])
        return sorted((p for p in stored if start_ns <= p.at_ns <= end_ns), key=lambda p: p.at_ns)

    def signals(
        self,
        *,
        symbol: str | None = None,
        timeframe_ns: int | None = None,
        status: str | None = None,
        start_ns: int | None = None,
        end_ns: int | None = None,
    ) -> list[Candidate]:
        return sorted(
            (
                c
                for c in self._signals
                if (symbol is None or c.symbol == symbol)
                and (timeframe_ns is None or c.timeframe_ns == timeframe_ns)
                and (status is None or c.state.value == status)
                and (start_ns is None or c.opened_at_ns >= start_ns)
                and (end_ns is None or c.opened_at_ns <= end_ns)
            ),
            key=lambda c: c.opened_at_ns,
        )

    def signal(self, signal_id: uuid.UUID) -> Candidate | None:
        for c in self._signals:
            if signal_id_for(c) == signal_id:
                return c
        return None

    def add_bin_block(self, block: BinBlock) -> None:
        self._bin_rows.extend(to_rows(block))

    def volume_bins(
        self, *, venue: str, symbol: str, as_of_ns: int | None, window_ns: int
    ) -> BinsRead:
        return select_bins(
            self._bin_rows, venue=venue, symbol=symbol, as_of_ns=as_of_ns, window_ns=window_ns
        )

    def add_depth_band(self, band: DepthBand) -> None:
        self._depth_bands.append(band)

    def dex_depth_at(self, *, chain_id: int, pool: str, at_ns: int) -> list[DepthBand]:
        """The most recent curve at or before `at_ns`, as the lakehouse one does.

        The same reading deliberately: two implementations of one protocol that
        disagreed about "as of" would make the API's answer depend on how it was
        wired, which is the kind of difference nobody finds until a backtest and
        a live chart disagree.
        """
        eligible = [
            band
            for band in self._depth_bands
            if band.chain_id == chain_id and band.pool == pool and band.state_time_ns <= at_ns
        ]
        if not eligible:
            return []
        newest = max(band.state_time_ns for band in eligible)
        return [band for band in eligible if band.state_time_ns == newest]

    def add_consensus(self, consensus: Consensus) -> None:
        self._consensus_rows.append(consensus_to_row(consensus))

    def get_consensus(
        self,
        *,
        asset: str,
        market_type: str,
        timeframe_ns: int,
        window_ns: int,
        at_ns: int | None,
    ) -> list[dict[str, object]]:
        """The consensus layer's rows, never one closed after `at_ns` (FR-017).

        `timeframe_ns` is the caller's bar width and does not filter here: the
        consensus table is keyed by `(asset, market_type, bar_close_ns)` and
        carries no timeframe column, one consensus being written per asset and
        market type per bar close. It stays on the signature because the read
        has to say which series it was asked about, and because a future
        per-timeframe table must not have to change this call to use it.
        """
        return select_consensus(
            self._consensus_rows,
            asset=asset,
            market_type=market_type,
            window_ns=window_ns,
            at_ns=at_ns,
        )

    def add_quote(self, quote: Quote) -> None:
        self._quote_rows.append(quote_to_row(quote))

    def get_venue_basis(
        self,
        *,
        asset: str,
        market_type: str,
        venue: str,
        timeframe_ns: int,
        start_ns: int,
        end_ns: int,
    ) -> list[dict[str, object]]:
        """The viewed venue's `venue_basis_bps` per bar, as of each bar's close.

        Read rather than computed: the consensus and the quote at the close are
        what the pass stored, so live and replay get the same number from the
        same rows (Principle VII). `timeframe_ns` is carried as the consensus
        read carries it -- see `get_consensus`.
        """
        return select_venue_basis(
            self._consensus_rows,
            self._quote_rows,
            asset=asset,
            market_type=market_type,
            venue=venue,
            start_ns=start_ns,
            end_ns=end_ns,
        )
