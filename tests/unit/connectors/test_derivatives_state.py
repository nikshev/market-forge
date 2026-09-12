"""Bybit and OKX report funding and open interest comparably (REQ-WP-049).

One fixture, both venues, captured in a single pass -- because the whole point is
that they disagree about units and about names, and neither disagreement is
demonstrable from one venue alone.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.connectors.bybit.normalize import NormalizationError as BybitError
from channelflow.connectors.bybit.normalize import derivatives_state as bybit_state
from channelflow.connectors.okx.normalize import (
    AssembledDerivatives,
    NormalizationError,
    StaleAssembly,
    UnknownContractValue,
)
from channelflow.connectors.okx.normalize import derivatives_state as okx_state
from channelflow.connectors.okx.normalize import (
    open_interest_base as okx_open_interest_base,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "derivatives" / "bybit_okx.jsonl"

HOUR_NS = 3_600 * 1_000_000_000
GENEROUS_SPREAD_NS = 30 * 1_000_000_000


def _rows() -> list[dict[str, Any]]:
    assert FIXTURE.is_file(), (
        f"missing fixture {FIXTURE}; regenerate with tools.record.derivatives_capture"
    )
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


ROWS = _rows()
BYBIT = [row for row in ROWS if row["kind"] == "bybit_ticker"]
OKX = [row for row in ROWS if row["kind"] == "okx_derivatives"]
PAIRS = list(zip(BYBIT, OKX, strict=True))


def _okx(row: dict[str, Any], **overrides: Any) -> AssembledDerivatives:
    arguments: dict[str, Any] = {
        "funding": row["funding"],
        "open_interest": row["open_interest"],
        "mark": row["mark"],
        "index": row["index"],
        "contract_value": Decimal(row["instrument"]["ctVal"]),
        "venue": "okx",
        "market_type": "perp",
        "ingest_time_ns": 7,
        "max_spread_ns": GENEROUS_SPREAD_NS,
    }
    return okx_state(**{**arguments, **overrides})


def _bybit(row: dict[str, Any]) -> Any:
    return bybit_state(row["body"], venue="bybit", market_type="perp", ingest_time_ns=7)


# --- both venues produce the same shape ---------------------------------------


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("row", BYBIT, ids=[row["symbol"] for row in BYBIT])
def test_bybit_normalizes_into_the_shared_derivatives_state(row: dict[str, Any]) -> None:
    state = _bybit(row)
    assert state.meta.venue == "bybit"
    assert state.meta.symbol == row["symbol"]
    assert state.mark_price == Decimal(row["body"]["markPrice"])
    assert state.index_price == Decimal(row["body"]["indexPrice"])
    assert state.funding_rate == float(row["body"]["fundingRate"])
    assert state.open_interest_base == float(row["body"]["openInterest"])
    assert state.basis_bps is not None


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("row", OKX, ids=[row["inst_id"] for row in OKX])
def test_okx_normalizes_into_the_shared_derivatives_state(row: dict[str, Any]) -> None:
    state = _okx(row).state
    assert state.meta.venue == "okx"
    assert state.meta.symbol == row["inst_id"]
    assert state.mark_price == Decimal(row["mark"]["markPx"])
    assert state.index_price == Decimal(row["index"]["idxPx"])
    assert state.funding_rate == float(row["funding"]["fundingRate"])
    assert state.basis_bps is not None


# --- the same instant under opposite names ------------------------------------


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize(("bybit", "okx"), PAIRS, ids=[row["symbol"] for row in BYBIT])
def test_the_two_venues_settle_at_the_same_instant(
    bybit: dict[str, Any], okx: dict[str, Any]
) -> None:
    """The finding this requirement exists for.

    `OKX.fundingTime` is `Bybit.nextFundingTime`. Both normalize to the same
    field, and after normalization the two venues agree to the nanosecond.
    """
    assert _bybit(bybit).next_funding_time_ns == _okx(okx).state.next_funding_time_ns


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("row", OKX, ids=[row["inst_id"] for row in OKX])
def test_mapping_okx_by_field_name_would_be_a_settlement_period_late(
    row: dict[str, Any],
) -> None:
    """OKX's `nextFundingTime` is the settlement *after* the one its rate pays
    at, so a connector matching field names puts the venue eight hours out --
    and a dispersion computed across that boundary compares a settled rate
    against a forthcoming one."""
    used = int(row["funding"]["fundingTime"])
    by_name = int(row["funding"]["nextFundingTime"])
    assert by_name > used
    assert by_name - used == 8 * 3_600 * 1000


# --- contracts against base units ---------------------------------------------


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize(("bybit", "okx"), PAIRS, ids=[row["symbol"] for row in BYBIT])
def test_reading_okx_open_interest_as_base_units_is_wrong_by_the_contract_value(
    bybit: dict[str, Any], okx: dict[str, Any]
) -> None:
    """The error is exactly the contract value, so it is a hundredfold on BTC
    and tenfold on ETH -- and only visible against the other venue, because on
    its own the wrong figure is positive, ordered and believable.
    """
    correct = _okx(okx).state.open_interest_base
    naive = float(okx["open_interest"]["oi"])
    theirs = _bybit(bybit).open_interest_base
    contract_value = float(okx["instrument"]["ctVal"])
    assert correct is not None and theirs is not None

    # The invariant, which does not depend on which instrument this is.
    assert naive == pytest.approx(correct / contract_value)
    assert contract_value < 1, "this instrument needs no conversion; the test proves nothing"

    # Against the other venue: the corrected figure belongs to the same market,
    # the naive one does not.
    assert 0.1 < correct / theirs < 10
    assert naive / theirs > 5


@pytest.mark.trace("REQ-WP-049")
def test_the_contract_value_is_per_instrument_and_not_a_constant() -> None:
    """Which is why it is an argument rather than a number in this module."""
    values = {row["inst_id"]: row["instrument"]["ctVal"] for row in OKX}
    assert len(set(values.values())) > 1, f"every instrument shares a contract value: {values}"


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("row", OKX, ids=[row["inst_id"] for row in OKX])
def test_the_venue_s_own_base_figure_and_the_conversion_agree(row: dict[str, Any]) -> None:
    """OKX publishes both, which is a cross-check it gives away for free."""
    converted = Decimal(row["open_interest"]["oi"]) * Decimal(row["instrument"]["ctVal"])
    published = Decimal(row["open_interest"]["oiCcy"])
    assert abs(converted - published) / published < Decimal("0.0001")


@pytest.mark.trace("REQ-WP-049")
def test_a_contract_value_that_disagrees_with_the_venue_is_refused() -> None:
    """A disagreement means the value in hand is not the one the venue applied,
    which is worth refusing over rather than picking a side."""
    row = OKX[0]
    wrong = Decimal(row["instrument"]["ctVal"]) * 10
    with pytest.raises(UnknownContractValue, match="not the one it applied"):
        okx_open_interest_base(row["open_interest"], contract_value=wrong)


# --- four readings are not a snapshot -----------------------------------------


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("row", OKX, ids=[row["inst_id"] for row in OKX])
def test_an_okx_state_carries_how_far_apart_its_readings_were(row: dict[str, Any]) -> None:
    assembled = _okx(row)
    assert assembled.spread_ns == assembled.newest_ns - assembled.oldest_ns
    assert assembled.spread_ns >= 0
    # And the state is stamped with the oldest: it is no fresher than its
    # stalest part, and the newest would claim a freshness none of it has.
    assert assembled.state.meta.event_time_ns == assembled.oldest_ns


@pytest.mark.trace("REQ-WP-049")
def test_readings_further_apart_than_the_bound_are_refused() -> None:
    """Across a fast move, a mark from one second and an index from the next
    give a basis neither moment had."""
    row = OKX[0]
    with pytest.raises(StaleAssembly, match="more than"):
        _okx(row, max_spread_ns=1)


@pytest.mark.trace("REQ-WP-049")
def test_the_spread_bound_has_no_default_and_must_be_positive() -> None:
    """How stale is too stale is a property of what the state is for, and a
    default would be this module deciding that for every caller."""
    row = OKX[0]
    for bound in (0, -1):
        with pytest.raises(ValueError, match="bound on their spread"):
            _okx(row, max_spread_ns=bound)


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("field", ["open_interest", "mark"])
def test_readings_for_a_different_instrument_are_refused(field: str) -> None:
    """Four endpoints means four chances to assemble a state from two markets."""
    row = OKX[0]
    other = dict(row[field]) | {"instId": "ETH-USDT-SWAP"}
    with pytest.raises(NormalizationError, match="not 'BTC-USDT-SWAP'"):
        _okx(row, **{field: other})


# --- absent is not zero --------------------------------------------------------


@pytest.mark.trace("REQ-WP-049")
def test_bybit_reports_an_empty_funding_rate_as_absent_not_zero() -> None:
    """This venue sends an empty string for "not applicable", and a market in
    balance is not a market with no funding mechanism ([[REQ-WP-031]])."""
    row = dict(BYBIT[0]["body"]) | {"fundingRate": "", "nextFundingTime": ""}
    state = bybit_state(row, venue="bybit", market_type="perp", ingest_time_ns=7)
    assert state.funding_rate is None
    assert state.next_funding_time_ns is None

    balanced = dict(BYBIT[0]["body"]) | {"fundingRate": "0"}
    assert (
        bybit_state(balanced, venue="bybit", market_type="perp", ingest_time_ns=7).funding_rate
        == 0.0
    )


@pytest.mark.trace("REQ-WP-049")
def test_okx_reports_an_empty_funding_rate_as_absent_not_zero() -> None:
    """The same rule as Bybit's, asserted separately because it is a separate
    code path and a venue that publishes no funding is not a venue whose funding
    is zero."""
    row = OKX[0]
    silent = dict(row["funding"]) | {"fundingRate": "", "fundingTime": ""}
    state = _okx(row, funding=silent).state
    assert state.funding_rate is None
    assert state.next_funding_time_ns is None

    balanced = dict(row["funding"]) | {"fundingRate": "0"}
    assert _okx(row, funding=balanced).state.funding_rate == 0.0


@pytest.mark.trace("REQ-WP-049")
def test_bybit_reports_an_absent_index_as_absent_and_computes_no_basis() -> None:
    row = {key: value for key, value in BYBIT[0]["body"].items() if key != "indexPrice"}
    state = bybit_state(row, venue="bybit", market_type="perp", ingest_time_ns=7)
    assert state.index_price is None
    assert state.basis_bps is None


# --- the basis is the same quantity on both venues -----------------------------


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("row", OKX, ids=[row["inst_id"] for row in OKX])
def test_the_venue_s_premium_is_not_the_basis_and_is_not_used(row: dict[str, Any]) -> None:
    """It looks like one. Measured, the two differ: the premium is averaged over
    a funding window and the basis is instantaneous, so substituting it would
    compare OKX's window against Bybit's instant under one name."""
    state = _okx(row).state
    assert state.basis_bps is not None
    premium_bps = float(row["funding"]["premium"]) * 10_000
    assert state.basis_bps != pytest.approx(premium_bps, abs=1e-9)


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize(("bybit", "okx"), PAIRS, ids=[row["symbol"] for row in BYBIT])
def test_both_venues_compute_the_basis_the_same_way(
    bybit: dict[str, Any], okx: dict[str, Any]
) -> None:
    """Same formula, same sign convention, so the two are comparable -- which is
    what the phase needs them for."""
    for state, mark_key, index_key, source in (
        (_bybit(bybit), "markPrice", "indexPrice", bybit["body"]),
        (_okx(okx).state, None, None, None),
    ):
        assert state.basis_bps is not None
        assert state.mark_price is not None and state.index_price is not None
        expected = float((state.mark_price / state.index_price - 1) * 10_000)
        assert state.basis_bps == pytest.approx(expected)
        if source is not None:
            assert state.mark_price == Decimal(source[mark_key])
            assert state.index_price == Decimal(source[index_key])


# --- time parsing (§35.6) ------------------------------------------------------


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize(("bybit", "okx"), PAIRS, ids=[row["symbol"] for row in BYBIT])
def test_milliseconds_become_nanoseconds_on_both_venues(
    bybit: dict[str, Any], okx: dict[str, Any]
) -> None:
    """Left unconverted a venue timestamp is still a plausible instant, in 1970."""
    assert _bybit(bybit).next_funding_time_ns == int(bybit["body"]["nextFundingTime"]) * 1_000_000
    assembled = _okx(okx)
    assert assembled.state.next_funding_time_ns == int(okx["funding"]["fundingTime"]) * 1_000_000
    assert assembled.oldest_ns % 1_000_000 == 0


@pytest.mark.trace("REQ-WP-049")
def test_the_settlement_is_a_whole_number_of_hours_from_the_epoch() -> None:
    """A weak check that survives a venue changing its schedule, and a strong one
    against a unit mistake: milliseconds read as nanoseconds would not land on an
    hour."""
    for row in BYBIT:
        settlement = _bybit(row).next_funding_time_ns
        assert settlement is not None
        assert settlement % HOUR_NS == 0


# --- malformed events (§35.6) --------------------------------------------------


@pytest.mark.trace("REQ-WP-049")
def test_a_ticker_without_a_symbol_is_refused() -> None:
    row = {key: value for key, value in BYBIT[0]["body"].items() if key != "symbol"}
    with pytest.raises(BybitError, match="symbol"):
        bybit_state(row, venue="bybit", market_type="perp", ingest_time_ns=7)


@pytest.mark.trace("REQ-WP-049")
@pytest.mark.parametrize("missing", ["ts", "oi", "oiCcy"])
def test_an_okx_reading_missing_a_required_field_is_refused(missing: str) -> None:
    row = OKX[0]
    broken = {key: value for key, value in row["open_interest"].items() if key != missing}
    with pytest.raises(NormalizationError, match=missing):
        _okx(row, open_interest=broken)


@pytest.mark.trace("REQ-WP-049")
def test_a_price_that_is_not_a_number_is_refused() -> None:
    row = BYBIT[0]
    broken = dict(row["body"]) | {"markPrice": "not a price"}
    with pytest.raises(BybitError, match="not a number"):
        bybit_state(broken, venue="bybit", market_type="perp", ingest_time_ns=7)


# --- provenance ----------------------------------------------------------------


@pytest.mark.trace("REQ-WP-049")
def test_both_venues_were_captured_in_one_pass() -> None:
    """The two disagreements are only demonstrable side by side, and only if the
    readings are close enough together to be about the same market."""
    capture = next(row for row in ROWS if row["kind"] == "capture")
    assert capture["elapsed_ns"] < 120 * 1_000_000_000
    assert len(BYBIT) == len(OKX) >= 2
