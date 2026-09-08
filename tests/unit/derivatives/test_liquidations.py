"""PRD section 16.4's liquidation aggregates (REQ-WP-013)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.derivatives import clusters, intensity, time_since_spike, window

from .conftest import BASE_NS, MINUTE_NS, liquidation


def at(minute: int) -> int:
    return BASE_NS + minute * MINUTE_NS


LIQUIDATIONS = [
    liquidation(at=10, side="long_liquidated", notional="100000", price="112000"),
    liquidation(at=11, side="long_liquidated", notional="50000", price="111900"),
    liquidation(at=12, side="short_liquidated", notional="30000", price="112100"),
    liquidation(at=60, side="short_liquidated", notional="900000", price="115000"),
]


@pytest.mark.trace("REQ-WP-013")
def test_sides_are_totalled_separately() -> None:
    """SC-005, FR-009. Netting them at source would lose the asymmetry that is
    the whole reason to track forced selling apart from volume."""
    result = window(LIQUIDATIONS, as_of_ns=at(15), window_ns=10 * MINUTE_NS)

    assert result.long_usd == Decimal("150000")
    assert result.short_usd == Decimal("30000")
    assert result.events == 3


@pytest.mark.trace("REQ-WP-013")
def test_the_window_excludes_what_is_outside_it() -> None:
    """FR-009, FR-013: event-time windows.

    `(as_of - window, as_of]`, half-open at the start. At minute 12 with a
    two-minute window that is minutes 11 and 12 -- so the 100,000 long
    liquidation at minute 10 sits exactly on the excluded edge.
    """
    result = window(LIQUIDATIONS, as_of_ns=at(12), window_ns=2 * MINUTE_NS)

    assert result.events == 2
    assert result.long_usd == Decimal("50000"), "minute 10's 100,000 is outside"
    assert result.short_usd == Decimal("30000")


@pytest.mark.trace("REQ-WP-013")
def test_the_imbalance_is_hand_computable() -> None:
    """SC-005. (150,000 - 30,000) / 180,000 = 0.666..."""
    result = window(LIQUIDATIONS, as_of_ns=at(15), window_ns=10 * MINUTE_NS)

    assert result.imbalance == pytest.approx(120_000 / 180_000)


@pytest.mark.trace("REQ-WP-013")
def test_the_imbalance_is_absent_when_nothing_was_liquidated() -> None:
    """SC-005, FR-007.

    Zero would mean both sides equally, which is a fact about a busy window.
    A quiet window is not a balanced one.
    """
    quiet = window(LIQUIDATIONS, as_of_ns=at(500), window_ns=MINUTE_NS)

    assert quiet.events == 0
    assert quiet.total_usd == Decimal(0)
    assert quiet.imbalance is None


@pytest.mark.trace("REQ-WP-013")
def test_a_zero_notional_print_counts_as_an_event() -> None:
    """The spec's fourth edge case: a zero-notional liquidation is a
    data-quality signal, not an absence."""
    odd = [liquidation(at=10, side="long_liquidated", notional="0")]

    result = window(odd, as_of_ns=at(15), window_ns=10 * MINUTE_NS)

    assert result.events == 1
    assert result.total_usd == Decimal(0)


@pytest.mark.trace("REQ-WP-013")
def test_intensity_is_absent_on_no_volume() -> None:
    """FR-007, FR-009."""
    assert intensity(Decimal("180000"), Decimal("0")) is None
    assert intensity(Decimal("180000"), Decimal("900000")) == pytest.approx(0.2)


@pytest.mark.trace("REQ-WP-013")
def test_clusters_group_by_relative_price_bucket() -> None:
    """FR-009, PRD section 16.4's "liquidation clusters by price".

    Buckets are relative to a reference price rather than absolute: an absolute
    bucket size tuned on one symbol is meaningless on another.
    """
    grouped = clusters(LIQUIDATIONS, bucket_bps=100.0, reference_price=Decimal("112000"))

    assert sum(grouped.values()) == Decimal("1080000")
    assert len(grouped) >= 2, "115,000 is far from 112,000 and must not share a bucket"


@pytest.mark.trace("REQ-WP-013")
def test_clusters_of_an_impossible_reference_are_empty() -> None:
    """A zero or negative reference has no bucket width to divide by."""
    assert clusters(LIQUIDATIONS, reference_price=Decimal("0")) == {}


@pytest.mark.trace("REQ-WP-013")
def test_time_since_a_spike_is_event_time() -> None:
    """FR-009, FR-013. The 900,000 print at minute 60 is the only spike."""
    since = time_since_spike(LIQUIDATIONS, as_of_ns=at(90), spike_usd=Decimal("500000"))

    assert since == 30 * MINUTE_NS


@pytest.mark.trace("REQ-WP-013")
def test_no_spike_is_absent_not_infinite() -> None:
    """FR-009.

    "No spike has been seen" and "a spike infinitely long ago" are different
    facts, and a caller plotting a sentinel would draw a line at whatever
    number we picked.
    """
    assert time_since_spike(LIQUIDATIONS, as_of_ns=at(90), spike_usd=Decimal("99999999")) is None


@pytest.mark.trace("REQ-WP-013")
def test_a_spike_after_the_instant_is_not_counted() -> None:
    """Principle I, in the one function here that scans the whole stream."""
    assert time_since_spike(LIQUIDATIONS, as_of_ns=at(30), spike_usd=Decimal("500000")) is None


@pytest.mark.trace("REQ-WP-013")
def test_the_derivatives_package_cannot_consult_a_clock() -> None:
    """SC-008, FR-012."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "derivatives"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
