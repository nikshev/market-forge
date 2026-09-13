"""What goes over the wire.

# @trace: REQ-API-001
# @trace: REQ-US-001
# @trace: REQ-US-004
# @trace: REQ-US-003

Separate from the domain models deliberately. A wire format that *is* a domain
model makes every domain change an API change, and PRD section 0.5's
immutability guarantees are about stored records, not about JSON.

Decimals become strings. A price that round-trips through a JSON float is a
different price, and the whole point of ADR-003's `Decimal` at the boundary was
to stop that happening once.

**Timestamps become strings for the same reason and a worse one** ([[REQ-WP-061]]).
A nanosecond count since the epoch is around 1.8e18 and JavaScript's
`Number.MAX_SAFE_INTEGER` is 9.0e15, so at that magnitude the representable
values are 256 nanoseconds apart: a mark read as a number is rounded, and two
marks 100 nanoseconds apart compare equal. PRD §13A.1 requires
`extremum_time != known_at` and the comparisons that enforce it are exactly the
ones the rounding reaches, always in the permissive direction.

Durations are not converted. `timeframe_ns` and `hindsight_ns` are bounded by the
timeframes this system supports -- a week is 6.0e14, well inside the safe range --
and converting them would obscure which fields had a reason.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from channelflow.api.channels import AS_SEEN_THEN, CURRENT_REFIT
from channelflow.api.comparison import ChannelComparison
from channelflow.api.repositories import FeaturePoint, Market, ScoredSetup
from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.extrema.models import ConfirmedExtremum, ExtremumCandidate
from channelflow.scoring import Explanation, Factor
from channelflow.signals import Candidate
from channelflow.tables.dex_depth import DepthBand

#: A nanosecond timestamp on the wire: digits, as a string.
#:
#: The pattern is the contract rather than a convention. It refuses `""`, which
#: `BigInt("")` in a browser turns into `0n` -- the epoch, which is positive,
#: ordered and believable, and would place a bar at the beginning of time rather
#: than failing. It also refuses a fractional or negative string, which
#: `BigInt` throws on and which a reader would otherwise meet as a crash in a
#: render instead of a stated load failure.
WireTime = Annotated[str, StringConstraints(pattern=r"^(?:0|[1-9][0-9]*)$")]


class MarketOut(BaseModel):
    """A market, and its latest score when it has one.

    The three score fields are `None` rather than zero for a market nobody has
    scored. A zero would say the setup was examined and found worthless, which
    is a different claim from "not examined" -- and the list is sorted on it.
    """

    model_config = ConfigDict(frozen=True)

    venue: str
    symbol: str
    market_type: str
    setup_score: float | None = None
    rank_score: float | None = None
    #: The share of PRD section 22.1's 100 points any family could speak to.
    confidence: float | None = None

    @classmethod
    def of(
        cls, market: Market, *, scored: ScoredSetup | None = None, rank_score: float | None = None
    ) -> MarketOut:
        return cls(
            venue=market.venue,
            symbol=market.symbol,
            market_type=market.market_type,
            setup_score=None if scored is None else scored.score.final,
            rank_score=rank_score,
            confidence=None if scored is None else scored.score.confidence,
        )


class BarOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    open_time_ns: WireTime
    close_time_ns: WireTime
    open: str
    high: str
    low: str
    close: str
    volume_base: str
    is_final: bool

    @classmethod
    def of(cls, bar: Bar) -> BarOut:
        return cls(
            open_time_ns=str(bar.open_time_ns),
            close_time_ns=str(bar.close_time_ns),
            open=str(bar.open),
            high=str(bar.high),
            low=str(bar.low),
            close=str(bar.close),
            volume_base=str(bar.volume_base),
            is_final=bar.is_final,
        )


class ChannelOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of_ns: WireTime
    model_name: str
    model_version: str
    lookback: int
    center_now: float
    upper_now: float
    lower_now: float
    slope_normalized: float
    width_pct: float
    quality_score: float
    source_max_event_time_ns: WireTime
    #: Which of PRD section 27.5's two views this is. Carried in the payload,
    #: not only in the request, so a cached or forwarded response can still say
    #: what it is (ADR-020).
    mode: str

    @classmethod
    def of(cls, snapshot: ChannelSnapshot, *, mode: str) -> ChannelOut:
        return cls(
            as_of_ns=str(snapshot.as_of_ns),
            model_name=snapshot.model_name,
            model_version=snapshot.model_version,
            lookback=snapshot.lookback,
            center_now=snapshot.center_now,
            upper_now=snapshot.upper_now,
            lower_now=snapshot.lower_now,
            slope_normalized=snapshot.slope_normalized,
            width_pct=snapshot.width_pct,
            quality_score=snapshot.quality.score,
            source_max_event_time_ns=str(snapshot.source_max_event_time_ns),
            mode=mode,
        )


class ChannelDifferenceOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    center: float
    upper: float
    lower: float
    slope: float
    width_pct: float
    quality: float
    #: `None` when the stored channel had no width. See `comparison.py`.
    center_in_widths: float | None


class ChannelComparisonOut(BaseModel):
    """PRD section 27.5's two views at once, and what moved (REQ-US-003)."""

    model_config = ConfigDict(frozen=True)

    as_seen_then: ChannelOut
    current_refit: ChannelOut
    difference: ChannelDifferenceOut
    #: How far past the compared instant the refit could see.
    hindsight_ns: int
    #: Always true. A channel fitted over later bars has seen what followed.
    research_only: bool

    @classmethod
    def of(cls, comparison: ChannelComparison) -> ChannelComparisonOut:
        return cls(
            as_seen_then=ChannelOut.of(comparison.as_seen_then, mode=AS_SEEN_THEN),
            current_refit=ChannelOut.of(comparison.current_refit, mode=CURRENT_REFIT),
            difference=ChannelDifferenceOut(
                center=comparison.difference.center,
                upper=comparison.difference.upper,
                lower=comparison.difference.lower,
                slope=comparison.difference.slope,
                width_pct=comparison.difference.width_pct,
                quality=comparison.difference.quality,
                center_in_widths=comparison.difference.center_in_widths,
            ),
            hindsight_ns=comparison.hindsight_ns,
            research_only=comparison.research_only,
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
    opened_at_ns: WireTime

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
            opened_at_ns=str(candidate.opened_at_ns),
        )


class TransitionOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_state: str
    to_state: str
    bar_close_time_ns: WireTime
    reason: str


class FactorOut(BaseModel):
    """One group's contribution, as PRD section 22.4's panel needs it."""

    model_config = ConfigDict(frozen=True)

    group: str
    value: float
    cap: float
    #: The contribution as a share of its own cap. 26 of 30 and 8 of 10 are both
    #: strong; 4 of 20 is weak while being the larger number.
    share: float
    names: tuple[str, ...]

    @classmethod
    def of(cls, factor: Factor) -> FactorOut:
        return cls(
            group=factor.group.value,
            value=factor.value,
            cap=factor.cap,
            share=factor.share,
            names=factor.names,
        )


class ExplanationOut(BaseModel):
    """PRD section 22.4's five items.

    The outcome is deliberately not among them. Section 27.4 requires the later
    outcome "visually separated so it cannot be confused with information
    available at signal time", and nesting it here would make that impossible
    for any UI, not only this one.
    """

    model_config = ConfigDict(frozen=True)

    top_positive: tuple[FactorOut, ...]
    top_negative: tuple[FactorOut, ...]
    missing: tuple[str, ...]
    feature_snapshot: dict[str, float]
    model_version: str
    factors: tuple[FactorOut, ...]

    @classmethod
    def of(cls, explanation: Explanation) -> ExplanationOut:
        return cls(
            top_positive=tuple(FactorOut.of(f) for f in explanation.top_positive),
            top_negative=tuple(FactorOut.of(f) for f in explanation.top_negative),
            missing=tuple(g.value for g in explanation.missing),
            feature_snapshot=explanation.feature_snapshot,
            model_version=explanation.model_version,
            factors=tuple(FactorOut.of(f) for f in explanation.factors),
        )


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
    #: `None` for a signal produced before it was scored, or one nobody scored.
    #: The rest of the detail still returns: an explanation is an addition to a
    #: signal, not a precondition for reading one.
    explanation: ExplanationOut | None = None


class FeaturePointOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    at_ns: WireTime
    values: dict[str, float]

    @classmethod
    def of(cls, point: FeaturePoint) -> FeaturePointOut:
        return cls(at_ns=str(point.at_ns), values=point.values)


class MarketsResponse(BaseModel):
    markets: tuple[MarketOut, ...]


