"""PRD section 28's endpoints.

# @trace: REQ-API-001
# @trace: REQ-US-001
# @trace: REQ-US-004
# @trace: REQ-US-003

Read-only, every one of them: Principle IX says phases 1-3 form signals and
alerts and the system does not open positions, and an API with no write path
cannot be talked into one.

The handlers read and shape. The only computation anywhere here is section
27.5's explicit refit, which lives in `channels.py` and calls REQ-WP-006's
fitter rather than a copy of it (FR-010).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from channelflow.alerting import signal_id_for
from channelflow.api.channels import ChannelUnavailable, channel_at
from channelflow.api.comparison import HindsightInverted, compare_channel
from channelflow.api.ranking import rank_markets
from channelflow.api.repositories import Repository
from channelflow.api.schemas import (
    BarOut,
    BarsResponse,
    ChannelComparisonOut,
    ChannelOut,
    ConfirmedExtremumOut,
    DexDepthBandOut,
    DexDepthResponse,
    ExplanationOut,
    ExtremaResponse,
    ExtremumCandidateOut,
    FeaturePointOut,
    FeatureSeriesResponse,
    FeatureSnapshotResponse,
    MarketOut,
    MarketsResponse,
    SignalDetailOut,
    SignalOut,
    SignalsResponse,
    TransitionOut,
)
from channelflow.scoring import explain

router = APIRouter(prefix="/api/v1")


def _repository(request: Request) -> Repository:
    return request.app.state.repository  # type: ignore[no-any-return]


@router.get("/markets", response_model=MarketsResponse)
def get_markets(
    request: Request,
    venue: str | None = None,
    market_type: str | None = None,
) -> MarketsResponse:
    """PRD section 28.1's list, ordered by section 43's rank score (REQ-US-001).

    Filters first, then order. A list ordered before filtering is ordered over
    rows the caller never sees, and the visible order is then whatever survived.

    An unscored market sorts after every scored one and carries nulls. Ranking
    it at zero would place it among the worst setups, saying it had been
    examined and found weak.
    """
    repository = _repository(request)
    found = repository.markets(venue=venue, market_type=market_type)
    return MarketsResponse(
        markets=tuple(
            MarketOut.of(r.market, scored=r.scored, rank_score=r.rank_score)
            for r in rank_markets(found, repository=repository)
        )
    )


@router.get("/bars", response_model=BarsResponse)
def get_bars(
    request: Request,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    start_ns: int | None = None,
    end_ns: int | None = None,
    limit: int | None = Query(default=None, ge=1, le=10_000),
) -> BarsResponse:
    found = _repository(request).bars(
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        start_ns=start_ns,
        end_ns=end_ns,
        limit=limit,
    )
    return BarsResponse(bars=tuple(BarOut.of(b) for b in found))


@router.get("/channels", response_model=ChannelOut)
def get_channel(
    request: Request,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    at_ns: int,
    # PRD section 28.3 and section 27.5: the default is the stored snapshot.
    # ADR-020 makes it the default here, in the chart, and when the value
    # cannot be parsed.
    as_seen_then: bool = True,
) -> ChannelOut:
    try:
        view = channel_at(
            _repository(request),
            venue=venue,
            symbol=symbol,
            timeframe_ns=timeframe_ns,
            at_ns=at_ns,
            as_seen_then=as_seen_then,
        )
    except ChannelUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChannelOut.of(view.snapshot, mode=view.mode)


@router.get("/channels/comparison", response_model=ChannelComparisonOut)
def get_channel_comparison(
    request: Request,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    at_ns: int,
    now_ns: int,
) -> ChannelComparisonOut:
    """PRD section 27.5's two views at once (REQ-US-003).

    `now_ns` is the caller's, not a clock reading: section 27.5 refits over
    "visible/current history", and what is visible is the reader's own window.
    """
    try:
        comparison = compare_channel(
            _repository(request),
            venue=venue,
            symbol=symbol,
            timeframe_ns=timeframe_ns,
            at_ns=at_ns,
            now_ns=now_ns,
        )
    except HindsightInverted as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ChannelUnavailable as exc:
        # 404: the pair of channels this names does not exist. Neither side can
        # be approximated -- a rebuilt AS-SEEN-THEN would measure nothing.
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChannelComparisonOut.of(comparison)


@router.get("/features/snapshot", response_model=FeatureSnapshotResponse)
def get_feature_snapshot(
    request: Request,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    at_ns: int,
) -> FeatureSnapshotResponse:
    points = _repository(request).feature_points(
        venue=venue, symbol=symbol, timeframe_ns=timeframe_ns, start_ns=0, end_ns=at_ns
    )
    latest = points[-1] if points else None
    return FeatureSnapshotResponse(
        at_ns=str(latest.at_ns if latest else at_ns),
        values=latest.values if latest else {},
    )


@router.get("/features/timeseries", response_model=FeatureSeriesResponse)
def get_feature_series(
    request: Request,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    start_ns: int,
    end_ns: int,
) -> FeatureSeriesResponse:
    points = _repository(request).feature_points(
        venue=venue, symbol=symbol, timeframe_ns=timeframe_ns, start_ns=start_ns, end_ns=end_ns
    )
    return FeatureSeriesResponse(points=tuple(FeaturePointOut.of(p) for p in points))


@router.get("/extrema", response_model=ExtremaResponse)
def get_extrema(
    request: Request,
    instrument_id: str,
    timeframe_ns: int,
    as_of_ns: int | None = None,
) -> ExtremaResponse:
    """Turns knowable as of an instant.

    `as_of_ns` is a knowledge filter, not a window: it drops turns that had not
    been confirmed by then. Omitting it asks for everything on record, which is
    what `CURRENT REFIT` wants -- PRD §27.5 makes that mode the place where
    repaint-like differences are meant to be visible ([[REQ-WP-028]]).
    """
    found = _repository(request).extrema(
        instrument_id=instrument_id, timeframe_ns=timeframe_ns, as_of_ns=as_of_ns
    )
    return ExtremaResponse(
        confirmed=tuple(ConfirmedExtremumOut.of(e) for e in found.confirmed),
        candidates=tuple(ExtremumCandidateOut.of(c) for c in found.candidates),
    )


@router.get("/signals", response_model=SignalsResponse)
def get_signals(
    request: Request,
    symbol: str | None = None,
    timeframe_ns: int | None = None,
    status: str | None = None,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> SignalsResponse:
    found = _repository(request).signals(
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        status=status,
        start_ns=start_ns,
        end_ns=end_ns,
    )
    return SignalsResponse(
        signals=tuple(SignalOut.of(c, signal_id=signal_id_for(c)) for c in found)
    )


@router.get("/signals/{signal_id}", response_model=SignalDetailOut)
def get_signal(request: Request, signal_id: uuid.UUID) -> SignalDetailOut:
    repository = _repository(request)
    candidate = repository.signal(signal_id)
    if candidate is None:
        # The one place a 404 is right: the id names a specific thing that does
        # not exist, rather than a query that matched nothing.
        raise HTTPException(status_code=404, detail=f"no signal {signal_id}")

    channel: ChannelOut | None = None
    try:
        view = channel_at(
            repository,
            venue=candidate.venue,
            symbol=candidate.symbol,
            timeframe_ns=candidate.timeframe_ns,
            at_ns=candidate.opened_at_ns,
            as_seen_then=True,
        )
        channel = ChannelOut.of(view.snapshot, mode=view.mode)
    except ChannelUnavailable:
        # An absent channel is not a flat one. The detail still returns; the
        # field is null and the UI says so.
        channel = None

    features = repository.feature_points(
        venue=candidate.venue,
        symbol=candidate.symbol,
        timeframe_ns=candidate.timeframe_ns,
        start_ns=0,
        end_ns=candidate.opened_at_ns,
    )
    scored = repository.setup_score(venue=candidate.venue, symbol=candidate.symbol)
    explanation = (
        None
        if scored is None
        else ExplanationOut.of(
            explain(
                scored.score,
                feature_snapshot=scored.feature_snapshot,
                model_version=scored.model_version,
            )
        )
    )
    return SignalDetailOut(
        explanation=explanation,
        decision=SignalOut.of(candidate, signal_id=signal_id),
        history=tuple(
            TransitionOut(
                from_state=t.from_state.value,
                to_state=t.to_state.value,
                bar_close_time_ns=str(t.bar_close_time_ns),
                reason=t.reason,
            )
            for t in candidate.history
        ),
        channel=channel,
        features=features[-1].values if features else {},
        # Nothing resolves a confirmation yet (ADR-010), so this is always
        # null today. It exists as its own field from the start because PRD
        # section 27.4 requires the later outcome to be separable from what was
        # known at signal time, and retrofitting that separation is how it gets
        # lost.
        outcome=None,
    )


@router.get("/dex/depth", response_model=DexDepthResponse)
def get_dex_depth(
    request: Request,
    chain_id: int,
    pool: str,
    at_ns: int,
) -> DexDepthResponse:
    """PRD §27.2's "DEX liquidity bands", as of an instant.

    `at_ns` is required and has no default. Defaulting it to now would make a
    historical chart quietly show the present, which is the look-ahead
    Principle I forbids arriving through the one door nobody guards -- and the
    caller who wants "now" can say so in a way the reader of the request can see.
    """
    bands = _repository(request).dex_depth_at(chain_id=chain_id, pool=pool, at_ns=at_ns)
    return DexDepthResponse(
        chain_id=chain_id,
        pool=pool,
        requested_at_ns=str(at_ns),
        # The curve's own time, not the requested one. They differ whenever the
        # most recent curve predates the cursor, and a reader who could not tell
        # would have no way to know how stale the overlay is.
        state_time_ns=str(bands[0].state_time_ns) if bands else None,
        bands=tuple(DexDepthBandOut.of(band) for band in bands),
    )
