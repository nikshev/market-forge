"""Both repositories answer alike (REQ-STORE-002, REQ-API-001).

[[ADR-019]] made the API depend on a protocol so the durable implementation
could replace the in-memory one "without any endpoint changing". That is only a
claim until something checks it, and checking it is what this module does: every
test here is parametrised over both implementations and asserts the same thing
of each.

A conformance suite rather than two suites, because two would drift. The first
divergence would be a behaviour one implementation has and the other does not,
and nothing would say which was right.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from decimal import Decimal

import pytest

from channelflow.alerting import signal_id_for
from channelflow.api import InMemoryRepository, LakehouseRepository
from channelflow.bars import Bar
from channelflow.channels import ChannelQuality, ChannelSnapshot
from channelflow.domain import Instrument
from channelflow.extrema.models import ConfirmedExtremum, ExtremumCandidate
from channelflow.lakehouse import Catalog
from channelflow.scoring import Group, GroupContribution, SignalScore
from channelflow.signals import Candidate, CandidateState, Transition

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1_788_838_800_000_000_000

Repo = InMemoryRepository | LakehouseRepository


def _in_memory(catalog: Catalog) -> Repo:
    # Takes the catalog it does not use, so both factories have one shape and
    # the fixture below needs no special case for either.
    return InMemoryRepository()


def _lakehouse(catalog: Catalog) -> Repo:
    return LakehouseRepository(catalog=catalog)


#: Both implementations, named so a failure says which one broke.
IMPLEMENTATIONS: list[Callable[[Catalog], Repo]] = [_in_memory, _lakehouse]
IDS = ["in_memory", "lakehouse"]


@pytest.fixture(params=IMPLEMENTATIONS, ids=IDS)
def repo(request: pytest.FixtureRequest, catalog: Catalog) -> Repo:
    factory: Callable[[Catalog], Repo] = request.param
    return factory(catalog)


def bar(index: int, *, price: str = "112000.10", symbol: str = "BTCUSDT") -> Bar:
    open_ns = BASE_NS + index * MINUTE_NS
    return Bar(
        venue="binance",
        symbol=symbol,
        timeframe_ns=MINUTE_NS,
        open_time_ns=open_ns,
        close_time_ns=open_ns + MINUTE_NS,
        open=Decimal(price),
        high=Decimal(price) + Decimal("5"),
        low=Decimal(price) - Decimal("5"),
        close=Decimal(price) + Decimal("1"),
        volume_base=Decimal("1.5"),
        volume_quote=Decimal("168000.15"),
        trade_count=42,
        aggressive_buy_base=Decimal("0.9"),
        aggressive_sell_base=Decimal("0.6"),
        delta_base=Decimal("0.3"),
        vwap=Decimal("112000.55"),
        high_time_ns=open_ns + 10,
        low_time_ns=open_ns + 20,
        first_trade_id="t1",
        last_trade_id="t9",
        is_final=True,
    )


def snapshot(*, as_of_ns: int, center: float = 112_000.0) -> ChannelSnapshot:
    return ChannelSnapshot(
        as_of_ns=as_of_ns,
        model_name="rolling_ols",
        model_version="1",
        lookback=60,
        center_now=center,
        upper_now=center + 100.0,
        lower_now=center - 100.0,
        slope_normalized=0.2,
        slope_log_per_bar=0.0001,
        width_pct=0.18,
        forecast_horizons=(1.5, 2.5),
        quality=ChannelQuality(
            score=0.8,
            submetrics={"fit": 0.9, "width": 0.7},
            contributing=("fit", "width"),
            unavailable=("age",),
        ),
        source_max_event_time_ns=as_of_ns - 1,
    )


def candidate(*, opened_at_ns: int = BASE_NS + 3 * MINUTE_NS) -> Candidate:
    return Candidate(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        direction="short",
        boundary="upper",
        state=CandidateState.CONFIRMED,
        opened_at_ns=opened_at_ns,
        bars_since_open=2,
        history=(
            Transition(
                from_state=CandidateState.NONE,
                to_state=CandidateState.APPROACH,
                bar_close_time_ns=opened_at_ns,
                reason="entered the upper zone",
            ),
            Transition(
                from_state=CandidateState.APPROACH,
                to_state=CandidateState.TOUCH,
                bar_close_time_ns=opened_at_ns,
                reason="touched the boundary in the same bar",
            ),
            Transition(
                from_state=CandidateState.TOUCH,
                to_state=CandidateState.CONFIRMED,
                bar_close_time_ns=opened_at_ns + MINUTE_NS,
                reason="rejection confirmed",
            ),
        ),
    )


def score() -> SignalScore:
    return SignalScore(
        raw=72.0,
        final=68.0,
        data_quality=0.94,
        confidence=0.8,
        contributions=(
            GroupContribution(
                group=Group.CHANNEL_STRUCTURE, value=20.0, factors=("quality", "width")
            ),
            GroupContribution(group=Group.REJECTION_QUALITY, value=12.0, factors=("wick",)),
        ),
        missing=(Group.DEFI_CROSSVENUE,),
    )


@pytest.mark.trace("REQ-STORE-002")
def test_a_bar_round_trips_with_its_decimals(repo: Repo) -> None:
    """Whatever is underneath, a price is the price that went in."""
    repo.add_bar(bar(1, price="0.1"))

    read = repo.bars(venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS)

    assert read == [bar(1, price="0.1")]
    assert read[0].open == Decimal("0.1")


@pytest.mark.trace("REQ-STORE-002")
def test_bars_come_back_in_time_order_and_the_limit_takes_the_newest(repo: Repo) -> None:
    """A chart opening on a symbol wants the end of the series; the oldest N
    would look like a stalled feed."""
    for index in (3, 1, 2):
        repo.add_bar(bar(index))

    read = repo.bars(venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, limit=2)

    assert [b.open_time_ns for b in read] == [
        bar(2).open_time_ns,
        bar(3).open_time_ns,
    ]


@pytest.mark.trace("REQ-STORE-002")
def test_bars_can_be_bounded_at_both_ends(repo: Repo) -> None:
    for index in range(1, 5):
        repo.add_bar(bar(index))

    read = repo.bars(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        start_ns=bar(2).close_time_ns,
        end_ns=bar(3).close_time_ns,
    )

    assert [b.open_time_ns for b in read] == [bar(2).open_time_ns, bar(3).open_time_ns]


@pytest.mark.trace("REQ-STORE-002")
def test_a_market_list_filters_on_both_fields(repo: Repo) -> None:
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="spot")
    repo.add_market(venue="binance", symbol="ETHUSDT", market_type="perp")
    repo.add_market(venue="bybit", symbol="BTCUSDT", market_type="spot")

    assert len(repo.markets()) == 3
    assert {m.symbol for m in repo.markets(venue="binance")} == {"BTCUSDT", "ETHUSDT"}
    assert {m.venue for m in repo.markets(market_type="spot")} == {"binance", "bybit"}


@pytest.mark.trace("REQ-STORE-002")
def test_a_channel_snapshot_is_never_later_than_the_instant_asked_for(repo: Repo) -> None:
    """The API's FR-017. A snapshot taken after the requested instant is exactly
    the hindsight PRD §27.5 exists to keep out of the view."""
    early, late = BASE_NS + MINUTE_NS, BASE_NS + 5 * MINUTE_NS
    repo.add_channel_snapshot(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, snapshot=snapshot(as_of_ns=early)
    )
    repo.add_channel_snapshot(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, snapshot=snapshot(as_of_ns=late)
    )

    at_early = repo.channel_snapshot_at(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, at_ns=late - 1
    )
    at_late = repo.channel_snapshot_at(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, at_ns=late
    )

    assert at_early is not None and at_early.as_of_ns == early
    assert at_late is not None and at_late.as_of_ns == late


@pytest.mark.trace("REQ-STORE-002")
def test_a_channel_snapshot_survives_its_quality_and_its_forecast(repo: Repo) -> None:
    """PRD §29.6 names quality components and forecast arrays; both are
    containers, and losing either would be invisible in a scalar-only table."""
    original = snapshot(as_of_ns=BASE_NS + MINUTE_NS)
    repo.add_channel_snapshot(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, snapshot=original
    )

    read = repo.channel_snapshot_at(
        venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, at_ns=BASE_NS + MINUTE_NS
    )

    assert read == original


@pytest.mark.trace("REQ-STORE-002")
def test_a_snapshot_for_another_series_is_not_returned(repo: Repo) -> None:
    repo.add_channel_snapshot(
        venue="binance",
        symbol="ETHUSDT",
        timeframe_ns=MINUTE_NS,
        snapshot=snapshot(as_of_ns=BASE_NS + MINUTE_NS),
    )

    assert (
        repo.channel_snapshot_at(
            venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, at_ns=BASE_NS + MINUTE_NS
        )
        is None
    )


@pytest.mark.trace("REQ-STORE-002")
def test_feature_points_come_back_grouped_by_instant(repo: Repo) -> None:
    """Stored one row per feature, read one point per instant."""
    repo.add_feature_snapshot(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=BASE_NS + MINUTE_NS,
        values={"ofi_1m": 0.4, "qi_l1": -0.2},
    )
    repo.add_feature_snapshot(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=BASE_NS + 2 * MINUTE_NS,
        values={"ofi_1m": 0.7},
    )

    points = repo.feature_points(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        start_ns=BASE_NS,
        end_ns=BASE_NS + 10 * MINUTE_NS,
    )

    assert [p.at_ns for p in points] == [BASE_NS + MINUTE_NS, BASE_NS + 2 * MINUTE_NS]
    assert points[0].values == {"ofi_1m": 0.4, "qi_l1": -0.2}
    assert points[1].values == {"ofi_1m": 0.7}


@pytest.mark.trace("REQ-STORE-002")
def test_feature_points_are_bounded_at_both_ends(repo: Repo) -> None:
    for index in range(1, 4):
        repo.add_feature_snapshot(
            venue="binance",
            symbol="BTCUSDT",
            timeframe_ns=MINUTE_NS,
            at_ns=BASE_NS + index * MINUTE_NS,
            values={"ofi_1m": float(index)},
        )

    points = repo.feature_points(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        start_ns=BASE_NS + 2 * MINUTE_NS,
        end_ns=BASE_NS + 2 * MINUTE_NS,
    )

    assert [p.at_ns for p in points] == [BASE_NS + 2 * MINUTE_NS]


@pytest.mark.trace("REQ-STORE-002")
def test_a_signal_round_trips_with_its_history_in_order(repo: Repo) -> None:
    """Two of the three transitions share a bar close time. Without an ordinal
    their order would depend on how the rows came back, which is not an order."""
    original = candidate()
    repo.add_signal(original)

    read = repo.signals()

    assert read == [original]
    assert [t.to_state for t in read[0].history] == [
        CandidateState.APPROACH,
        CandidateState.TOUCH,
        CandidateState.CONFIRMED,
    ]


@pytest.mark.trace("REQ-STORE-002")
def test_signals_filter_on_every_field_the_port_offers(repo: Repo) -> None:
    repo.add_signal(candidate())

    assert repo.signals(symbol="BTCUSDT") != []
    assert repo.signals(symbol="ETHUSDT") == []
    assert repo.signals(timeframe_ns=MINUTE_NS) != []
    assert repo.signals(timeframe_ns=5 * MINUTE_NS) == []
    assert repo.signals(status="confirmed") != []
    assert repo.signals(status="expired") == []
    assert repo.signals(start_ns=BASE_NS) != []
    assert repo.signals(start_ns=BASE_NS + 99 * MINUTE_NS) == []
    assert repo.signals(end_ns=BASE_NS) == []


@pytest.mark.trace("REQ-STORE-002")
def test_a_signal_is_reachable_by_the_id_its_deep_link_uses(repo: Repo) -> None:
    """A different id here would make every alert link a 404 while looking
    entirely correct."""
    original = candidate()
    repo.add_signal(original)

    assert repo.signal(signal_id_for(original)) == original
    assert repo.signal(uuid.UUID(int=0)) is None


@pytest.mark.trace("REQ-STORE-002")
def test_a_score_round_trips_with_its_contributions(repo: Repo) -> None:
    repo.add_setup_score(
        venue="binance",
        symbol="BTCUSDT",
        score=score(),
        feature_snapshot={"ofi_1m": 0.4, "qi_l1": -0.2},
        model_version="score-1",
        liquidity_factor=0.9,
        novelty_factor=0.8,
    )

    read = repo.setup_score(venue="binance", symbol="BTCUSDT")

    assert read is not None
    assert read.score == score()
    assert read.feature_snapshot == {"ofi_1m": 0.4, "qi_l1": -0.2}
    assert read.model_version == "score-1"
    assert (read.liquidity_factor, read.novelty_factor) == (0.9, 0.8)


@pytest.mark.trace("REQ-STORE-002")
def test_a_market_nobody_scored_has_no_score(repo: Repo) -> None:
    """`None`, not a zero. A market nobody scored and a market that scored zero
    are different facts."""
    assert repo.setup_score(venue="binance", symbol="BTCUSDT") is None


@pytest.mark.trace("REQ-STORE-002")
def test_an_empty_repository_answers_every_read_without_raising(repo: Repo) -> None:
    """The state a fresh deployment is in, and the one a reader is most likely to
    hit first."""
    assert repo.markets() == []
    assert repo.bars(venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS) == []
    assert (
        repo.channel_snapshot_at(
            venue="binance", symbol="BTCUSDT", timeframe_ns=MINUTE_NS, at_ns=BASE_NS
        )
        is None
    )
    assert (
        repo.feature_points(
            venue="binance",
            symbol="BTCUSDT",
            timeframe_ns=MINUTE_NS,
            start_ns=0,
            end_ns=BASE_NS,
        )
        == []
    )
    assert repo.signals() == []
    assert repo.signal(uuid.UUID(int=0)) is None
    assert repo.setup_score(venue="binance", symbol="BTCUSDT") is None


@pytest.mark.trace("REQ-STORE-002")
def test_the_latest_score_is_the_one_returned(repo: Repo) -> None:
    """Two scores for one market, and the second is what a reader gets.

    The in-memory repository overwrites; the plane appends. Both have to answer
    the same question the same way, and on the plane that means the newest row
    rather than the first one found -- scores tie on their instant whenever the
    caller does not supply one.
    """
    repo.add_setup_score(
        venue="binance",
        symbol="BTCUSDT",
        score=score(),
        feature_snapshot={"ofi_1m": 0.4},
        model_version="score-1",
    )
    later = SignalScore(
        raw=30.0,
        final=28.0,
        data_quality=0.5,
        confidence=0.4,
        contributions=(GroupContribution(group=Group.ORDER_FLOW, value=8.0, factors=("ofi",)),),
        missing=(),
    )
    repo.add_setup_score(
        venue="binance",
        symbol="BTCUSDT",
        score=later,
        feature_snapshot={"ofi_1m": 0.9},
        model_version="score-2",
    )

    read = repo.setup_score(venue="binance", symbol="BTCUSDT")

    assert read is not None
    assert read.model_version == "score-2"
    assert read.feature_snapshot == {"ofi_1m": 0.9}
    # The earlier score's two groups must not appear beside this one's single
    # group: a reader that took every contribution for the market would report a
    # score that does not add up.
    assert read.score == later


# --- an instrument's trading rules (REQ-WP-021) ------------------------------


def an_instrument(symbol: str = "BTCUSDT", **overrides: object) -> Instrument:
    fields: dict[str, object] = {
        "venue": "binance",
        "symbol": symbol,
        "market_type": "perp",
        "base_asset": symbol[:3],
        "quote_asset": "USDT",
        "tick_size": Decimal("0.10"),
        "step_size": Decimal("0.001"),
        "min_notional": Decimal("5"),
        "contract_size": Decimal("1"),
        "status": "TRADING",
    }
    fields.update(overrides)
    return Instrument(**fields)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-021")
def test_a_market_carries_the_rules_it_was_stored_with(repo: Repo) -> None:
    instrument = an_instrument()
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="perp", instrument=instrument)

    (market,) = repo.markets()

    assert market.instrument == instrument


@pytest.mark.trace("REQ-WP-021")
def test_every_decimal_survives_the_round_trip_exactly(repo: Repo) -> None:
    """`0.10` is the venue's tick size and `float("0.10")` is not. A rule that
    came back as `0.1000000000000000055511151231257827` would round a price to a
    tick the venue does not have."""
    instrument = an_instrument(tick_size=Decimal("0.010"), min_notional=Decimal("5.25"))
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="perp", instrument=instrument)

    (market,) = repo.markets()

    assert market.instrument is not None
    assert market.instrument.tick_size == Decimal("0.010")
    assert market.instrument.min_notional == Decimal("5.25")


@pytest.mark.trace("REQ-WP-021")
def test_a_market_stored_without_rules_has_them_absent(repo: Repo) -> None:
    """Absent, not zeroed. An unknown tick size and a tick size of zero must
    never read alike -- the second is a rule, and it is one nothing could
    satisfy."""
    repo.add_market(venue="binance", symbol="BTCUSDT", market_type="perp")

    (market,) = repo.markets()

    assert market.instrument is None


@pytest.mark.trace("REQ-WP-021")
def test_a_market_described_twice_appears_once(repo: Repo) -> None:
    """A re-ingest is one market described twice, not two markets. Returning
    both would make a routine refresh look like a second venue."""
    repo.add_market(
        venue="binance", symbol="BTCUSDT", market_type="perp", instrument=an_instrument()
    )
    repo.add_market(
        venue="binance",
        symbol="BTCUSDT",
        market_type="perp",
        instrument=an_instrument(tick_size=Decimal("0.50")),
    )

    markets = repo.markets()

    assert len(markets) == 1
    assert markets[0].instrument is not None
    assert markets[0].instrument.tick_size == Decimal("0.50")


@pytest.mark.trace("REQ-WP-021")
def test_one_venue_s_rules_are_not_returned_for_another(repo: Repo) -> None:
    repo.add_market(
        venue="binance", symbol="BTCUSDT", market_type="perp", instrument=an_instrument()
    )
    repo.add_market(
        venue="bybit",
        symbol="BTCUSDT",
        market_type="perp",
        instrument=an_instrument(venue="bybit", tick_size=Decimal("0.25")),
    )

    (market,) = repo.markets(venue="bybit")

    assert market.instrument is not None
    assert market.instrument.tick_size == Decimal("0.25")


@pytest.mark.trace("REQ-WP-021")
def test_a_spot_market_has_no_contract_size(repo: Repo) -> None:
    repo.add_market(
        venue="binance",
        symbol="BTCUSDT",
        market_type="spot",
        instrument=an_instrument(market_type="spot", contract_size=None),
    )

    (market,) = repo.markets()

    assert market.instrument is not None
    assert market.instrument.contract_size is None


# --- extrema, and when they may be seen (REQ-WP-028) -------------------------


def a_turn(
    *, turn_at: int, known_at: int, instrument: str = "binance:BTCUSDT"
) -> ConfirmedExtremum:
    return ConfirmedExtremum(
        extremum_id=uuid.uuid5(uuid.NAMESPACE_OID, f"{instrument}:{turn_at}:{known_at}"),
        instrument_id=instrument,
        timeframe_ns=MINUTE_NS,
        extremum_type="HIGH",
        extremum_time_ns=BASE_NS + turn_at * MINUTE_NS,
        known_at_ns=BASE_NS + known_at * MINUTE_NS,
        price=Decimal("112000.10"),
        confirmation_method="directional_change",
        confirmation_lag_bars=known_at - turn_at,
        reversal_bps=45.0,
        threshold_bps=30.0,
        prominence_bps=None,
        prominence_atr=None,
        channel_class=None,
        source_candidate_id=None,
    )


def a_candidate(*, at: int, observed: int) -> ExtremumCandidate:
    return ExtremumCandidate(
        candidate_id=uuid.uuid5(uuid.NAMESPACE_OID, f"cand:{at}"),
        instrument_id="binance:BTCUSDT",
        venue_scope="binance",
        timeframe_ns=MINUTE_NS,
        candidate_type="LOW",
        candidate_time_ns=BASE_NS + at * MINUTE_NS,
        observed_at_ns=BASE_NS + observed * MINUTE_NS,
        price=Decimal("111000.00"),
        method="directional_change",
        structural_score=0.4,
        channel_position=None,
        data_quality="ok",
    )


@pytest.mark.trace("REQ-WP-028")
def test_a_turn_is_not_visible_before_it_was_confirmed(repo: Repo) -> None:
    """PRD section 45's Phase 1A acceptance, asserted of both implementations.

    The turn happened at minute 10 and was confirmed at minute 14. Returning it
    as of minute 13 would be the chart claiming the system knew about a turn
    before it did.
    """
    repo.add_confirmed_extremum(a_turn(turn_at=10, known_at=14))

    before = repo.extrema(
        instrument_id="binance:BTCUSDT",
        timeframe_ns=MINUTE_NS,
        as_of_ns=BASE_NS + 13 * MINUTE_NS,
    )
    after = repo.extrema(
        instrument_id="binance:BTCUSDT",
        timeframe_ns=MINUTE_NS,
        as_of_ns=BASE_NS + 14 * MINUTE_NS,
    )

    assert before.confirmed == []
    assert len(after.confirmed) == 1


@pytest.mark.trace("REQ-WP-028")
def test_a_visible_turn_still_reports_where_it_happened(repo: Repo) -> None:
    """The other half of the pair. Drawing it at `known_at` never appears too
    early and is also not where the turn was."""
    repo.add_confirmed_extremum(a_turn(turn_at=10, known_at=14))

    (found,) = repo.extrema(
        instrument_id="binance:BTCUSDT", timeframe_ns=MINUTE_NS, as_of_ns=None
    ).confirmed

    assert found.extremum_time_ns == BASE_NS + 10 * MINUTE_NS
    assert found.known_at_ns == BASE_NS + 14 * MINUTE_NS


@pytest.mark.trace("REQ-WP-028")
def test_a_candidate_obeys_the_same_rule(repo: Repo) -> None:
    repo.add_extremum_candidate(a_candidate(at=10, observed=12))

    before = repo.extrema(
        instrument_id="binance:BTCUSDT",
        timeframe_ns=MINUTE_NS,
        as_of_ns=BASE_NS + 11 * MINUTE_NS,
    )
    after = repo.extrema(
        instrument_id="binance:BTCUSDT",
        timeframe_ns=MINUTE_NS,
        as_of_ns=BASE_NS + 12 * MINUTE_NS,
    )

    assert before.candidates == []
    assert len(after.candidates) == 1


@pytest.mark.trace("REQ-WP-028")
def test_candidates_and_confirmations_are_kept_apart(repo: Repo) -> None:
    """Two lists rather than one with a flag: a caller that had to tell them
    apart by inspecting a field would eventually forget to."""
    repo.add_confirmed_extremum(a_turn(turn_at=10, known_at=14))
    repo.add_extremum_candidate(a_candidate(at=20, observed=21))

    found = repo.extrema(instrument_id="binance:BTCUSDT", timeframe_ns=MINUTE_NS, as_of_ns=None)

    assert len(found.confirmed) == 1
    assert len(found.candidates) == 1


@pytest.mark.trace("REQ-WP-028")
def test_one_instrument_does_not_see_another_s_turns(repo: Repo) -> None:
    repo.add_confirmed_extremum(a_turn(turn_at=10, known_at=14))
    repo.add_confirmed_extremum(a_turn(turn_at=10, known_at=14, instrument="binance:ETHUSDT"))

    found = repo.extrema(instrument_id="binance:ETHUSDT", timeframe_ns=MINUTE_NS, as_of_ns=None)

    assert [e.instrument_id for e in found.confirmed] == ["binance:ETHUSDT"]
