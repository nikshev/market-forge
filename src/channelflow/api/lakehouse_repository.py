"""The API's reads, served from the canonical plane.

# @trace: REQ-STORE-002
# @trace: REQ-API-001

[[ADR-019]] made the API depend on a protocol rather than a database, with a
note saying the durable implementation "arrives with section 29 and replaces it
without any endpoint changing". [[REQ-STORE-001]] built the plane, [[REQ-TBL-001]]
put the first table on it, and this is the rest of them behind the same port.

**No endpoint changes, and that is testable rather than asserted.** The same
behavioural suite runs against both implementations, so "the in-memory one and
this one answer alike" is a fact the suite checks rather than a claim this
docstring makes.

Two behaviours are worth naming because they are where the two implementations
could most easily diverge:

- **A channel snapshot is never later than the instant asked for.** The API's
  FR-017. Here it is the plane's own point-in-time read plus a max, so the rule
  is enforced twice on the way out and cannot be lost by a query that forgot it.
- **A missing thing is `None`, not an empty one.** A market nobody scored and a
  market that scored zero are different facts; so are a signal that does not
  exist and one with no history.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from channelflow.api.repositories import FeaturePoint, Market, ScoredSetup
from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.domain import Instrument
from channelflow.lakehouse import ObjectStore, Table
from channelflow.scoring import SignalScore
from channelflow.signals import Candidate
from channelflow.tables import bars as bars_table
from channelflow.tables import channels as channels_table
from channelflow.tables import features as features_table
from channelflow.tables import signals as signals_table
from channelflow.tables.rows import as_float, as_int, as_str


@dataclass
class LakehouseRepository:
    """Everything the API reads, from PRD §29's canonical tables.

    The tables are built once from the store rather than per call: a `Table` is
    frozen and stateless, so holding one caches nothing -- it is a name, a schema
    and a store, and every read goes to the store.
    """

    store: ObjectStore

    _bars: Table = field(init=False)
    _channels: Table = field(init=False)
    _features: Table = field(init=False)
    _markets: Table = field(init=False)
    _scores: Table = field(init=False)
    _contributions: Table = field(init=False)
    _signals: Table = field(init=False)
    _transitions: Table = field(init=False)

    def __post_init__(self) -> None:
        self._bars = bars_table.table_for(self.store)
        self._channels = channels_table.table_for(self.store)
        self._features = features_table.features_table_for(self.store)
        self._markets = features_table.markets_table_for(self.store)
        self._scores = features_table.scores_table_for(self.store)
        self._contributions = features_table.contributions_table_for(self.store)
        self._signals = signals_table.table_for(self.store)
        self._transitions = signals_table.transitions_table_for(self.store)

    # --- writing, for the pipeline and the tests ---------------------------
    #
    # The in-memory repository's writers take one item at a time because it has
    # nowhere to buffer. These take one too, for the same signature, and each is
    # a commit -- which is right for a test and wrong for a backfill. A backfill
    # uses the table modules directly, where the batch is the unit.

    def add_market(
        self,
        *,
        venue: str,
        symbol: str,
        market_type: str,
        instrument: Instrument | None = None,
    ) -> None:
        if instrument is not None:
            self._markets.append([features_table.market_row(instrument)])
            return
        # No rules yet: the row still has to satisfy the schema, and every rule
        # column is written empty rather than zeroed. `instrument_from_row`
        # reads an empty tick size back as "no rules", which is what it is.
        self._markets.append(
            [
                {
                    "venue": venue,
                    "symbol": symbol,
                    "market_type": market_type,
                    "base_asset": "",
                    "quote_asset": "",
                    "tick_size": Decimal(0),
                    "step_size": Decimal(0),
                    "min_notional": Decimal(0),
                    "contract_size": "",
                    "status": "",
                }
            ]
        )

    def add_bar(self, bar: Bar) -> None:
        bars_table.write_bars(self._bars, [bar])

    def add_channel_snapshot(
        self, *, venue: str, symbol: str, timeframe_ns: int, snapshot: ChannelSnapshot
    ) -> None:
        self._channels.append(
            [channels_table.to_row(snapshot, venue=venue, symbol=symbol, timeframe_ns=timeframe_ns)]
        )

    def add_feature_snapshot(
        self,
        *,
        venue: str,
        symbol: str,
        timeframe_ns: int,
        at_ns: int,
        values: dict[str, float],
    ) -> None:
        rows = features_table.feature_rows(
            venue=venue,
            symbol=symbol,
            timeframe_ns=timeframe_ns,
            at_ns=at_ns,
            values=values,
        )
        if rows:
            self._features.append(rows)

    def add_signal(self, candidate: Candidate) -> None:
        signals_table.write_signals(self._signals, self._transitions, [candidate])

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
        as_of_ns: int = 0,
    ) -> None:
        core, contributions = features_table.score_rows(
            venue=venue,
            symbol=symbol,
            as_of_ns=as_of_ns,
            score=score,
            feature_snapshot=feature_snapshot,
            model_version=model_version,
            liquidity_factor=liquidity_factor,
            novelty_factor=novelty_factor,
        )
        if contributions:
            self._contributions.append(contributions)
        self._scores.append([core])

    # --- reading ------------------------------------------------------------

    def markets(self, *, venue: str | None = None, market_type: str | None = None) -> list[Market]:
        """One entry per market, latest row wins.

        The plane is append-only, so a market described twice is two rows. The
        later one is the amendment ([[ADR-056]]'s reasoning on the scores table,
        which reads the same way), and returning both would make a re-ingest
        look like a second venue.
        """
        latest: dict[tuple[str, str], Market] = {}
        for row in self._markets.read().to_pylist():
            if venue is not None and row["venue"] != venue:
                continue
            if market_type is not None and row["market_type"] != market_type:
                continue
            key = (as_str(row, "venue"), as_str(row, "symbol"))
            latest[key] = Market(
                venue=key[0],
                symbol=key[1],
                market_type=as_str(row, "market_type"),
                instrument=features_table.instrument_from_row(row),
            )
        return list(latest.values())

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
        matched = [
            bar
            for bar in bars_table.read_bars(
                self._bars, venue=venue, symbol=symbol, timeframe_ns=timeframe_ns
            )
            if (start_ns is None or bar.close_time_ns >= start_ns)
            and (end_ns is None or bar.close_time_ns <= end_ns)
        ]
        matched.sort(key=lambda bar: bar.close_time_ns)
        # The most recent that fit, not the first: a chart opening on a symbol
        # wants the end of the series, and the oldest N would look like a
        # stalled feed. Same reading as the in-memory repository, deliberately.
        return matched[-limit:] if limit is not None else matched

    def channel_snapshot_at(
        self, *, venue: str, symbol: str, timeframe_ns: int, at_ns: int
    ) -> ChannelSnapshot | None:
        return channels_table.latest_at(
            self._channels,
            venue=venue,
            symbol=symbol,
            timeframe_ns=timeframe_ns,
            at_ns=at_ns,
        )

    def feature_points(
        self, *, venue: str, symbol: str, timeframe_ns: int, start_ns: int, end_ns: int
    ) -> list[FeaturePoint]:
        """The long form gathered back into a point per instant.

        One row per feature is what makes a new feature a new row rather than a
        schema change (PRD §29.5); the API wants an instant's features together,
        so the grouping happens on the way out.
        """
        by_instant: dict[int, dict[str, float]] = {}
        for row in self._features.read().to_pylist():
            if (
                row["venue"] != venue
                or row["symbol"] != symbol
                or row["timeframe_ns"] != timeframe_ns
            ):
                continue
            at_ns = as_int(row, "at_ns")
            if not start_ns <= at_ns <= end_ns:
                continue
            by_instant.setdefault(at_ns, {})[as_str(row, "feature_name")] = as_float(row, "value")
        return [FeaturePoint(at_ns=at_ns, values=by_instant[at_ns]) for at_ns in sorted(by_instant)]

    def signals(
        self,
        *,
        symbol: str | None = None,
        timeframe_ns: int | None = None,
        status: str | None = None,
        start_ns: int | None = None,
        end_ns: int | None = None,
    ) -> list[Candidate]:
        return signals_table.read_signals(
            self._signals,
            self._transitions,
            symbol=symbol,
            timeframe_ns=timeframe_ns,
            state=status,
            start_ns=start_ns,
            end_ns=end_ns,
        )

    def signal(self, signal_id: uuid.UUID) -> Candidate | None:
        return signals_table.read_signal(self._signals, self._transitions, signal_id)

    def setup_score(self, *, venue: str, symbol: str) -> ScoredSetup | None:
        core = features_table.newest_score_row(
            self._scores.read().to_pylist(), venue=venue, symbol=symbol
        )
        if core is None:
            return None
        # The contributions of *this* score, joined on its own id rather than on
        # its instant. Two scores tie on `as_of_ns` whenever the caller does not
        # supply one, and joining on the instant gives a score every group any
        # of them had -- a score that does not add up, assembled from rows that
        # are each correct.
        identity = as_str(core, "score_id")
        contributions = [
            row
            for row in self._contributions.read().to_pylist()
            if as_str(row, "score_id") == identity
        ]
        return ScoredSetup(
            venue=venue,
            symbol=symbol,
            score=features_table.score_from_rows(core, contributions),
            feature_snapshot=features_table.snapshot_of(core),
            model_version=as_str(core, "model_version"),
            liquidity_factor=as_float(core, "liquidity_factor"),
            novelty_factor=as_float(core, "novelty_factor"),
        )
