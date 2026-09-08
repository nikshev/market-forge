"""The decimal precision policy stays set (ADR-006, REQ-WP-002).

Python's default context rounds at 28 significant digits. That silently
truncated a venue price during REQ-WP-005, and the loss was in
`price * quantity` -- so it reached the connector's notional_quote too, not
just one division. The policy is a single line in `channelflow/__init__.py`,
and a single line is exactly what gets removed by someone tidying imports.
"""

from __future__ import annotations

from decimal import Decimal, getcontext

import pytest

import channelflow


@pytest.mark.trace("REQ-WP-002")
def test_the_precision_policy_is_applied_on_import() -> None:
    assert getcontext().prec == channelflow.DECIMAL_PRECISION
    assert channelflow.DECIMAL_PRECISION >= 50, (
        "below about 50 digits, a venue price times a quantity can round"
    )


@pytest.mark.trace("REQ-WP-002")
def test_a_venue_price_times_a_quantity_keeps_every_digit() -> None:
    """The concrete case that exposed the default context."""
    price = Decimal("50000.123456789012345678901234")  # 29 significant digits
    assert price * Decimal("1") == price
    assert price * Decimal("2") == Decimal("100000.246913578024691357802468")


@pytest.mark.trace("REQ-WP-002")
def test_division_is_still_not_claimed_to_be_exact() -> None:
    """ADR-006 is explicit that 60 digits reduces loss rather than abolishing
    it. Asserting that keeps the claim honest if someone later reads the
    precision as a guarantee of exactness."""
    third = Decimal(1) / Decimal(3)
    assert third * 3 != Decimal(1), (
        "division does not terminate; the policy reduces loss, it does not abolish it"
    )
