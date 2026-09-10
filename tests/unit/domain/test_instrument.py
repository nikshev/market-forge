"""An instrument's trading rules (REQ-WP-021)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import Instrument, InstrumentRejected


def rules(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "venue": "binance",
        "symbol": "BTCUSDT",
        "market_type": "perp",
        "base_asset": "BTC",
        "quote_asset": "USDT",
        "tick_size": Decimal("0.10"),
        "step_size": Decimal("0.001"),
        "min_notional": Decimal("5"),
        "contract_size": Decimal("1"),
        "status": "TRADING",
    }
    base.update(overrides)
    return base


@pytest.mark.trace("REQ-WP-021")
def test_an_instrument_carries_every_rule_it_was_given() -> None:
    instrument = Instrument(**rules())  # type: ignore[arg-type]

    assert instrument.tick_size == Decimal("0.10")
    assert instrument.step_size == Decimal("0.001")
    assert instrument.min_notional == Decimal("5")
    assert instrument.contract_size == Decimal("1")


@pytest.mark.trace("REQ-WP-021")
@pytest.mark.parametrize("field", ["tick_size", "step_size", "min_notional"])
def test_a_rule_of_zero_is_refused(field: str) -> None:
    """A zero increment is not a smaller increment, it is a missing one -- and a
    price rounded to a tick of zero is a price rounded to nothing."""
    with pytest.raises(InstrumentRejected, match=field):
        Instrument(**rules(**{field: Decimal(0)}))  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-021")
@pytest.mark.parametrize("field", ["tick_size", "step_size", "min_notional"])
def test_a_negative_rule_is_refused(field: str) -> None:
    with pytest.raises(InstrumentRejected, match=field):
        Instrument(**rules(**{field: Decimal("-1")}))  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-021")
def test_an_empty_name_is_refused() -> None:
    """An instrument without a symbol cannot be told from another one."""
    with pytest.raises(InstrumentRejected, match="symbol"):
        Instrument(**rules(symbol=""))  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-021")
def test_a_spot_instrument_has_no_contract_size() -> None:
    """Absent, not one. A contract size of `1` would let a later calculation
    multiply by it and be right by accident, which is a worse failure than being
    wrong -- it survives review."""
    instrument = Instrument(**rules(market_type="spot", contract_size=None))  # type: ignore[arg-type]

    assert instrument.contract_size is None


@pytest.mark.trace("REQ-WP-021")
def test_a_contract_size_of_zero_is_refused() -> None:
    """Absent is a fact. Zero is a quantity nothing can be denominated in."""
    with pytest.raises(InstrumentRejected, match="contract_size"):
        Instrument(**rules(contract_size=Decimal(0)))  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-021")
def test_a_float_rule_is_refused() -> None:
    """PRD section 41 rule 9 is about realistic execution, and a tick size that
    went through binary floating point is not the venue's tick size."""
    with pytest.raises(InstrumentRejected, match="tick_size"):
        Instrument(**rules(tick_size=0.1))  # type: ignore[arg-type]
