"""PRD §35.4: every feature answers the same on a truncated and a full input.

    For every feature:
      1. Run on truncated dataset through `t`.
      2. Run on full dataset but ask for feature at `t`.
      3. Values must match exactly within numeric tolerance.
      This should be an automated CI suite.

**Why this is worth the work.** `FeatureSpec` carries
`point_in_time_safe: Literal[True]`, so the type makes any other value
unregisterable: all 55 registered features *declare* point-in-time safety, and
the only test that touches that field asserts it is a `bool` — which the type
guarantees before the test runs. The promise is extracted by the type and
verified by nothing. This is its verification.

**`NOT_YET_COVERED` is a debt register, not a permission.** The 55 features share
no interface — some take events with a window, some a book service, some a
stateful tracker — so each case is written by hand against its own signature.
[[REQ-NRT-LEAK]] stays at `specified` until that list is empty. What the list
*does* buy: a feature added tomorrow lands in `uncovered()` and not in the
literal, so the suite goes red by name rather than the gap widening quietly.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import pytest

from channelflow.bars import Bar
from channelflow.book import BookService
from channelflow.channels import RollingOLSChannel
from channelflow.channels.features import (
    channel_position,
    channel_quality_score,
    channel_slope_normalized,
    channel_width_pct,
)
from channelflow.derivatives.funding import (
    funding_acceleration,
    funding_z,
    settled_funding,
)
from channelflow.derivatives.liquidations import intensity, time_since_spike
from channelflow.derivatives.liquidations import window as liq_window
from channelflow.derivatives.openinterest import (
    basis_bps,
    mark_premium_bps,
    oi_change,
    oi_to_volume,
    oi_z,
    price_oi_regime,
)
from channelflow.derivatives.positioning import (
    long_short_ratio,
    long_short_z,
    top_trader_ratio,
)
from channelflow.derivatives.state import state_at
from channelflow.domain import BookDelta, DerivativesState, LiquidationEvent
from channelflow.features import REGISTRY, exposed_feature_names
from channelflow.features.flow import FlowTracker
from channelflow.features.ofi import OFITracker
from channelflow.features.truncation import (
    RELATIVE_TOLERANCE,
    Refusal,
    TruncationCase,
    divergence,
    uncovered,
)
from channelflow.features.walls import WallTracker
from tests.unit.channels.conftest import log_linear_series
from tests.unit.derivatives.conftest import BASE_NS as DBASE_NS
from tests.unit.derivatives.conftest import MINUTE_NS as DMINUTE_NS
from tests.unit.derivatives.conftest import NOT_ABOUT_FRESHNESS, liquidation
from tests.unit.derivatives.conftest import meta as dmeta
from tests.unit.features.conftest import BASE_NS, SECOND_NS, levels, snapshot, trade
from tests.unit.features.conftest import meta as bmeta
from tests.unit.features.test_ofi import obs

LOOKBACK = 30
BARS = 90
#: The moment every case asks about: far enough in that the model has its whole
#: lookback, far enough from the end that a real future exists to leak from.
AT_INDEX = 60


def _snapshot(bars: list[Bar], *, upto: int | None, at_index: int):
    """Fit at `bars[at_index]`, seeing either the prefix or everything."""
    series = bars if upto is None else bars[:upto]
    return RollingOLSChannel(lookback=LOOKBACK).fit(
        list(series), as_of_ns=bars[at_index].close_time_ns
    )


def _channel_cases() -> list[TruncationCase]:
    bars = log_linear_series(BARS)
    at_ns = bars[AT_INDEX].close_time_ns
    price = float(bars[AT_INDEX].close)
    readers = {
        "channel_slope_normalized": channel_slope_normalized,
        "channel_width_pct": channel_width_pct,
        "channel_quality_score": channel_quality_score,
    }
    cases = [
        TruncationCase(
            feature=name,
            at_ns=at_ns,
            truncated=lambda reader=reader: reader(
                _snapshot(bars, upto=AT_INDEX + 1, at_index=AT_INDEX)
            ),
            full=lambda reader=reader: reader(_snapshot(bars, upto=None, at_index=AT_INDEX)),
        )
        for name, reader in readers.items()
    ]
    cases.append(
        TruncationCase(
            feature="channel_position",
            at_ns=at_ns,
            truncated=lambda: channel_position(
                _snapshot(bars, upto=AT_INDEX + 1, at_index=AT_INDEX), price
            ),
            full=lambda: channel_position(_snapshot(bars, upto=None, at_index=AT_INDEX), price),
        )
    )
    return cases


def _flow_cases() -> list[TruncationCase]:
    """`trade_flow`: a stateful tracker, fed trades, asked for a window at `t`.

    The truncated side sees only trades at or before `t`; the full side sees the
    whole day. `FlowTracker.window` filters `floor < event_time <= as_of_ns` and
    `_cvd_at` stops at the first event past its argument, so the two should
    agree -- and if either boundary were `<` or `<=` the wrong way, or the cursor
    walked past `t`, this is what would notice.
    """
    trades = [
        trade(f"t{i}", "100", "1", "buy" if i % 3 else "sell", at_ns=BASE_NS + i * SECOND_NS)
        for i in range(1, 41)
    ]
    at_ns = BASE_NS + 20 * SECOND_NS
    window_ns = 10 * SECOND_NS

    def tracker(upto_t: bool) -> FlowTracker:
        built = FlowTracker()
        for event in trades:
            if upto_t and event.meta.event_time_ns > at_ns:
                continue
            built.observe(event)
        return built

    readers: dict[str, Callable[[FlowTracker], object]] = {
        "delta_notional": lambda t: t.window(window_ns, as_of_ns=at_ns).delta,
        "normalized_delta": lambda t: t.window(window_ns, as_of_ns=at_ns).normalized_delta,
        "cvd": lambda t: t.window(window_ns, as_of_ns=at_ns).cvd_end,
        "cvd_slope": lambda t: t.window(window_ns, as_of_ns=at_ns).cvd_slope_per_second,
        "cvd_acceleration": lambda t: t.acceleration(window_ns, as_of_ns=at_ns),
    }
    return [
        TruncationCase(
            feature=name,
            at_ns=at_ns,
            truncated=lambda reader=reader: reader(tracker(upto_t=True)),
            full=lambda reader=reader: reader(tracker(upto_t=False)),
        )
        for name, reader in readers.items()
    ]


def _ofi_cases() -> list[TruncationCase]:
    """`order_flow`: the same shape, over top-of-book observations.

    `ofi_bar` is the bar-length window rather than a fixed one, so it gets the
    signal timeframe -- a different number, not a different mechanism.
    """
    observations = [
        obs(
            str(100 + (i % 5)),
            str(10 + (i % 3)),
            str(101 + (i % 5)),
            str(12 + (i % 4)),
            at_ns=BASE_NS + i * SECOND_NS,
        )
        for i in range(1, 121)
    ]
    at_ns = BASE_NS + 90 * SECOND_NS

    def tracker(upto_t: bool) -> OFITracker:
        built = OFITracker()
        for observation in observations:
            if upto_t and observation.event_time_ns > at_ns:
                continue
            built.observe(observation)
        return built

    windows = {
        "ofi_1s": SECOND_NS,
        "ofi_5s": 5 * SECOND_NS,
        "ofi_30s": 30 * SECOND_NS,
        "ofi_1m": 60 * SECOND_NS,
        "ofi_bar": 60 * SECOND_NS,
    }
    return [
        TruncationCase(
            feature=name,
            at_ns=at_ns,
            truncated=lambda w=window: tracker(upto_t=True).window(w, as_of_ns=at_ns).value,
            full=lambda w=window: tracker(upto_t=False).window(w, as_of_ns=at_ns).value,
        )
        for name, window in windows.items()
    ]


def _derivatives_cases() -> list[TruncationCase]:
    """`derivatives`: mostly `(states, *, at_ns, ...)`, and five pure scalars.

    The scalars -- `basis_bps`, `mark_premium_bps`, `oi_to_volume`,
    `price_oi_regime`, `liquidation_intensity_5m` -- have no dataset of their
    own, so there is nothing in them to truncate. Their arguments are sourced
    through `state_at`, which is the point-in-time seam and therefore the path
    that can actually leak. A case that fed them two constants would agree with
    itself and prove nothing.
    """
    states = [
        DerivativesState(
            meta=dmeta(minute),
            mark_price=Decimal(112_000 + minute * 3),
            index_price=Decimal(112_000 + minute * 2),
            funding_rate=0.0001 * (1 + minute % 5),
            next_funding_time_ns=DBASE_NS + (minute // 60 + 1) * 60 * DMINUTE_NS,
            open_interest_usd=1_000_000.0 + minute * 2_000,
            open_interest_base=10.0 + minute,
            long_short_ratio=1.0 + 0.01 * (minute % 7),
            top_trader_long_short_ratio=1.0 + 0.02 * (minute % 5),
        )
        for minute in range(0, 121)
    ]
    events = [
        liquidation(
            at=minute,
            side="long_liquidated" if minute % 2 else "short_liquidated",
            notional=str(5_000 + minute),
        )
        for minute in range(1, 121)
    ]
    at_minute = 60
    at_ns = DBASE_NS + at_minute * DMINUTE_NS
    fresh = {"staleness_ns": NOT_ABOUT_FRESHNESS}
    five_m, one_h = 5 * DMINUTE_NS, 60 * DMINUTE_NS
    #: Not point-in-time data: a constant denominator, so any disagreement the
    #: case reports comes from the numerator's selection rather than from here.
    TRADED_USD = Decimal("50000000")

    def st(upto_t: bool) -> list[DerivativesState]:
        return [s for s in states if not upto_t or s.meta.event_time_ns <= at_ns]

    def ev(upto_t: bool) -> list[LiquidationEvent]:
        return [e for e in events if not upto_t or e.meta.event_time_ns <= at_ns]

    def price_change(rows: list[DerivativesState]) -> float:
        now = state_at(rows, at_ns=at_ns, **fresh).mark_price
        before = state_at(rows, at_ns=at_ns - one_h, **fresh).mark_price
        assert now is not None and before is not None
        return float(now - before)

    readers: dict[str, Callable[[list[DerivativesState], list[LiquidationEvent]], object]] = {
        "funding_rate_settled": lambda r, _e: settled_funding(r, at_ns=at_ns, **fresh)[-1].rate,
        "funding_z": lambda r, _e: funding_z(r, at_ns=at_ns, **fresh).value,
        "funding_acceleration": lambda r, _e: funding_acceleration(r, at_ns=at_ns, **fresh),
        "open_interest_usd": lambda r, _e: state_at(r, at_ns=at_ns, **fresh).open_interest_usd,
        "oi_change_5m": lambda r, _e: oi_change(r, at_ns=at_ns, window_ns=five_m, **fresh),
        "oi_change_1h": lambda r, _e: oi_change(r, at_ns=at_ns, window_ns=one_h, **fresh),
        "oi_z": lambda r, _e: oi_z(r, at_ns=at_ns, **fresh).value,
        "oi_to_volume": lambda r, _e: oi_to_volume(
            state_at(r, at_ns=at_ns, **fresh).open_interest_usd or 0.0, float(TRADED_USD)
        ),
        "price_oi_regime": lambda r, _e: (
            price_oi_regime(
                price_change=price_change(r),
                oi_change_usd=oi_change(r, at_ns=at_ns, window_ns=one_h, **fresh) or 0.0,
            ).value
        ),
        "basis_bps": lambda r, _e: basis_bps(
            perp_price=state_at(r, at_ns=at_ns, **fresh).mark_price,
            spot_price=state_at(r, at_ns=at_ns, **fresh).index_price,
        ),
        "mark_premium_bps": lambda r, _e: mark_premium_bps(
            mark_price=state_at(r, at_ns=at_ns, **fresh).mark_price,
            index_price=state_at(r, at_ns=at_ns, **fresh).index_price,
        ),
        "liquidation_long_usd_5m": lambda _r, e: (
            liq_window(e, as_of_ns=at_ns, window_ns=five_m).long_usd
        ),
        "liquidation_short_usd_5m": lambda _r, e: (
            liq_window(e, as_of_ns=at_ns, window_ns=five_m).short_usd
        ),
        "liquidation_imbalance_5m": lambda _r, e: (
            liq_window(e, as_of_ns=at_ns, window_ns=five_m).imbalance
        ),
        "liquidation_intensity_5m": lambda _r, e: intensity(
            liq_window(e, as_of_ns=at_ns, window_ns=five_m).total_usd, TRADED_USD
        ),
        "time_since_liquidation_spike": lambda _r, e: time_since_spike(
            e, as_of_ns=at_ns, spike_usd=Decimal("5030")
        ),
        "long_short_ratio": lambda r, _e: long_short_ratio(r, at_ns=at_ns, **fresh),
        "long_short_z": lambda r, _e: long_short_z(r, at_ns=at_ns, **fresh).value,
        "top_trader_long_short_ratio": lambda r, _e: top_trader_ratio(r, at_ns=at_ns, **fresh),
    }
    return [
        TruncationCase(
            feature=name,
            at_ns=at_ns,
            truncated=lambda reader=reader: reader(st(upto_t=True), ev(upto_t=True)),
            full=lambda reader=reader: reader(st(upto_t=False), ev(upto_t=False)),
        )
        for name, reader in readers.items()
    ]


#: Which `Wall` attribute each registered wall feature reads.
WALL_FIELDS = {
    "wall_persistence_ns": "persistence_ns",
    "wall_executed_size_est": "executed_size_est",
    "wall_cancelled_size_est": "cancelled_size_est",
    "wall_refill_count": "refill_count",
}


def _wall_field(tracker: WallTracker, field: str) -> object:
    """Summed over every wall the tracker knows, active and finished alike.

    Summed rather than "the biggest wall": which wall is biggest can change
    between two replays for reasons that have nothing to do with the future, and
    a case that picked one would report that churn as a leak.
    """
    walls = [*tracker.active, *tracker.finished]
    return (
        sum((getattr(w, field) for w in walls), type(getattr(walls[0], field))(0)) if walls else 0
    )


def _order_book_cases() -> list[TruncationCase]:
    """`order_book`: only the wall half can be asked §35.4's question.

    The eleven instant features -- `qi_l1`, `microprice`, the eight depth
    imbalances -- read `BookService` as it stands. No API in that path accepts a
    dataset **and** a moment, so "run on the full dataset but ask for the feature
    at `t`" has no expression: the only way to ask for `t` is to have replayed
    exactly to `t`, which makes the two runs one run. They are refused, with that
    as the reason, rather than covered by a case that would agree with itself.

    `WallTracker.observe(service, *, trades, as_of_ns)` is different: it takes
    the data and the moment **separately**, so the full run hands it every trade
    -- including trades after `t` -- and still says `as_of_ns=t`. That is §35.4's
    question exactly, and it had an answer worth having (see the note beside
    `test_a_wall_ignores_trades_from_after_its_moment`).
    """
    at_index = 10
    total = 20

    def delta(index: int) -> BookDelta:
        return BookDelta(
            meta=bmeta(BASE_NS + index * SECOND_NS),
            first_update_id=index + 2,
            final_update_id=index + 2,
            prev_update_id=index + 1,
            bids=levels([("112000", str(max(1, 40 - index * 3))), ("111999", "2")]),
            asks=levels([("112002", "4"), ("112003", "1")]),
        )

    deltas = [delta(i) for i in range(total)]
    at_ns = BASE_NS + at_index * SECOND_NS
    #: Small enough that the traded volume, not the wall's shrink, is what binds.
    #: At one unit a trade the attribution saturates and the two runs agree for a
    #: reason that has nothing to do with point-in-time safety.
    trades = tuple(
        trade(f"w{i}", "112000", "0.2", "buy", at_ns=BASE_NS + i * SECOND_NS) for i in range(total)
    )

    def wall_value(field: str, *, hand_over_the_future: bool) -> object:
        service = BookService()
        service.on_snapshot(
            snapshot(
                1,
                [("112000", "3"), ("111999", "2")],
                [("112002", "4"), ("112003", "1")],
                at_ns=BASE_NS,
            )
        )
        tracker = WallTracker()
        for event in deltas:
            moment = event.meta.event_time_ns
            if moment > at_ns:
                break
            service.on_delta(event)
            given = (
                trades
                if hand_over_the_future
                else tuple(t for t in trades if t.meta.event_time_ns <= moment)
            )
            tracker.observe(service, trades=given, as_of_ns=moment)
        return _wall_field(tracker, field)

    return [
        TruncationCase(
            feature=name,
            at_ns=at_ns,
            truncated=lambda f=field: wall_value(f, hand_over_the_future=False),
            full=lambda f=field: wall_value(f, hand_over_the_future=True),
        )
        for name, field in WALL_FIELDS.items()
    ]


CASES: list[TruncationCase] = (
    _channel_cases() + _flow_cases() + _ofi_cases() + _derivatives_cases() + _order_book_cases()
)

#: The eleven `order_book` instant features. Their path holds no API that takes
#: a dataset and a moment, so §35.4's second run cannot be expressed for them.
_NO_MOMENT = (
    "reads BookService as it stands; nothing in this path accepts a dataset and "
    "a moment, so the only way to ask for t is to have replayed exactly to t, "
    "and the two runs would be one run. Point-in-time safety here is the replay "
    "driver's, and tests/unit/book/ owns it"
)

REFUSALS: list[Refusal] = [
    Refusal(feature=name, reason=_NO_MOMENT)
    for name in (
        "qi_l1",
        "microprice",
        "microprice_mid_spread_bps",
        "depth_imbalance_5",
        "depth_imbalance_10",
        "depth_imbalance_20",
        "depth_imbalance_50",
        "depth_imbalance_bps_5",
        "depth_imbalance_bps_10",
        "depth_imbalance_bps_25",
        "depth_imbalance_bps_50",
    )
]

#: Registered features with neither a case nor a refusal. This list is debt and
#: must only shrink. REQ-NRT-LEAK cannot reach `implemented` while it is
#: non-empty.
COVERED_FAMILIES = frozenset({"channel", "trade_flow", "order_flow", "derivatives", "order_book"})

NOT_YET_COVERED: frozenset[str] = frozenset(
    name for name in exposed_feature_names() if REGISTRY[name].family not in COVERED_FAMILIES
)


# --- the enumeration --------------------------------------------------------


@pytest.mark.trace("REQ-NRT-LEAK")
def test_the_registry_is_fully_imported_before_anything_is_counted() -> None:
    """`REGISTRY` reaches 27 if only `channelflow.features.*` is imported.

    Three further packages register features. `exposed_feature_names()` imports
    all eight, and is therefore the enumeration -- counting the other way looks
    complete and is half.
    """
    names = exposed_feature_names()
    assert len(names) == 55
    assert sorted(names) == sorted(REGISTRY)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_every_registered_feature_is_covered_or_declared_outstanding() -> None:
    """A feature added tomorrow is red by name, not a quietly widening gap."""
    assert uncovered(REGISTRY, CASES, REFUSALS) == NOT_YET_COVERED, (
        "a registered feature has neither a truncation case nor a refusal, and is "
        "not in NOT_YET_COVERED -- add a case, or add it to the debt register"
    )


@pytest.mark.trace("REQ-NRT-LEAK")
def test_the_debt_register_is_what_stops_this_requirement_completing() -> None:
    assert len(NOT_YET_COVERED) == 7
    assert len(CASES) == 37
    assert len(REFUSALS) == 11
    assert {REGISTRY[case.feature].family for case in CASES} == COVERED_FAMILIES


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_case_for_an_unregistered_feature_is_refused() -> None:
    """Otherwise a typo in a feature name reads as coverage."""
    stray = TruncationCase(
        feature="no_such_feature", at_ns=1, truncated=lambda: 1.0, full=lambda: 1.0
    )
    with pytest.raises(KeyError, match="no_such_feature"):
        uncovered(REGISTRY, [*CASES, stray], REFUSALS)


# --- the parity itself ------------------------------------------------------


@pytest.mark.trace("REQ-NRT-LEAK")
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.feature)
def test_the_truncated_and_full_runs_agree(case: TruncationCase) -> None:
    found = divergence(case)
    assert found is None, str(found)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_every_case_computes_a_value() -> None:
    """A case whose two sides both return nothing agrees with itself and proves nothing.

    A string is a value: `price_oi_regime` is a classification, not a number, and
    a leak in it would read as the wrong regime rather than the wrong magnitude.
    """
    for case in CASES:
        value = case.truncated()
        assert value is not None, f"{case.feature} produced nothing to compare"
        assert isinstance(value, float | int | Decimal | str), f"{case.feature} gave {value!r}"


@pytest.mark.trace("REQ-NRT-LEAK")
def test_the_inputs_are_not_degenerate() -> None:
    """Zero on both sides is agreement about nothing happening.

    At least one case per covered family has to move, or the series feeding it
    is flat and the parity it demonstrates is vacuous.
    """
    moved: set[str] = set()
    for case in CASES:
        if case.truncated() not in (0, 0.0, None):
            moved.add(REGISTRY[case.feature].family)
    assert moved == COVERED_FAMILIES, f"no moving value in {sorted(COVERED_FAMILIES - moved)}"


# --- the fault, introduced on purpose ---------------------------------------


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_wall_ignores_trades_from_after_its_moment() -> None:
    """The one real leak §35.4 has found in this repository so far.

    `WallTracker.observe(service, *, trades, as_of_ns)` takes the data and the
    moment separately and, until this requirement, reconciled them nowhere. Every
    production caller filtered; nothing made them. Measured before the fix, on a
    wall shrinking three units a step against trades of 0.2 each:

        executed_size_est   2.0 filtered    4.0 unfiltered
        cancelled_size_est 25.0 filtered   23.0 unfiltered

    Trade size matters and is why an earlier attempt at this test saw nothing: at
    one unit a trade the attribution saturates against the shrink, and the two
    runs agree for a reason that has nothing to do with point-in-time safety.
    """
    walls = _order_book_cases()
    by_feature = {case.feature: case for case in walls}
    assert set(by_feature) == set(WALL_FIELDS)
    for name in ("wall_executed_size_est", "wall_cancelled_size_est"):
        case = by_feature[name]
        assert case.truncated() == case.full(), f"{name} still depends on trades after as_of_ns"
    #: The fixture has to be in the regime where the filter can matter at all.
    executed = by_feature["wall_executed_size_est"].truncated()
    assert executed not in (0, Decimal(0)), (
        "no volume was attributed, so this test would pass with the filter removed"
    )


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_leaking_feature_is_caught_and_names_both_values() -> None:
    """A feature that reads a later row answers differently on the full input."""
    bars = log_linear_series(BARS)
    leaking = TruncationCase(
        feature="channel_width_pct",
        at_ns=bars[AT_INDEX].close_time_ns,
        truncated=lambda: float(bars[AT_INDEX].close),
        # The leak: it reads a bar after `t`.
        full=lambda: float(bars[BARS - 1].close),
    )
    found = divergence(leaking)
    assert found is not None, "a feature reading the future went unnoticed"
    assert found.feature == "channel_width_pct"
    assert found.truncated == float(bars[AT_INDEX].close)
    assert found.full == float(bars[BARS - 1].close)
    assert "channel_width_pct" in str(found)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_difference_inside_the_tolerance_is_not_a_divergence() -> None:
    base = 1_000.0
    case = TruncationCase(
        feature="channel_width_pct",
        at_ns=1,
        truncated=lambda: base,
        full=lambda: base * (1 + RELATIVE_TOLERANCE / 2),
    )
    assert divergence(case) is None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_difference_outside_the_tolerance_is_a_divergence() -> None:
    base = 1_000.0
    case = TruncationCase(
        feature="channel_width_pct",
        at_ns=1,
        truncated=lambda: base,
        full=lambda: base * (1 + RELATIVE_TOLERANCE * 10),
    )
    assert divergence(case) is not None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_two_large_integers_one_apart_are_not_the_same_answer() -> None:
    """A relative tolerance applied to integers would call these equal.

    `10**12` and `10**12 + 1` differ by 1e-12 relative -- inside any float
    tolerance worth having, and a whole unit of whatever the feature counts.
    """
    case = TruncationCase(
        feature="channel_width_pct",
        at_ns=1,
        truncated=lambda: 10**12,
        full=lambda: 10**12 + 1,
    )
    assert divergence(case) is not None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_an_integer_and_an_equal_float_are_different_answers() -> None:
    """`5` and `5.0` are equal in Python and are not the same value here."""
    case = TruncationCase(
        feature="channel_width_pct", at_ns=1, truncated=lambda: 5, full=lambda: 5.0
    )
    assert divergence(case) is not None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_integers_and_none_compare_exactly() -> None:
    """Tolerance is for floating point. An integer that moved by one has moved."""
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: 5, full=lambda: 6
            )
        )
        is not None
    )
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: 5, full=lambda: 5
            )
        )
        is None
    )
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: None, full=lambda: None
            )
        )
        is None
    )
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: None, full=lambda: 0.0
            )
        )
        is not None
    )


@pytest.mark.trace("REQ-NRT-LEAK")
@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n  "])
def test_a_refusal_has_to_give_a_reason(blank: str) -> None:
    """Whitespace is not a reason. A refusal without one is a skip, renamed."""
    with pytest.raises(ValueError, match="reason"):
        Refusal(feature="channel_width_pct", reason=blank)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_refusal_covers_the_feature_it_names() -> None:
    """Otherwise the debt register and the refusals disagree about the same name."""
    outstanding = sorted(NOT_YET_COVERED)[0]
    refusal = Refusal(feature=outstanding, reason="a reason long enough to be one")
    still_open = uncovered(REGISTRY, CASES, [*REFUSALS, refusal])
    assert outstanding not in still_open
    assert still_open == NOT_YET_COVERED - {outstanding}
