"""The worker's context-feature pass: open interest, funding (z) and basis at each bar's close.

REQ-WP-093. The point of every test here is Principle I -- a value at a bar's close is made of what
was knowable at that close, and appending later rows changes nothing -- and the rule that absence is
absence: a stale poll, a short history or a constant series writes no row, never a zero.
"""

from __future__ import annotations

import math
from decimal import Decimal

import pytest

from channelflow.bars.models import Bar
from channelflow.context import sources
from channelflow.derivatives import funding as funding_lib
from channelflow.derivatives.openinterest import basis_bps as perp_basis_bps
from channelflow.domain import DerivativesState, EventMeta
from channelflow.lakehouse import Catalog
from channelflow.pipeline import context_pass as write
from channelflow.tables import derivatives_state as state_table
from channelflow.tables import features as features_table

MINUTE = 60_000_000_000
HOUR = 60 * MINUTE
T0 = 1_791_700_000_000_000_000  # a settlement instant, round enough to read
FEATURES = ("open_interest_usd", "funding_z", "basis_bps")


def settled(
    at: int, rate: float, venue: str = "bybit", symbol: str = "BTCUSDT"
) -> DerivativesState:
    return DerivativesState(
        meta=EventMeta(
            source=f"{venue}-funding-history",
            venue=venue,
            market_type="perp",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=T0
            + 10_000 * HOUR,  # loaded long afterwards: availability is the settlement's
            sequence=None,
            source_event_id=None,
        ),
        funding_rate=rate,
        next_funding_time_ns=at,
    )


def polled(
    at: int,
    *,
    usd: float | None = 1_000.0,
    mark: str | None = "100.5",
    index: str | None = "100",
    ingest: int | None = None,
    venue: str = "bybit",
    symbol: str = "BTCUSDT",
    source: str | None = None,
    rate: float | None = 0.0001,
    next_funding: int | None = None,
) -> DerivativesState:
    return DerivativesState(
        meta=EventMeta(
            source=source or f"{venue}-rest",
            venue=venue,
            market_type="perp",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=at if ingest is None else ingest,
            sequence=None,
            source_event_id=None,
        ),
        mark_price=None if mark is None else Decimal(mark),
        index_price=None if index is None else Decimal(index),
        open_interest_usd=usd,
        funding_rate=rate,
        next_funding_time_ns=T0 + 8 * HOUR if next_funding is None else next_funding,
    )


def history(count: int = 30, *, ending: int = T0, varying: bool = True) -> list[DerivativesState]:
    return [
        settled(ending - (count - 1 - i) * 8 * HOUR, (0.0001 + 0.00001 * i) if varying else 0.0001)
        for i in range(count)
    ]


def series(minutes: int = 180, *, start: int = T0 + 1 * HOUR) -> list[DerivativesState]:
    """One polled state a minute, open interest rising so the latest one is recognisable."""
    return [
        polled(start + m * MINUTE, usd=1_000.0 + m, mark=str(100 + m / 100)) for m in range(minutes)
    ]


def close_of(minute: int, *, start: int = T0 + 1 * HOUR) -> int:
    return start + minute * MINUTE


# --- the value at a close -----------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-093")
def test_the_three_values_at_a_close_are_what_the_library_gives_at_that_instant() -> None:
    states = sorted(history() + series(), key=lambda s: s.meta.event_time_ns)
    close = close_of(90) + 5 * 1_000_000_000  # five seconds after the 90th poll

    values = write.context_values(states, close_ns=close)

    latest = [s for s in states if s.meta.source == "bybit-rest" and s.meta.event_time_ns <= close][
        -1
    ]
    assert values["open_interest_usd"] == latest.open_interest_usd
    assert values["basis_bps"] == pytest.approx(
        perp_basis_bps(perp_price=latest.mark_price, spot_price=latest.index_price)
    )
    expected = funding_lib.funding_z(
        history(), at_ns=close, window=24, staleness_ns=sources.FUNDING_STALENESS_NS
    ).value
    assert values["funding_z"] == pytest.approx(expected)
    assert set(values) == set(FEATURES)


@pytest.mark.trace("REQ-WP-093")
def test_values_are_plain_finite_floats() -> None:
    values = write.context_values(history() + series(), close_ns=close_of(10))
    assert all(isinstance(v, float) and math.isfinite(v) for v in values.values())


# --- Principle I ----------------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-093")
def test_appending_later_rows_changes_nothing_at_an_earlier_close() -> None:
    base = history() + series(60)
    close = close_of(30)
    before = write.context_values(base, close_ns=close)

    later = [polled(close + (i + 1) * MINUTE, usd=9e9, mark="999", index="1") for i in range(20)]
    later_history = [settled(close + 1 * HOUR, 5.0), settled(close + 9 * HOUR, 7.0)]

    assert write.context_values(base + later + later_history, close_ns=close) == before


