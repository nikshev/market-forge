"""What the collector stores from each venue's REST answers (REQ-WP-093).

The fixtures are the three venues' real public answers, recorded 2026-10-11
(`tests/fixtures/context/README.md` gives each URL). What is pinned here is what a state's two
times, its USD open interest and its settled funding rows are made of, because the worker's
point-in-time rules are only as good as the rows they read.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.connectors.binance import normalize as binance
from channelflow.connectors.bybit import normalize as bybit
from channelflow.connectors.okx import normalize as okx

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "context"
MS = 1_000_000


def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text())


# --- Binance: two kinds of state, because the two answers are about two instants ---------------


@pytest.mark.trace("REQ-WP-093")
def test_binance_mark_index_and_funding_come_from_premium_index_at_the_venues_time() -> None:
    row = load("binance_premiumIndex")
    state = binance.futures_state(row, venue="binance", ingest_time_ns=9)

    assert state.meta.event_time_ns == int(row["time"]) * MS
    assert state.meta.ingest_time_ns == 9
    assert state.meta.source == "binance-rest"
    assert state.meta.market_type == "perp"
    assert state.mark_price == Decimal(row["markPrice"])
    assert state.index_price == Decimal(row["indexPrice"])
    assert state.funding_rate == float(row["lastFundingRate"])
    assert state.next_funding_time_ns == int(row["nextFundingTime"]) * MS
    expected = float((Decimal(row["markPrice"]) / Decimal(row["indexPrice"]) - 1) * 10_000)
    assert state.basis_bps == pytest.approx(expected)
    # This answer says nothing about open interest, so the state does not either.
    assert state.open_interest_usd is None
    assert state.open_interest_base is None


@pytest.mark.trace("REQ-WP-093")
def test_binance_open_interest_usd_is_the_figure_the_venue_reports_at_the_buckets_time() -> None:
    rows = load("binance_openInterestHist")
    newest = max(rows, key=lambda r: r["timestamp"])
    state = binance.open_interest_state(newest, venue="binance", ingest_time_ns=9)

    assert state.meta.event_time_ns == int(newest["timestamp"]) * MS
    assert state.meta.source == "binance-rest-oi"
    assert state.open_interest_usd == float(newest["sumOpenInterestValue"])
    assert state.open_interest_base == float(newest["sumOpenInterest"])
    # A price of our choosing is never multiplied in: the USD figure is the venue's.
    assert state.mark_price is None and state.funding_rate is None


@pytest.mark.trace("REQ-WP-093")
def test_binance_state_refuses_an_answer_missing_a_field_rather_than_defaulting_it() -> None:
    row = dict(load("binance_premiumIndex"))
    del row["markPrice"]
    with pytest.raises(binance.NormalizationError, match="markPrice"):
        binance.futures_state(row, venue="binance", ingest_time_ns=1)


# --- Bybit: the venue's own clock, not ours -----------------------------------------------------


@pytest.mark.trace("REQ-WP-093")
def test_bybit_state_is_stamped_with_the_responses_time_not_the_receipt() -> None:
    body = load("bybit_tickers")
    ticker = body["result"]["list"][0]
    state = bybit.derivatives_state(
        ticker,
        venue="bybit",
        market_type="perp",
        ingest_time_ns=123,
        event_time_ns=int(body["time"]) * MS,
    )

    assert state.meta.event_time_ns == int(body["time"]) * MS
    assert state.meta.ingest_time_ns == 123
    assert state.open_interest_usd == float(ticker["openInterestValue"])


@pytest.mark.trace("REQ-WP-093")
def test_bybit_state_without_a_venue_time_keeps_its_old_behaviour() -> None:
    ticker = load("bybit_tickers")["result"]["list"][0]
    state = bybit.derivatives_state(ticker, venue="bybit", market_type="perp", ingest_time_ns=77)
    assert state.meta.event_time_ns == 77


# --- OKX: four answers, one state; the contract value comes from the instrument ----------------


@pytest.mark.trace("REQ-WP-093")
def test_okx_contract_value_is_read_from_the_instruments_answer_not_assumed() -> None:
    body = load("okx_instruments")
    assert okx.contract_value(body, inst_id="BTC-USDT-SWAP") == Decimal(body["data"][0]["ctVal"])


@pytest.mark.trace("REQ-WP-093")
def test_okx_contract_value_refuses_an_instrument_the_answer_does_not_contain() -> None:
    with pytest.raises(okx.UnknownContractValue):
        okx.contract_value(load("okx_instruments"), inst_id="X-USDT-SWAP")


# --- Settled funding: one row per settlement, the venue's settled rate -------------------------


def _history_cases() -> list[tuple[str, Any, Any, str]]:
    return [
        (
            "binance",
            lambda: binance.funding_history(
                load("binance_fundingRate"), venue="binance", ingest_time_ns=5
            ),
            load("binance_fundingRate"),
            "fundingTime",
        ),
        (
            "bybit",
            lambda: bybit.funding_history(
                load("bybit_funding_history")["result"]["list"],
                venue="bybit",
                market_type="perp",
                ingest_time_ns=5,
            ),
            load("bybit_funding_history")["result"]["list"],
            "fundingRateTimestamp",
        ),
        (
            "okx",
            lambda: okx.funding_history(
                load("okx_funding_history")["data"],
                venue="okx",
                market_type="perp",
                ingest_time_ns=5,
            ),
            load("okx_funding_history")["data"],
            "fundingTime",
        ),
    ]


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize(("venue", "build", "raw", "time_key"), _history_cases())
def test_every_venues_history_becomes_one_settled_row_per_settlement(
    venue: str, build: Any, raw: list[dict[str, Any]], time_key: str
) -> None:
    states = build()

    assert len(states) == len(raw)
    for state in states:
        assert state.meta.source == f"{venue}-funding-history"
        # The interval ended at the settlement and the rate is public from then on: the row is
        # dated there, and `settled_funding` reads it as settled at that very instant.
        assert state.meta.event_time_ns == state.next_funding_time_ns
        assert state.funding_rate is not None
        assert state.mark_price is None and state.open_interest_usd is None
        assert state.meta.ingest_time_ns == 5
    assert {s.meta.event_time_ns for s in states} == {int(r[time_key]) * MS for r in raw}


@pytest.mark.trace("REQ-WP-093")
def test_okx_history_uses_the_realized_rate_not_the_formula_rate() -> None:
    raw = [dict(load("okx_funding_history")["data"][0])]
    raw[0]["fundingRate"] = "0.5"  # a different number under the other name
    raw[0]["realizedRate"] = "-0.0000154175824147"
    (state,) = okx.funding_history(raw, venue="okx", market_type="perp", ingest_time_ns=1)
    assert state.funding_rate == float("-0.0000154175824147")


@pytest.mark.trace("REQ-WP-093")
@pytest.mark.parametrize("venue", ["binance", "bybit", "okx"])
def test_a_history_row_with_no_rate_is_refused_not_stored_as_zero(venue: str) -> None:
    broken: dict[str, Any] = {"fundingTime": "1", "fundingRateTimestamp": "1", "symbol": "X"}
    with pytest.raises(
        (binance.NormalizationError, bybit.NormalizationError, okx.NormalizationError)
    ):
        if venue == "binance":
            binance.funding_history([broken], venue=venue, ingest_time_ns=1)
        elif venue == "bybit":
            bybit.funding_history([broken], venue=venue, market_type="perp", ingest_time_ns=1)
        else:
            okx.funding_history([broken], venue=venue, market_type="perp", ingest_time_ns=1)
