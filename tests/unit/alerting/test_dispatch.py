"""Delivery that survives a failing network (REQ-WP-008).

PRD section 26.4: retry with exponential backoff, a dead-letter table, a
delivery audit, and -- the line that matters most -- "never block signal engine
on Telegram failure".

ADR-018 makes that last one a property rather than a promise: there is no
socket and no sleep in the queue path, so there is nothing that *can* block.
The transport here is a scripted fake, ten lines, with no network beneath it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from channelflow.alerting import Alert, Dispatcher
from channelflow.signals import Candidate

from .conftest import BASE_NS, MINUTE_NS, confirmed_candidate

CHART_BASE = "https://charts.example.internal"


@dataclass
class ScriptedTransport:
    """Fails `failures` times, then succeeds. Or throws, if `raises` is set."""

    failures: int = 0
    raises: bool = False
    sent: list[str] = field(default_factory=list)
    calls: int = 0

    def send(self, text: str, *, link: str) -> str:
        self.calls += 1
        if self.raises:
            raise ConnectionError("the network is down")
        if self.calls <= self.failures:
            return "error: 502 bad gateway"
        self.sent.append(text)
        return "ok"


def _alert(candidate: Candidate) -> Alert:
    return Alert(
        candidate=candidate,
        price=Decimal("112480"),
        invalidation_price=Decimal("113080"),
        research_target_price=Decimal("111900"),
        event_time_ns=BASE_NS + 3 * MINUTE_NS,
        chart_base_url=CHART_BASE,
    )


@pytest.mark.trace("REQ-WP-008")
def test_a_first_time_success_is_delivered_and_audited(candidate: Candidate) -> None:
    transport = ScriptedTransport()
    dispatcher = Dispatcher(transport=transport)

    dispatcher.deliver(_alert(candidate), at_ns=BASE_NS)

    assert len(transport.sent) == 1
    record = dispatcher.audit[0]
    assert record.status == "delivered"
    assert len(record.attempts) == 1
    assert record.signal_id == _alert(candidate).signal_id


@pytest.mark.trace("REQ-WP-008")
def test_a_transport_failing_twice_delivers_on_the_third_attempt(
    candidate: Candidate,
) -> None:
    """SC-005, FR-009, FR-011. One delivery, three audited attempts."""
    transport = ScriptedTransport(failures=2)
    dispatcher = Dispatcher(transport=transport, max_attempts=5)

    dispatcher.deliver(_alert(candidate), at_ns=BASE_NS)

    assert len(transport.sent) == 1
    record = dispatcher.audit[0]
    assert record.status == "delivered"
    assert [a.ok for a in record.attempts] == [False, False, True]
    assert [a.attempt for a in record.attempts] == [1, 2, 3]


@pytest.mark.trace("REQ-WP-008")
def test_a_transport_that_always_fails_dead_letters(candidate: Candidate) -> None:
    """SC-006, FR-010. The budget is spent and the alert is kept, not lost."""
    transport = ScriptedTransport(failures=99)
    dispatcher = Dispatcher(transport=transport, max_attempts=3)

    dispatcher.deliver(_alert(candidate), at_ns=BASE_NS)

    assert transport.sent == []
    record = dispatcher.audit[0]
    assert record.status == "dead_lettered"
    assert len(record.attempts) == 3
    assert len(dispatcher.dead_letters) == 1
    assert dispatcher.dead_letters[0].signal_id == _alert(candidate).signal_id


@pytest.mark.trace("REQ-WP-008")
def test_a_throwing_transport_never_reaches_the_caller(candidate: Candidate) -> None:
    """SC-006, FR-012, and PRD section 26.4's last line.

    A messaging outage must not stop the system computing signals. The
    exception becomes an audit record; nothing propagates.
    """
    transport = ScriptedTransport(raises=True)
    dispatcher = Dispatcher(transport=transport, max_attempts=2)

    dispatcher.deliver(_alert(candidate), at_ns=BASE_NS)  # must not raise

    record = dispatcher.audit[0]
    assert record.status == "dead_lettered"
    assert "network is down" in record.attempts[-1].detail


@pytest.mark.trace("REQ-WP-008")
def test_the_engine_keeps_going_after_a_dead_letter(candidate: Candidate) -> None:
    """The same property from the caller's side: a failure does not poison the
    dispatcher for the next alert."""
    transport = ScriptedTransport(raises=True)
    dispatcher = Dispatcher(transport=transport, max_attempts=1)
    dispatcher.deliver(_alert(candidate), at_ns=BASE_NS)

    transport.raises = False
    later = confirmed_candidate(opened_at_ns=BASE_NS + 60 * MINUTE_NS)
    dispatcher.deliver(_alert(later), at_ns=BASE_NS + 60 * MINUTE_NS)

    assert [r.status for r in dispatcher.audit] == ["dead_lettered", "delivered"]


@pytest.mark.trace("REQ-WP-008")
def test_backoff_delays_strictly_increase() -> None:
    """FR-009, SC-005.

    Computed, never slept (ADR-018): the requirement is that the delays grow,
    and a test that slept would assert exactly this and take a minute.
    """
    dispatcher = Dispatcher(transport=ScriptedTransport(), backoff_base_ns=MINUTE_NS)

    delays = [dispatcher.backoff_ns(attempt) for attempt in (1, 2, 3, 4)]

    assert delays == sorted(delays)
    assert len(set(delays)) == len(delays), "a flat backoff is not a backoff"
    assert delays[0] == MINUTE_NS


@pytest.mark.trace("REQ-WP-008")
def test_an_unexpected_response_is_treated_as_a_failure(candidate: Candidate) -> None:
    """The spec's first edge case. A delivery nobody can confirm is not one."""

    @dataclass
    class VagueTransport:
        def send(self, text: str, *, link: str) -> str:
            return "202 accepted, probably"

    dispatcher = Dispatcher(transport=VagueTransport(), max_attempts=2)
    dispatcher.deliver(_alert(candidate), at_ns=BASE_NS)

    assert dispatcher.audit[0].status == "dead_lettered"


@pytest.mark.trace("REQ-WP-008")
def test_the_message_and_the_link_both_reach_the_transport(
    candidate: Candidate,
) -> None:
    """The alert is rendered once and handed over whole."""

    @dataclass
    class RecordingTransport:
        seen: list[tuple[str, str]] = field(default_factory=list)

        def send(self, text: str, *, link: str) -> str:
            self.seen.append((text, link))
            return "ok"

    transport = RecordingTransport()
    Dispatcher(transport=transport).deliver(_alert(candidate), at_ns=BASE_NS)

    text, link = transport.seen[0]
    assert "BTCUSDT" in text
    assert link.startswith(f"{CHART_BASE}/chart/binance/BTCUSDT?")