@pytest.mark.trace("REQ-WP-093")
def test_a_state_observed_after_the_close_is_not_used_even_if_its_event_time_is_earlier() -> None:
    """Binance's open-interest bucket is dated at its own time and lands later.

    Event time at or before the close is not enough: a state whose receipt came after the close
    was not knowable at it.
    """
    close = close_of(30)
    known = polled(close - 2 * MINUTE, usd=111.0)
    late = polled(close - 1 * MINUTE, usd=222.0, ingest=close + 3 * MINUTE)

    values = write.context_values(history() + [known, late], close_ns=close)

    assert values["open_interest_usd"] == 111.0


@pytest.mark.trace("REQ-WP-093")
def test_basis_also_uses_only_what_had_been_received_by_the_close() -> None:
    close = close_of(30)
    known = polled(close - 2 * MINUTE, mark="101", index="100")
    late = polled(close - 1 * MINUTE, mark="150", index="100", ingest=close + 3 * MINUTE)

    values = write.context_values(history() + [known, late], close_ns=close)

    assert values["basis_bps"] == pytest.approx(100.0)  # 101 against 100, not 150 against 100


@pytest.mark.trace("REQ-WP-093")
def test_a_state_dated_after_the_close_is_not_used_when_the_venue_clock_runs_ahead() -> None:
    """The venue's clock can run ahead of ours: its event time is then after the close while we
    received it before. The event time is the venue's claim about when the figure was true."""
    close = close_of(30)
    known = polled(close - 2 * MINUTE, usd=111.0, mark="101", index="100")
    ahead = polled(close + 1 * MINUTE, usd=999.0, mark="150", index="100", ingest=close - 1)

    values = write.context_values(history() + [known, ahead], close_ns=close)

    assert values["open_interest_usd"] == 111.0
    assert values["basis_bps"] == pytest.approx(100.0)


@pytest.mark.trace("REQ-WP-093")
def test_a_settled_rate_is_available_from_its_settlement_not_from_when_it_was_loaded() -> None:
    """History is loaded long after the fact; the rate was public at its settlement."""
    values = write.context_values(history() + [polled(T0 + 30 * MINUTE)], close_ns=T0 + 31 * MINUTE)
    assert "funding_z" in values


# --- funding comes from settled rows only ---------------------------------------------------------


@pytest.mark.trace("REQ-WP-093")
def test_polled_funding_estimates_never_enter_the_funding_z() -> None:
    """Many polled states share a settlement; a 24-window of them is one interval, 24 times."""
    close = close_of(120)
    plain = write.context_values(history() + series(120), close_ns=close)

    noisy = [
        polled(close_of(m), rate=0.5 + m, next_funding=T0 - 8 * HOUR)  # 'settled' by their field
        for m in range(120)
    ]
    with_noise = write.context_values(history() + series(120) + noisy, close_ns=close)

    assert with_noise["funding_z"] == plain["funding_z"]


@pytest.mark.trace("REQ-WP-093")
def test_fewer_than_24_settlements_writes_no_funding_z() -> None:
    values = write.context_values(history(23) + series(60), close_ns=close_of(30))
    assert "funding_z" not in values and "open_interest_usd" in values


@pytest.mark.trace("REQ-WP-093")
def test_a_constant_funding_series_writes_no_funding_z_not_zero() -> None:
    values = write.context_values(history(30, varying=False) + series(60), close_ns=close_of(30))
    assert "funding_z" not in values


@pytest.mark.trace("REQ-WP-093")
def test_a_settlement_older_than_one_interval_plus_the_margin_is_stale() -> None:
    last = T0
    just_inside = last + sources.FUNDING_STALENESS_NS
    assert "funding_z" in write.context_values(history(ending=last), close_ns=just_inside)
    assert "funding_z" not in write.context_values(history(ending=last), close_ns=just_inside + 1)


@pytest.mark.trace("REQ-WP-093")
def test_funding_z_exists_for_the_whole_interval_not_for_five_minutes_of_it() -> None:
    """The library's 5-minute default would make this vanish; the writer states its own bound."""
    values = write.context_values(history(ending=T0), close_ns=T0 + 7 * HOUR)
    assert "funding_z" in values


# --- freshness of the polled values ---------------------------------------------------------------


@pytest.mark.trace("REQ-WP-093")
def test_a_poll_older_than_the_bound_writes_no_open_interest_and_no_basis() -> None:
    close = close_of(0)
    stale = polled(close - sources.POLLED_STALENESS_NS - 1)
    fresh = polled(close - sources.POLLED_STALENESS_NS)

    assert not {"open_interest_usd", "basis_bps"} & set(
        write.context_values([stale], close_ns=close)
    )
    assert {"open_interest_usd", "basis_bps"} <= set(write.context_values([fresh], close_ns=close))