class ConfirmedExtremumOut(BaseModel):
    """A turn, when it happened, and when it became knowable.

    Both instants travel, because they mean different things and a client that
    received only one would have to guess which ([[REQ-WP-028]]).
    """

    model_config = ConfigDict(frozen=True)

    extremum_id: str
    extremum_type: str
    #: Where the marker goes.
    extremum_time_ns: WireTime
    #: The earliest instant this may be shown at all.
    known_at_ns: WireTime
    price: str
    confirmation_lag_bars: int
    prominence_bps: float | None
    source_candidate_id: str | None

    @classmethod
    def of(cls, extremum: ConfirmedExtremum) -> ConfirmedExtremumOut:
        return cls(
            extremum_id=str(extremum.extremum_id),
            extremum_type=extremum.extremum_type,
            extremum_time_ns=str(extremum.extremum_time_ns),
            known_at_ns=str(extremum.known_at_ns),
            # A string, like every other price on the wire: a Decimal through a
            # JSON float is a different price.
            price=str(extremum.price),
            confirmation_lag_bars=extremum.confirmation_lag_bars,
            prominence_bps=extremum.prominence_bps,
            source_candidate_id=(
                None if extremum.source_candidate_id is None else str(extremum.source_candidate_id)
            ),
        )


class ExtremumCandidateOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: str
    candidate_type: str
    candidate_time_ns: WireTime
    observed_at_ns: WireTime
    price: str
    structural_score: float

    @classmethod
    def of(cls, candidate: ExtremumCandidate) -> ExtremumCandidateOut:
        return cls(
            candidate_id=str(candidate.candidate_id),
            candidate_type=candidate.candidate_type,
            candidate_time_ns=str(candidate.candidate_time_ns),
            observed_at_ns=str(candidate.observed_at_ns),
            price=str(candidate.price),
            structural_score=candidate.structural_score,
        )


class ExtremaResponse(BaseModel):
    """Kept apart on the wire, for the reason the repository keeps them apart:
    a candidate and a confirmation are different claims."""

    model_config = ConfigDict(frozen=True)

    confirmed: tuple[ConfirmedExtremumOut, ...]
    candidates: tuple[ExtremumCandidateOut, ...]


class BarsResponse(BaseModel):
    bars: tuple[BarOut, ...]


class SignalsResponse(BaseModel):
    signals: tuple[SignalOut, ...]


class FeatureSnapshotResponse(BaseModel):
    at_ns: WireTime
    values: dict[str, float]


class FeatureSeriesResponse(BaseModel):
    points: tuple[FeaturePointOut, ...]


class DexDepthBandOut(BaseModel):
    """One band of PRD §18.12.3's curve, as the API serves it.

    Amounts and prices are strings, as bars' are: they are money, and JSON's
    number is a float64 that cannot hold 0.1.

    **`reachable` is the field a reader must consult first**, and it is here
    rather than being folded into the amounts. When it is false the amounts
    describe exhausting the known liquidity rather than reaching the target
    ([[ADR-036]]), and a client that saw only a band and a notional would draw a
    pool too thin to move 100 bps as a pool where 100 bps is cheap.
    """

    model_config = ConfigDict(frozen=True)

    side: str
    target_bps: str
    reachable: bool
    #: How far the book actually went. Equal to `target_bps` when reached, and
    #: the reason the unreached row is worth drawing at all.
    reached_bps: str
    amount0: str
    amount1: str
    reference_price: str
    ticks_crossed: int
    reason: str

    @classmethod
    def of(cls, band: DepthBand) -> DexDepthBandOut:
        return cls(
            side=band.side,
            target_bps=str(band.target_bps),
            reachable=band.reachable,
            reached_bps=str(band.reached_bps),
            amount0=str(band.amount0),
            amount1=str(band.amount1),
            reference_price=str(band.reference_price),
            ticks_crossed=band.ticks_crossed,
            reason=band.reason,
        )


class DexDepthResponse(BaseModel):
    """A pool's curve at an instant, and which instant that was.

    `state_time_ns` is the curve's own time rather than the requested one. They
    differ whenever the most recent curve predates the chart's cursor, and a
    reader who could not tell would have no way to know how stale the overlay is.

    `None` when the pool has no curve at or before the instant -- distinct from
    an empty band list, which nothing produces: a curve is written whole.
    """

    model_config = ConfigDict(frozen=True)

    chain_id: int
    pool: str
    #: Times cross the wire as strings, for the same reason prices do: JSON's
    #: number is a float64. A nanosecond epoch timestamp is around 1.7e18 and
    #: `Number.MAX_SAFE_INTEGER` is 9.0e15, so a browser reading one as a number
    #: quantises it to the nearest 256 nanoseconds and cannot represent the
    #: value it was sent. Measured, and true of every `_ns` field this API
    #: already serves -- see [[REQ-WP-054]]'s open question.
    requested_at_ns: str
    state_time_ns: str | None
    bands: tuple[DexDepthBandOut, ...]
