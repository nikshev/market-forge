"""Not saying the same thing twice (REQ-WP-008).

PRD section 26.2: no repeated alert for the same setup state unless the score
improves by a delta, the signal changes phase, or the cooldown elapsed *and* a
new independent touch occurred.

The score clause is absent here -- ADR-016: there is no score until PRD section
43's ranker exists, so there is nothing to improve by a delta.

PRD section 25.6 counts duplicate alert rate as a quality metric, and the
reason is not tidiness: an alerter that repeats itself teaches its reader to
stop looking, which costs more than sending nothing at all.
"""

from __future__ import annotations

import pytest

from channelflow.alerting import DedupePolicy
from channelflow.signals import Candidate, CandidateState

from .conftest import BASE_NS, MINUTE_NS, confirmed_candidate

COOLDOWN_NS = 30 * MINUTE_NS


def _policy() -> DedupePolicy:
    return DedupePolicy(cooldown_ns=COOLDOWN_NS)


@pytest.mark.trace("REQ-WP-008")
def test_the_first_alert_for_a_setup_is_allowed(candidate: Candidate) -> None:
    assert _policy().should_send(candidate, at_ns=BASE_NS)


@pytest.mark.trace("REQ-WP-008")
def test_the_same_state_offered_again_is_refused(candidate: Candidate) -> None:
    """SC-003, FR-006."""
    policy = _policy()
    assert policy.should_send(candidate, at_ns=BASE_NS)

    assert not policy.should_send(candidate, at_ns=BASE_NS + MINUTE_NS)
    assert not policy.should_send(candidate, at_ns=BASE_NS + 2 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-008")
def test_a_phase_change_allows_a_new_alert(candidate: Candidate) -> None:
    """SC-004, FR-007. Section 26.2's second clause."""
    policy = _policy()
    policy.should_send(candidate, at_ns=BASE_NS)

    alerted = candidate.model_copy(update={"state": CandidateState.ALERTED})
    assert policy.should_send(alerted, at_ns=BASE_NS + MINUTE_NS)


@pytest.mark.trace("REQ-WP-008")
def test_an_elapsed_cooldown_alone_does_not_allow_a_new_alert(
    candidate: Candidate,
) -> None:
    """SC-004, FR-008. Section 26.2's third clause has two halves, and this is
    the half that is easy to drop.

    A cooldown that alone re-armed the alerter would repeat the same unchanged
    setup every half hour for as long as it stayed confirmed -- which, under
    ADR-010, is indefinitely.
    """
    policy = _policy()
    policy.should_send(candidate, at_ns=BASE_NS)

    assert not policy.should_send(candidate, at_ns=BASE_NS + COOLDOWN_NS + MINUTE_NS)


@pytest.mark.trace("REQ-WP-008")
def test_a_cooldown_plus_a_new_touch_allows_a_new_alert(candidate: Candidate) -> None:
    """FR-008's other half: both conditions, not either."""
    policy = _policy()
    policy.should_send(candidate, at_ns=BASE_NS)

    fresh = confirmed_candidate(opened_at_ns=BASE_NS + 60 * MINUTE_NS)
    assert policy.should_send(fresh, at_ns=BASE_NS + COOLDOWN_NS + MINUTE_NS)


@pytest.mark.trace("REQ-WP-008")
def test_a_new_touch_before_the_cooldown_is_refused(candidate: Candidate) -> None:
    """The symmetric half. A fresh candidate inside the cooldown is still a
    second message about the same symbol within minutes."""
    policy = _policy()
    policy.should_send(candidate, at_ns=BASE_NS)

    fresh = confirmed_candidate(opened_at_ns=BASE_NS + 5 * MINUTE_NS)
    assert not policy.should_send(fresh, at_ns=BASE_NS + 5 * MINUTE_NS)


@pytest.mark.trace("REQ-WP-008")
def test_two_symbols_do_not_suppress_each_other(candidate: Candidate) -> None:
    """Dedupe is per setup, not global. A policy keyed on time alone would
    silence a genuine second symbol."""
    policy = _policy()
    policy.should_send(candidate, at_ns=BASE_NS)

    other = candidate.model_copy(update={"symbol": "ETHUSDT"})
    assert policy.should_send(other, at_ns=BASE_NS)


@pytest.mark.trace("REQ-WP-008")
def test_the_cooldown_is_configurable() -> None:
    """Principle X. A hard-coded cooldown is a trading threshold in disguise."""
    candidate = confirmed_candidate()
    strict = DedupePolicy(cooldown_ns=24 * 60 * MINUTE_NS)
    strict.should_send(candidate, at_ns=BASE_NS)

    fresh = confirmed_candidate(opened_at_ns=BASE_NS + 60 * MINUTE_NS)
    assert not strict.should_send(fresh, at_ns=BASE_NS + 60 * MINUTE_NS)
