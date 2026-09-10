"""PRD §32's four health states, and what an absent reading means (REQ-WP-035)."""

from __future__ import annotations

import pytest

from channelflow.health import HealthReadings, HealthState, HealthThresholds, assess

BASE_NS = 1788838800000000000
SECOND_NS = 1_000_000_000


def limits(**overrides: object) -> HealthThresholds:
    fields: dict[str, object] = {
        "reconnects": 2,
        "missing_bars": 0,
        "stale_ns": 5 * SECOND_NS,
        "gap_rate": 0.0,
        "duplicate_rate": 0.01,
    }
    fields.update(overrides)
    return HealthThresholds(**fields)  # type: ignore[arg-type]


def healthy() -> HealthReadings:
    return HealthReadings(
        reconnects=0,
        missing_bars=0,
        stale_ns=0,
        gap_rate=0.0,
        duplicate_rate=0.0,
    )


def check(readings: HealthReadings) -> HealthState:
    return assess(readings, feed="binance:BTCUSDT", at_ns=BASE_NS, thresholds=limits()).state


# --- nothing reported is not good news ---------------------------------------


@pytest.mark.trace("REQ-WP-035")
def test_nothing_reported_is_not_good_news() -> None:
    """The sharpest form of "absent is not zero" in this repository.

    A feed so broken it cannot report is the case this alerting exists for, and
    a default of GOOD is exactly what silences it: the silence looks identical
    to a healthy system.
    """
    health = assess(HealthReadings(), feed="binance:BTCUSDT", at_ns=BASE_NS, thresholds=limits())

    assert health.state is not HealthState.GOOD
    assert "nothing was reported" in health.reason


@pytest.mark.trace("REQ-WP-035")
def test_one_absent_reading_is_not_one_reading_within_its_limit() -> None:
    """The same rule one scale down. A feed reporting only its easiest metric
    must not look like one reporting all of them."""
    partial = HealthReadings(reconnects=0)

    assert check(partial) is not HealthState.GOOD


# --- four states, kept apart -------------------------------------------------


@pytest.mark.trace("REQ-WP-035")
def test_everything_within_its_limit_is_good() -> None:
    assert check(healthy()) is HealthState.GOOD


@pytest.mark.trace("REQ-WP-035")
def test_a_stale_feed_and_a_gappy_one_are_two_different_states() -> None:
    """§32's eligibility rules treat them differently -- a degraded confirmation
    lowers confidence, a stale book disqualifies a signal outright -- so one
    "unhealthy" would make those rules unimplementable."""
    stale = HealthReadings(**{**healthy().__dict__, "stale_ns": 30 * SECOND_NS})
    gappy = HealthReadings(**{**healthy().__dict__, "gap_rate": 0.2})

    assert check(stale) is HealthState.STALE
    assert check(gappy) is HealthState.INVALID


@pytest.mark.trace("REQ-WP-035")
def test_reconnects_and_missing_bars_degrade_rather_than_disqualify() -> None:
    churning = HealthReadings(**{**healthy().__dict__, "reconnects": 9})
    missing = HealthReadings(**{**healthy().__dict__, "missing_bars": 3})

    assert check(churning) is HealthState.DEGRADED
    assert check(missing) is HealthState.DEGRADED


@pytest.mark.trace("REQ-WP-035")
def test_the_worst_reading_decides_and_the_reason_names_it() -> None:
    both = HealthReadings(**{**healthy().__dict__, "reconnects": 9, "gap_rate": 0.2})

    health = assess(both, feed="binance:BTCUSDT", at_ns=BASE_NS, thresholds=limits())

    assert health.state is HealthState.INVALID
    assert "gap" in health.reason


@pytest.mark.trace("REQ-WP-035")
def test_the_worst_wins_even_when_a_milder_reading_is_checked_after_it() -> None:
    """The guard that "the worst decides" needs to be more than "the last one".

    A gap rate is checked before missing bars and is worse than it. An
    implementation that simply overwrote its running answer would report
    DEGRADED here and INVALID in the test above, and both would look right.
    """
    both = HealthReadings(**{**healthy().__dict__, "gap_rate": 0.2, "missing_bars": 3})

    health = assess(both, feed="binance:BTCUSDT", at_ns=BASE_NS, thresholds=limits())

    assert health.state is HealthState.INVALID
    assert "gap" in health.reason


@pytest.mark.trace("REQ-WP-035")
def test_the_states_are_ranked_worst_last() -> None:
    """Asserted directly rather than implied by the tests that use it.

    Mis-ordered, a stale feed outranks an invalid one and every assessment still
    returns a plausible state -- a defect with no symptom.
    """
    assert HealthState.GOOD < HealthState.DEGRADED < HealthState.STALE < HealthState.INVALID


@pytest.mark.trace("REQ-WP-035")
def test_the_thresholds_are_arguments() -> None:
    """§32 lists nine metrics and no values. A constant here would be a research
    default wearing a decision's clothes (§13.11)."""
    churning = HealthReadings(**{**healthy().__dict__, "reconnects": 9})

    strict = assess(churning, feed="f", at_ns=BASE_NS, thresholds=limits(reconnects=2))
    lenient = assess(churning, feed="f", at_ns=BASE_NS, thresholds=limits(reconnects=20))

    assert strict.state is HealthState.DEGRADED
    assert lenient.state is HealthState.GOOD


@pytest.mark.trace("REQ-WP-035")
def test_the_reading_carries_the_feed_and_the_instant() -> None:
    health = assess(healthy(), feed="binance:BTCUSDT", at_ns=BASE_NS, thresholds=limits())

    assert health.feed == "binance:BTCUSDT"
    assert health.observed_at_ns == BASE_NS
