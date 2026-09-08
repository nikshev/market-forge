"""What goes over the wire.

# @trace: REQ-API-001

Separate from the domain models deliberately. A wire format that *is* a domain
model makes every domain change an API change, and PRD section 0.5's
immutability guarantees are about stored records, not about JSON.

Decimals become strings. A price that round-trips through a JSON float is a
different price, and the whole point of ADR-003's `Decimal` at the boundary was
to stop that happening once.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from channelflow.api.repositories import FeaturePoint, Market
from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.signals import Candidate


class MarketOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue: str
    symbol: str
    market_type: str

    @classmethod
    def of(cls, market: Market) -> MarketOut:
        return cls(venue=market.venue, symbol=market.symbol, market_type=market.market_type)


class BarOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    open_time_ns: int
    close_time_ns: int
    open: str
    high: str
    low: str
    close: str
    volume_base: str
    is_final: bool

    @classmethod
    def of(cls, bar: Bar) -> BarOut:
        return cls(
            open_time_ns=bar.open_time_ns,
            close_time_ns=bar.close_time_ns,
            open=str(bar.open),
            high=str(bar.high),
            low=str(bar.low),
            close=str(bar.close),
            volume_base=str(bar.volume_base),
            is_final=bar.is_final,
        )


class ChannelOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of_ns: int
    model_name: str
    model_version: str
    lookback: int
    center_now: float
    upper_now: float
    lower_now: float
    slope_normalized: float
    width_pct: float
    quality_score: float
    source_max_event_time_ns: int
    #: Which of PRD section 27.5's two views this is. Carried in the payload,
    #: not only in the request, so a cached or forwarded response can still say
    #: what it is (ADR-020).
    mode: str

    @classmethod
    def of(cls, snapshot: ChannelSnapshot, *, mode: str) -> ChannelOut:
        return cls(
            as_of_ns=snapshot.as_of_ns,
            model_name=snapshot.model_name,
            model_version=snapshot.model_version,
            lookback=snapshot.lookback,
            center_now=snapshot.center_now,
            upper_now=snapshot.upper_now,
            lower_now=snapshot.lower_now,
            slope_normalized=snapshot.slope_normalized,
            width_pct=snapshot.width_pct,
            quality_score=snapshot.quality.score,
            source_max_event_time_ns=snapshot.source_max_event_time_ns,
            mode=mode,
        )


class SignalOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: uuid.UUID
    venue: str
    symbol: str
    timeframe_ns: int
    direction: str
    boundary: str
    state: str
    opened_at_ns: int

    @classmethod
    def of(cls, candidate: Candidate, *, signal_id: uuid.UUID) -> SignalOut:
        return cls(
            signal_id=signal_id,
            venue=candidate.venue,
            symbol=candidate.symbol,
            timeframe_ns=candidate.timeframe_ns,
            direction=candidate.direction,
            boundary=candidate.boundary,
            state=candidate.state.value,
            opened_at_ns=candidate.opened_at_ns,
        )


class TransitionOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_state: str
    to_state: str
    bar_close_time_ns: int
    reason: str


class SignalDetailOut(BaseModel):
    """PRD section 28.6.

    `outcome` is its own field and is never merged into `decision`. Section
    27.4 requires the later outcome "visually separated so it cannot be
    confused with information available at signal time" -- a response that
    merged them would make that impossible for any UI, not only this one.
    """

    model_config = ConfigDict(frozen=True)

    decision: SignalOut
    history: tuple[TransitionOut, ...]
    channel: ChannelOut | None
    features: dict[str, float]
    outcome: dict[str, str] | None


class FeaturePointOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    at_ns: int
    values: dict[str, float]

    @classmethod
    def of(cls, point: FeaturePoint) -> FeaturePointOut:
        return cls(at_ns=point.at_ns, values=point.values)


class MarketsResponse(BaseModel):
    markets: tuple[MarketOut, ...]


class BarsResponse(BaseModel):
    bars: tuple[BarOut, ...]


class SignalsResponse(BaseModel):
    signals: tuple[SignalOut, ...]


class FeatureSnapshotResponse(BaseModel):
    at_ns: int
    values: dict[str, float]


class FeatureSeriesResponse(BaseModel):
    points: tuple[FeaturePointOut, ...]