@pytest.mark.trace("REQ-WP-093")
def test_binance_open_interest_has_its_own_longer_bound() -> None:
    close = close_of(0)
    age = sources.POLLED_STALENESS_NS + 5 * MINUTE
    assert age <= sources.OPEN_INTEREST_STALENESS_NS
    oi = polled(
        close - age, mark=None, index=None, rate=None, source="binance-rest-oi", venue="binance"
    )
    mark = polled(close - MINUTE, usd=None, venue="binance")

    values = write.context_values([oi, mark], close_ns=close)

    assert values["open_interest_usd"] == 1_000.0
    assert "basis_bps" in values


@pytest.mark.trace("REQ-WP-093")
def test_a_state_without_the_field_leaves_that_feature_absent() -> None:
    no_oi = polled(close_of(0) - MINUTE, usd=None)
    no_prices = polled(close_of(0) - MINUTE, mark=None, index=None)
    assert "open_interest_usd" not in write.context_values([no_oi], close_ns=close_of(0))
    assert "basis_bps" not in write.context_values([no_prices], close_ns=close_of(0))


@pytest.mark.trace("REQ-WP-093")
def test_no_states_at_all_is_no_values() -> None:
    assert write.context_values([], close_ns=close_of(0)) == {}


# --- the series association -----------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-093")
def test_a_spot_series_is_given_its_venues_perpetual_and_unknown_series_are_given_nothing() -> None:
    assert sources.perpetual_for("binance", "BTCUSDT") == "BTCUSDT"
    assert sources.perpetual_for("binance", "ETHUSDT") == "ETHUSDT"
    assert sources.perpetual_for("okx", "BTC-USDT-SWAP") == "BTC-USDT-SWAP"
    assert sources.perpetual_for("bybit", "BTCUSDT") == "BTCUSDT"
    assert sources.perpetual_for("binance", "DOGEUSDT") is None
    assert sources.perpetual_for("kraken", "BTCUSDT") is None


# --- the pass -------------------------------------------------------------------------------------


def make_bar(
    index: int,
    *,
    venue: str = "binance",
    symbol: str = "BTCUSDT",
    timeframe_ns: int = MINUTE,
    is_final: bool = True,
    start: int = T0 + 1 * HOUR,
) -> Bar:
    open_time = start + index * timeframe_ns
    price = Decimal("100")
    return Bar(
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        open_time_ns=open_time,
        close_time_ns=open_time + timeframe_ns,
        open=price,
        high=price,
        low=price,
        close=price,
        volume_base=Decimal(1),
        volume_quote=price,
        trade_count=1,
        aggressive_buy_base=Decimal(1),
        aggressive_sell_base=Decimal(0),
        delta_base=Decimal(1),
        vwap=price,
        high_time_ns=open_time,
        low_time_ns=open_time,
        first_trade_id=str(index),
        last_trade_id=str(index),
        is_final=is_final,
    )


def store(catalog: Catalog, states: list[DerivativesState]) -> None:
    sink = state_table.DerivativesStateSink(state_table.table_for(catalog))
    for item in states:
        sink(item)
    sink.flush()


def features_for(
    catalog: Catalog, venue: str, symbol: str, timeframe_ns: int
) -> dict[int, dict[str, float]]:
    rows = features_table.features_table_for(catalog).read().to_pylist()
    out: dict[int, dict[str, float]] = {}
    for row in rows:
        if (row["venue"], row["symbol"], row["timeframe_ns"]) == (venue, symbol, timeframe_ns):
            out.setdefault(row["at_ns"], {})[row["feature_name"]] = row["value"]
    return out


def history_for(venue: str, symbol: str) -> list[DerivativesState]:
    return [settled(h.meta.event_time_ns, h.funding_rate or 0.0, venue, symbol) for h in history()]


def binance_states() -> list[DerivativesState]:
    return [
        settled(s.meta.event_time_ns, s.funding_rate or 0.0, venue="binance") for s in history()
    ] + [
        polled(
            s.meta.event_time_ns, usd=s.open_interest_usd, mark=str(s.mark_price), venue="binance"
        )
        for s in series()
    ]


@pytest.mark.trace("REQ-WP-093")
def test_the_pass_writes_the_three_features_at_every_final_bars_close(catalog: Catalog) -> None:
    store(catalog, binance_states())
    bars = [make_bar(i) for i in range(5, 15)]

    written = write.write_context_features(catalog, bars)

    got = features_for(catalog, "binance", "BTCUSDT", MINUTE)
    assert sorted(got) == sorted(b.close_time_ns for b in bars)
    assert all(set(v) == set(FEATURES) for v in got.values())
    assert written == len(bars) * 3


