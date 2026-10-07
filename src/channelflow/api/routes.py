"""PRD section 28's endpoints.

# @trace: REQ-API-001
# @trace: REQ-US-001
# @trace: REQ-US-004
# @trace: REQ-US-003
# @trace: REQ-WP-074
# @trace: REQ-WP-091

Read-only, every one of them: Principle IX says phases 1-3 form signals and
alerts and the system does not open positions, and an API with no write path
cannot be talked into one.

The handlers read and shape. The only computation anywhere here is section
27.5's explicit refit, which lives in `channels.py` and calls REQ-WP-006's
fitter rather than a copy of it (FR-010).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping

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
    ConsensusBarOut,
    ConsensusResponse,
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
    TimeframeOut,
    TimeframesResponse,
    TransitionOut,
    VolumeProfileOut,
)
from channelflow.api.volume_profile import (
    WINDOWS,
    ProfileUnavailable,
    ProfileWindow,
    windowed_profile,
)
from channelflow.scoring import explain
from channelflow.tables.rows import as_float, as_int
from channelflow.timeframes import offered

router = APIRouter(prefix="/api/v1")


def _repository(request: Request) -> Repository:
    return request.app.state.repository  # type: ignore[no-any-return]


def _market_type(repository: Repository, *, venue: str, symbol: str) -> str | None:
    """The market type the registry gives this venue's symbol, or nothing.

    The consensus table is keyed by `(asset, market_type)`
    (`tables/consensus.py`), while the chart asks for a `venue` and a
    `symbol`. For every market this API serves the asset *is* the symbol --
    `repositories.select_venue_basis` reads it that way too -- and the market
    type is what the registry says, never an assumption of `"spot"`: FR-006
    keeps spot and perpetual consensuses apart, and guessing the type here is
    how a spot mid would end up measured against a perpetual's consensus.

    `None` is "no market row names this symbol", which every caller below
    turns into a stated refusal rather than a default.
    """
    for market in repository.markets(venue=venue, market_type=None):
        if market.symbol == symbol:
            return market.market_type
    return None


@router.get("/timeframes", response_model=TimeframesResponse)
def get_timeframes(request: Request) -> TimeframesResponse:
    """The timeframes this deployment can serve (REQ-WP-074).

    Computed from the same configuration the resampler reads, plus the source
    timeframe the ingest daemon always writes. The union lives in
    `timeframes.offered` rather than here, so a second view of the set cannot
    disagree with this one.
    """
    configured = request.app.state.timeframes
    return TimeframesResponse(
        timeframes=tuple(
            TimeframeOut(token=tf.token, timeframe_ns=tf.ns) for tf in offered(configured)
        )
    )


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
    """The stored feature series for one market, with REQ-WP-091's basis merged in.

    The shape is the one the chart already calls: five query parameters and
    every point carrying all of its values (`apps/web/src/api.ts`'s
    `fetchFeatureSeries` sends exactly `venue`, `symbol`, `timeframe_ns`,
    `start_ns`, `end_ns`). **There is no `feature` parameter and none is
    added** -- a caller that sends one gets its request ignored, not a
    filter, because a required `feature` would break every existing caller of
    an endpoint that has always answered with the whole point.

    `venue_basis_bps` therefore arrives as one more key in `values`, at the
    bar closes the consensus pass stored it for, merged into the point that
    already closed then (or appended as a point of its own where the feature
    snapshots hold nothing at that instant).

    **Best effort, deliberately.** The basis is an enrichment of an endpoint
    that already answers: a venue no market row names, or a read that raises,
    leaves the plain series unchanged rather than turning a working chart into
    a 500 for an optional layer (REQ-WP-091, FR-003).
    """
    repository = _repository(request)
    points = [
        FeaturePointOut.of(p)
        for p in repository.feature_points(
            venue=venue, symbol=symbol, timeframe_ns=timeframe_ns, start_ns=start_ns, end_ns=end_ns
        )
    ]
    index = {int(point.at_ns): position for position, point in enumerate(points)}
    for row in _venue_basis_or_nothing(
        repository,
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        start_ns=start_ns,
        end_ns=end_ns,
    ):
        # The bar's close is the feature's instant: `FeaturePointOut.at_ns` and
        # the consensus row's `bar_close_ns` are the same moment under two
        # names, which is why they merge instead of sitting side by side.
        close_ns = as_int(row, "bar_close_ns")
        value = as_float(row, "venue_basis_bps")
        position = index.get(close_ns)
        if position is None:
            points.append(FeaturePointOut(at_ns=str(close_ns), values={"venue_basis_bps": value}))
            index[close_ns] = len(points) - 1
            continue
        existing = points[position]
        # A new model rather than a mutation: `FeaturePointOut` is frozen, and
        # rebuilding keeps every other value of that point exactly as the
        # stored snapshot wrote it.
        points[position] = FeaturePointOut(
            at_ns=existing.at_ns,
            values={**existing.values, "venue_basis_bps": value},
        )
    points.sort(key=lambda point: int(point.at_ns))
    return FeatureSeriesResponse(points=tuple(points))


def _venue_basis_or_nothing(
    repository: Repository,
    *,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    start_ns: int,
    end_ns: int,
) -> list[dict[str, object]]:
    """The viewed venue's `venue_basis_bps` rows, or none if this read cannot have them.

    `_market_type` returning nothing is not an error the caller should see --
    the series is still the series. A raised read is swallowed the same way,
    for the reason stated on `get_feature_series`: an optional enrichment may
    fail, the endpoint's own answer may not.
    """
    try:
        market_type = _market_type(repository, venue=venue, symbol=symbol)
        if market_type is None:
            return []
        return repository.get_venue_basis(
            asset=symbol,
            market_type=market_type,
            venue=venue,
            timeframe_ns=timeframe_ns,
            start_ns=start_ns,
            end_ns=end_ns,
        )
    except Exception:  # noqa: BLE001 -- deliberately total: see the docstring.
        return []


def _consensus_bar(row: Mapping[str, object]) -> ConsensusBarOut:
    """One stored consensus row as the wire shapes it.

    `consensus_mid` travels as the decimal text it was stored as -- a JSON
    number is a float64 and would lose the cents on the way out -- and stays
    `None` where the consensus was refused, so no reader can mistake a
    refusal for a price. An empty `refusal_reason` is the plane's "no
    refusal" (`tables/consensus.py`) and travels as `None`, the wire's.
    """
    mid = row.get("consensus_mid")
    reason = row.get("refusal_reason")
    return ConsensusBarOut(
        bar_close_ns=str(as_int(row, "bar_close_ns")),
        consensus_mid=None if mid is None else str(mid),
        venue_count=as_int(row, "venue_count"),
        refusal_reason=None if not reason else str(reason),
    )


@router.get("/consensus", response_model=ConsensusResponse)
def get_consensus(
    request: Request,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    # Refused by the request validator for any token outside `ProfileWindow`
    # (422), the same `Literal` `get_volume_profile` takes. `None` is only
    # "the caller named no window", which is refused below.
    window: ProfileWindow | None = None,
    at_ns: int | None = None,
) -> ConsensusResponse:
    """PRD §17.1's consensus mid, one row per bar, over a rolling window (REQ-WP-091).

    What the chart draws over its candles as an optional layer: the median of
    the venues that had a fresh mid at each bar's close, with `venue_count`
    behind it and -- where fewer than two venues contributed -- no mid at all
    but the stored `refusal_reason`, so a gap in the line says *why* rather
    than leaving a reader to guess between "one venue had a mid" and "no
    quote arrived" (FR-002).

    **Point-in-time (Principle I).** With `at_ns`, a bar that closed after
    that instant has not happened yet and stays out of the answer however the
    stored row would look -- `repositories.select_consensus` filters on
    `bar_close_ns <= at_ns` and this route adds nothing to it, so live and
    replay read one rule. Omitting `at_ns` asks about the latest stored bar's
    close, which is what "the latest" means for a table whose only clock is
    `bar_close_ns`, and the response says which instant it answered for.

    **Which consensus is meant comes from the registry, not the request.**
    The table is keyed by asset and market type, so `_market_type` decides it
    (FR-006: spot against spot, perps against perps, never blended). A symbol
    no market row names is a 404 saying so -- the convention
    `get_volume_profile` sets with `ProfileUnavailable` -- never an empty 200
    a chart would draw as a flat line at nothing; so is a window the stored
    rows never reach. The market lookup answers before the absent-`window`
    refusal below, so such a request is still told what is missing rather
    than only what it failed to say.
    """
    repository = _repository(request)
    market_type = _market_type(repository, venue=venue, symbol=symbol)
    if market_type is None:
        raise HTTPException(status_code=404, detail=f"unknown market: {venue} {symbol}")
    if window is None:
        raise HTTPException(status_code=422, detail="window is required: one of 4h, 24h, 7d")

    rows = repository.get_consensus(
        asset=symbol,
        market_type=market_type,
        timeframe_ns=timeframe_ns,
        window_ns=WINDOWS[window],
        at_ns=at_ns,
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail=f"no consensus for {venue} {symbol} in {window}"
        )

    # The instant the answer describes: the one asked about, or -- when none
    # was -- the close of the newest bar in it, which is the effective instant
    # `select_consensus` windows from. Never a clock reading: the same stored
    # rows answer a historical chart and a live one (Principle VII).
    effective_at_ns = (
        at_ns if at_ns is not None else max(as_int(row, "bar_close_ns") for row in rows)
    )
    return ConsensusResponse(
        consensus=tuple(_consensus_bar(row) for row in rows),
        window=window,
        at_ns=str(effective_at_ns),
    )


@router.get("/volume-profile", response_model=VolumeProfileOut)
def get_volume_profile(
    request: Request,
    venue: str,
    symbol: str,
    window: ProfileWindow,
    at_ns: int | None = None,
) -> VolumeProfileOut:
    """PRD section 14.1's volume profile over a rolling window, as of an instant (REQ-WP-089).

    Built from the price bins the ingest collects, over whole blocks closed at or before `at_ns`
    (the latest closed block when omitted). It says how much of its window the data covers: the bins
    exist only from the moment collection started, so a 24h profile from three hours of data reports
    three hours and `complete` false. With no bins at all the answer is a 404 with a reason, never
    an empty profile.
    """
    window_ns = WINDOWS[window]
    read = _repository(request).volume_bins(
        venue=venue, symbol=symbol, as_of_ns=at_ns, window_ns=window_ns
    )
    try:
        view = windowed_profile(read, window_ns=window_ns)
    except ProfileUnavailable as exc:
        raise HTTPException(
            status_code=404, detail=f"no price bins for {venue} {symbol}: {exc}"
        ) from exc
    return VolumeProfileOut.of(venue=venue, symbol=symbol, window=window, view=view)


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
