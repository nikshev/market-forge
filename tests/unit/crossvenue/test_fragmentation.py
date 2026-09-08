"""PRD section 17.4 (REQ-WP-016)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.assets import VenueKind
from channelflow.crossvenue import (
    NoFillableVenue,
    best_execution_venue,
    concentration,
    depth_table,
)

from .conftest import executable


@pytest.mark.trace("REQ-WP-016")
def test_the_best_venue_is_chosen_by_all_in_cost_not_headline_price() -> None:
    """SC-009, FR-013, and the section's most expensive mistake.

    Binance shows the better executable price — 2999 against Uniswap's 3001 —
    and costs 40 bps all in against Uniswap's 8. The venue with the best
    headline is not the venue to trade on, and §18.14 forbids the comparison
    that conflates them.
    """
    choice = best_execution_venue(
        [
            executable("binance", price="2999", cost_bps=40.0),
            executable("uniswap", price="3001", cost_bps=8.0, kind=VenueKind.AMM_POOL),
        ]
    )

    assert choice.venue_id == "uniswap"
    assert choice.all_in_cost_bps == 8.0


@pytest.mark.trace("REQ-WP-016")
def test_a_venue_that_cannot_fill_is_excluded_and_reported() -> None:
    """SC-009, FR-013, the spec's fifth acceptance scenario.

    "Cannot fill" and "expensive" are different answers. A ranking that mixed
    them would put an unusable venue above a costly one whenever the costly one
    was costly enough.
    """
    choice = best_execution_venue(
        [
            executable("binance", price=None, cost_bps=None),
            executable("okx", price="3000", cost_bps=25.0),
        ]
    )

    assert choice.venue_id == "okx"
    assert "binance" in choice.excluded
    assert choice.considered == ("okx",)


@pytest.mark.trace("REQ-WP-016")
def test_no_venue_able_to_fill_is_refused() -> None:
    """FR-013. Returning the least bad of nothing would be a venue
    recommendation nobody can act on."""
    with pytest.raises(NoFillableVenue, match="every one was excluded"):
        best_execution_venue([executable("binance", price=None, cost_bps=None)])


@pytest.mark.trace("REQ-WP-016")
def test_an_empty_venue_list_is_refused() -> None:
    """FR-013."""
    with pytest.raises(NoFillableVenue):
        best_execution_venue([])


@pytest.mark.trace("REQ-WP-016")
def test_a_tie_breaks_deterministically() -> None:
    """Principle XI. Two runs over one set must agree, or a recommendation is
    not reproducible."""
    quotes = [
        executable("okx", price="3000", cost_bps=10.0),
        executable("binance", price="3000", cost_bps=10.0),
    ]

    assert best_execution_venue(quotes).venue_id == "binance"
    assert best_execution_venue(list(reversed(quotes))).venue_id == "binance"


@pytest.mark.trace("REQ-WP-016")
def test_concentration_rises_as_liquidity_gathers() -> None:
    """SC-010, FR-014.

    The Herfindahl index of depth shares. Chosen over "share of the largest
    venue" because that figure is unchanged whether the rest is split between
    two venues or twenty — and the difference is exactly what fragmentation
    means.
    """
    spread = concentration({"a": Decimal(1), "b": Decimal(1), "c": Decimal(1)})
    gathered = concentration({"a": Decimal(8), "b": Decimal(1), "c": Decimal(1)})

    assert spread < gathered
    assert spread == pytest.approx(1 / 3)


@pytest.mark.trace("REQ-WP-016")
def test_one_venue_is_maximum_concentration() -> None:
    """The spec's fifth edge case: correct, not degenerate — one venue holds
    all of it."""
    assert concentration({"a": Decimal(5)}) == pytest.approx(1.0)


@pytest.mark.trace("REQ-WP-016")
def test_no_depth_anywhere_is_not_concentrated() -> None:
    """Zero total depth has no shares to square, and returning 1.0 would read
    as "one venue holds everything"."""
    assert concentration({"a": Decimal(0), "b": Decimal(0)}) == 0.0


@pytest.mark.trace("REQ-WP-016")
def test_the_depth_table_covers_the_bands_the_prd_names() -> None:
    """FR-012, PRD section 17.4's "depth by venue at 10/25/50bps"."""
    rows = depth_table(
        {
            "binance": {10: Decimal(5), 25: Decimal(12), 50: Decimal(30)},
            "uniswap": {10: Decimal(2), 25: Decimal(6), 50: Decimal(20)},
        }
    )

    assert {r.band_bps for r in rows} == {10, 25, 50}
    assert len(rows) == 6
    assert [r.venue_id for r in rows[:3]] == ["binance"] * 3


@pytest.mark.trace("REQ-WP-016")
def test_a_venue_missing_a_band_is_simply_absent() -> None:
    """FR-012. Each venue is measured by its own executable-depth measure, and
    a band it cannot report is not a zero — zero depth is a fact about a
    market, not about a missing measurement."""
    rows = depth_table({"binance": {10: Decimal(5)}})

    assert len(rows) == 1
    assert rows[0].band_bps == 10


@pytest.mark.trace("REQ-WP-016")
def test_the_crossvenue_package_cannot_consult_a_clock() -> None:
    """SC-011, FR-016."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "crossvenue"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "time.monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
