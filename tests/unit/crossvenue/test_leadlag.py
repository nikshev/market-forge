"""PRD section 17.2's lead-lag features (REQ-WP-016).

    "Do not convert correlation to trading rule without OOS validation."

That cannot be checked as written. What can be checked is that the signal path
does not import this module — ADR-040, and the third use of a shape that has
worked twice before.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.crossvenue.leadlag import (
    DEFAULT_WINDOWS_NS,
    SECOND_NS,
    lagged_correlation,
    venue_return,
)

from .conftest import at

#: Packages that make trading decisions. Named explicitly rather than matched
#: by pattern: a loose definition would drift as packages are added, and
#: silently stop covering the one that mattered.
SIGNAL_PATH = ("signals", "alerting", "stops")


def prices(*pairs: tuple[int, str]) -> list[tuple[int, Decimal]]:
    return [(at(second), Decimal(price)) for second, price in pairs]


@pytest.mark.trace("REQ-WP-016")
def test_a_return_uses_only_prices_at_or_before_the_instant() -> None:
    """SC-007, FR-009, Principle I.

    The price at second 30 exists in the series and is invisible at second 12.
    A return that used it would give roughly 1.2 instead of 0.01 — the leak
    this whole repository is built against, and it would look like an
    unusually good signal rather than like a bug.
    """
    import math

    series = prices((0, "3000"), (10, "3030"), (30, "9999"))

    result = venue_return(series, venue_id="binance", window_ns=10 * SECOND_NS, at_ns=at(12))

    assert result is not None
    assert result.value == pytest.approx(math.log(3030 / 3000))
    assert result.value < 0.1, "9999 would have made this about 1.2"


@pytest.mark.trace("REQ-WP-016")
def test_a_return_measures_the_window() -> None:
    """FR-009. Log return from the window's opening price to the latest."""
    import math

    series = prices((0, "3000"), (10, "3030"))

    result = venue_return(series, venue_id="binance", window_ns=20 * SECOND_NS, at_ns=at(20))

    assert result is not None
    assert result.value == pytest.approx(math.log(3030 / 3000))


@pytest.mark.trace("REQ-WP-016")
def test_a_window_with_nothing_to_open_against_is_absent_not_zero() -> None:
    """FR-009.

    Zero would read as "the venue did not move", which is a fact about a quiet
    market rather than about a missing observation. A window reaching back
    before the data starts has no opening price, and reporting a ten-second
    return computed over five seconds of data would be a mislabelled number.
    """
    series = prices((10, "3000"))

    assert venue_return(series, venue_id="b", window_ns=SECOND_NS, at_ns=at(10)) is None


@pytest.mark.trace("REQ-WP-016")
def test_every_window_the_prd_names_is_available() -> None:
    """FR-009, PRD section 17.2's 1/5/10 s."""
    assert DEFAULT_WINDOWS_NS == (SECOND_NS, 5 * SECOND_NS, 10 * SECOND_NS)


@pytest.mark.trace("REQ-WP-016")
def test_a_lagged_correlation_aligns_the_series() -> None:
    """SC-007, FR-010. A leader whose moves the follower repeats one step later
    correlates at lag 1 and not at lag 0."""
    leader = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
    follower = [0.0, 1.0, -1.0, 1.0, -1.0, 1.0]

    at_lag_one = lagged_correlation(leader, follower, leader_id="a", follower_id="b", lag=1)
    at_lag_zero = lagged_correlation(leader, follower, leader_id="a", follower_id="b", lag=0)

    assert at_lag_one is not None and at_lag_zero is not None
    assert at_lag_one.value > 0.9
    assert at_lag_one.value > at_lag_zero.value


@pytest.mark.trace("REQ-WP-016")
def test_too_few_pairs_gives_no_correlation() -> None:
    """FR-010, the same reasoning as ADR-026's z-score: a correlation of zero
    means "no linear relationship", not "we could not compute one"."""
    assert lagged_correlation([1.0, 2.0], [1.0, 2.0], leader_id="a", follower_id="b", lag=0) is None


@pytest.mark.trace("REQ-WP-016")
def test_a_constant_series_gives_no_correlation() -> None:
    """FR-010. Zero variance has no correlation to report."""
    flat = [1.0, 1.0, 1.0, 1.0]

    assert lagged_correlation(flat, flat, leader_id="a", follower_id="b", lag=0) is None


@pytest.mark.trace("REQ-WP-016")
def test_a_negative_lag_is_refused() -> None:
    """Direction is expressed by which series is the leader; a negative lag
    would be a second way to say the same thing, and one of them wrong."""
    with pytest.raises(ValueError, match="negative"):
        lagged_correlation([1.0] * 5, [1.0] * 5, leader_id="a", follower_id="b", lag=-1)


@pytest.mark.trace("REQ-WP-016")
def test_every_output_declares_itself_research_only() -> None:
    """FR-011, ADR-040.

    Carried on the value rather than in documentation, so a reader who found
    one in a signal would see it there.
    """
    result = venue_return(
        prices((0, "3000"), (10, "3030")), venue_id="b", window_ns=20 * SECOND_NS, at_ns=at(20)
    )
    correlation = lagged_correlation(
        [1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0], leader_id="a", follower_id="b", lag=0
    )

    assert result is not None and result.research_only
    assert correlation is not None and correlation.research_only


@pytest.mark.trace("REQ-WP-016")
def test_no_signal_path_module_imports_lead_lag() -> None:
    """SC-008, FR-011, ADR-040, PRD section 17.2.

    The prohibition cannot be checked as written — the conversion happens in
    someone's head and lands as an ordinary-looking condition. What can be
    checked is that a rule built on lead-lag has no way to reach it.

    Narrower than the prohibition, and honestly so: someone can still copy a
    correlation into a spreadsheet and hard-code a threshold. What they cannot
    do is wire it in and keep the suite green.
    """
    root = Path(__file__).resolve().parents[3] / "src" / "channelflow"

    for package in SIGNAL_PATH:
        for module in (root / package).glob("*.py"):
            source = module.read_text()
            assert "leadlag" not in source, (
                f"{package}/{module.name} references the lead-lag module; PRD section "
                "17.2 forbids converting correlation to a trading rule without OOS "
                "validation, and ADR-040 keeps the signal path clear of it"
            )


@pytest.mark.trace("REQ-WP-016")
def test_the_signal_path_packages_all_exist() -> None:
    """Guard on the guard.

    The test above passes vacuously if a package is renamed and the list is not
    updated — which is exactly how a check like this rots.
    """
    root = Path(__file__).resolve().parents[3] / "src" / "channelflow"

    for package in SIGNAL_PATH:
        assert (root / package).is_dir(), f"{package} no longer exists; update SIGNAL_PATH"
        assert list((root / package).glob("*.py")), f"{package} has no modules"


@pytest.mark.trace("REQ-WP-016")
def test_lead_lag_is_not_re_exported_from_the_package_root() -> None:
    """ADR-040. `from channelflow.crossvenue import ...` cannot reach it by
    accident; reaching it takes naming the module, which is the deliberate act
    the ADR wants to keep visible."""
    import channelflow.crossvenue as crossvenue

    assert not any("lagged_correlation" in name for name in crossvenue.__all__)
    assert not any("venue_return" in name for name in crossvenue.__all__)