@pytest.mark.trace("REQ-WP-093")
def test_the_pass_skips_bars_that_are_not_final(catalog: Catalog) -> None:
    store(catalog, binance_states())
    write.write_context_features(catalog, [make_bar(5), make_bar(6, is_final=False)])
    assert sorted(features_for(catalog, "binance", "BTCUSDT", MINUTE)) == [
        make_bar(5).close_time_ns
    ]


@pytest.mark.trace("REQ-WP-093")
def test_every_timeframe_gets_its_value_as_of_its_own_close(catalog: Catalog) -> None:
    store(catalog, binance_states())
    five = [make_bar(i, timeframe_ns=5 * MINUTE) for i in range(2, 6)]

    write.write_context_features(catalog, five)

    got = features_for(catalog, "binance", "BTCUSDT", 5 * MINUTE)
    assert sorted(got) == sorted(b.close_time_ns for b in five)
    close = five[0].close_time_ns
    assert (
        got[close]["open_interest_usd"]
        == write.context_values(
            sorted(binance_states(), key=lambda s: s.meta.event_time_ns), close_ns=close
        )["open_interest_usd"]
    )


@pytest.mark.trace("REQ-WP-093")
def test_a_second_pass_over_the_same_bars_writes_nothing(catalog: Catalog) -> None:
    store(catalog, binance_states())
    bars = [make_bar(i) for i in range(5, 15)]
    write.write_context_features(catalog, bars)

    assert write.write_context_features(catalog, bars) == 0
    assert len(features_table.features_table_for(catalog).read().to_pylist()) == len(bars) * 3


@pytest.mark.trace("REQ-WP-093")
def test_a_later_pass_writes_only_the_new_bars(catalog: Catalog) -> None:
    store(catalog, binance_states())
    write.write_context_features(catalog, [make_bar(i) for i in range(5, 10)])

    written = write.write_context_features(catalog, [make_bar(i) for i in range(5, 12)])

    assert written == 2 * 3


@pytest.mark.trace("REQ-WP-093")
def test_a_series_with_no_perpetual_or_no_states_gets_nothing(catalog: Catalog) -> None:
    store(catalog, binance_states())
    bars = [make_bar(5, symbol="DOGEUSDT"), make_bar(5, venue="okx", symbol="BTC-USDT-SWAP")]

    assert write.write_context_features(catalog, bars) == 0


@pytest.mark.trace("REQ-WP-093")
def test_a_series_that_is_not_given_a_perpetual_is_ignored_even_if_states_exist_under_its_name(
    catalog: Catalog,
) -> None:
    store(
        catalog,
        [polled(s.meta.event_time_ns, venue="binance", symbol="DOGEUSDT") for s in series()]
        + history_for("binance", "DOGEUSDT"),
    )

    assert write.write_context_features(catalog, [make_bar(5, symbol="DOGEUSDT")]) == 0


@pytest.mark.trace("REQ-WP-093")
def test_bars_before_any_observation_get_nothing_not_zeros(catalog: Catalog) -> None:
    store(catalog, [s for s in binance_states() if s.meta.source != "binance-funding-history"])
    early = make_bar(-30)  # half an hour before the first poll

    assert write.write_context_features(catalog, [early]) == 0


@pytest.mark.trace("REQ-WP-093")
def test_the_pass_does_not_touch_the_flow_features(catalog: Catalog) -> None:
    store(catalog, binance_states())
    table = features_table.features_table_for(catalog)
    table.append(
        features_table.feature_rows(
            venue="binance",
            symbol="BTCUSDT",
            timeframe_ns=MINUTE,
            at_ns=make_bar(5).close_time_ns,
            values={"cvd_base": 1.0, "delta_base": 1.0},
        )
    )
    before = table.read().to_pylist()

    write.write_context_features(catalog, [make_bar(5)])

    after = table.read().to_pylist()
    assert [r for r in after if r["feature_name"] in ("cvd_base", "delta_base")] == before


@pytest.mark.trace("REQ-WP-093")
def test_a_failing_series_is_reported_and_does_not_stop_the_others(
    catalog: Catalog, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    store(catalog, binance_states())
    original = write.context_values

    def explode(
        states: list[DerivativesState], *, close_ns: int, **kwargs: object
    ) -> dict[str, float]:
        if states and states[0].meta.symbol == "ETHUSDT":
            raise RuntimeError("boom")
        return original(states, close_ns=close_ns, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(write, "context_values", explode)
    store(
        catalog,
        [
            s.model_copy(update={"meta": s.meta.model_copy(update={"symbol": "ETHUSDT"})})
            for s in binance_states()
        ],
    )

    write.write_context_features(catalog, [make_bar(5, symbol="ETHUSDT"), make_bar(5)])

    assert features_for(catalog, "binance", "BTCUSDT", MINUTE)
    assert "ETHUSDT" in capsys.readouterr().out
