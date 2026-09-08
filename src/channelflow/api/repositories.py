"""Where the API reads from.

# @trace: REQ-API-001

PRD section 29 defines the storage -- Iceberg on object storage, Pinot for HOT
serving, PostgreSQL for metadata. None of it is built, and REQ-WP-009's chart
cannot wait for it (ADR-019).

So the API depends on a protocol. The in-memory implementation below serves it
now; the durable one arrives with section 29 and replaces it without any
endpoint changing.

The protocol is also where the point-in-time rule lives. Every read takes its
bounds explicitly, so "never return data later than the instant asked for"
(FR-017) is a signature rather than something each route handler remembers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

#: Namespace for signal ids. Shared with REQ-WP-008 so an alert's deep link and
#: the API name the same signal -- a different namespace here would make every
#: link a 404 while looking entirely correct.
from channelflow.alerting import signal_id_for
from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.signals import Candidate


@dataclass(frozen=True)
class Market:
    venue: str
    symbol: str
    market_type: str


@dataclass(frozen=True)
class FeaturePoint:
    at_ns: int
    values: dict[str, float]


class Repository(Protocol):
    """What the API needs to be able to read."""

    def markets(self, *, venue: str | None, market_type: str | None) -> list[Market]: ...

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


@dataclass
class InMemoryRepository:
    """Everything the process has seen, and nothing from before it started.

    Not a deployable store and should not be mistaken for one: a restart loses
    all of it. That is acceptable only while nothing else persists either --
    ADR-019 is the record that storage is owed, not optional.
    """

    _markets: list[Market] = field(default_factory=list)
    _bars: list[Bar] = field(default_factory=list)
    _snapshots: dict[tuple[str, str, int], list[ChannelSnapshot]] = field(default_factory=dict)
    _features: dict[tuple[str, str, int], list[FeaturePoint]] = field(default_factory=dict)
    _signals: list[Candidate] = field(default_factory=list)

    # --- writing, for the pipeline and the tests ---

    def add_market(self, *, venue: str, symbol: str, market_type: str) -> None:
        self._markets.append(Market(venue=venue, symbol=symbol, market_type=market_type))

    def add_bar(self, bar: Bar) -> None:
        self._bars.append(bar)

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

    # --- reading ---

    def markets(self, *, venue: str | None = None, market_type: str | None = None) -> list[Market]:
        return [
            m
            for m in self._markets
            if (venue is None or m.venue == venue)
            and (market_type is None or m.market_type == market_type)
        ]

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
