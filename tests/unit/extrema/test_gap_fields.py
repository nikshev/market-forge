"""The confirmed extremum states its lag in time as well as in bars (REQ-WP-087).

FR-007: a lag in bars is only meaningful on a contiguous series (PRD section 32
makes missing bars a health metric), so a confirmation also carries the
nanoseconds between the turn's bar and the confirming bar -- the number that
still means what it says when the series has a hole in it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from channelflow.extrema.models import ConfirmedExtremum

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1_788_838_800_000_000_000

TURN_NS = BASE_NS + 10 * MINUTE_NS
CONFIRM_NS = BASE_NS + 14 * MINUTE_NS


def confirmed(**overrides: object) -> ConfirmedExtremum:
    fields: dict[str, object] = {
        "extremum_id": uuid.uuid5(uuid.NAMESPACE_OID, "gap-fields"),
        "instrument_id": "binance:BTCUSDT",
        "timeframe_ns": MINUTE_NS,
        "extremum_type": "HIGH",
        "extremum_time_ns": TURN_NS,
        "known_at_ns": CONFIRM_NS,
        "price": Decimal("112000.10"),
        "confirmation_method": "directional_change",
        "confirmation_lag_bars": 4,
        "reversal_bps": 45.0,
        "threshold_bps": 30.0,
    }
    fields.update(overrides)
    return ConfirmedExtremum(**fields)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-087")
def test_a_confirmed_extremum_states_its_confirmation_lag_in_time() -> None:
    """FR-007, SC-004: the lag is confirming bar close minus turn bar close."""
    extremum = confirmed(confirmation_lag_ns=CONFIRM_NS - TURN_NS)

    assert extremum.confirmation_lag_ns == 4 * MINUTE_NS
    assert extremum.confirmation_lag_bars == 4

    # Round-trips: the record a chart or a backtest reads back carries the same
    # time lag the detector wrote. Frozen plus extra="forbid" mean the only way
    # to lose the field would be a different constructor path.
    again = ConfirmedExtremum.model_validate(extremum.model_dump())

    assert again.confirmation_lag_ns == extremum.confirmation_lag_ns
    assert again == extremum


@pytest.mark.trace("REQ-WP-087")
def test_confirmation_lag_ns_defaults_to_zero_when_a_producer_has_not_computed_it() -> None:
    """The field is optional at construction, and cannot be negative.

    Producers that do not hold both bar timestamps at the call site still build
    a record; 0 is the sentinel they leave behind, not a measured lag, and a
    negative value is refused because the confirming bar cannot precede the
    turn.
    """
    extremum = confirmed()

    assert extremum.confirmation_lag_ns == 0

    with pytest.raises(ValidationError):
        confirmed(confirmation_lag_ns=-1)
